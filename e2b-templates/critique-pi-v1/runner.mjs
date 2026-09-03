/**
 * CritiqueCode is Verify's beta repair runtime, built around Pi's SDK.
 */
import { appendFile, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import {
  createAgentSession,
  DefaultResourceLoader,
  ModelRuntime,
  SessionManager,
  SettingsManager,
  createBashToolDefinition,
} from '@earendil-works/pi-coding-agent'
import {
  buildCritiqueSystemPrompt,
  createCritiqueCodeExtension,
  profileForTask,
} from './critique-code-extension.mjs'
import { policyDenial } from './critique-code-policy.mjs'

const VERIFY_EVENTS_PATH = '/tmp/critique-verify-events.jsonl'

function arg(name) {
  const index = process.argv.indexOf(name)
  return index === -1 ? null : process.argv[index + 1] || null
}

function canonicalEvent(kind, seq, activity = undefined, usage = undefined) {
  return {
    id: `pi_${seq}`,
    providerEventId: `pi_${seq}`,
    seq,
    at: new Date().toISOString(),
    kind,
    status: kind.endsWith('failed') ? 'failed' : kind.endsWith('completed') ? 'completed' : 'running',
    ...(activity ? { activity } : {}),
    ...(usage ? { usage } : {}),
  }
}

function agentEnvironment() {
  const copy = (name) => process.env[name] ? [name, process.env[name]] : null
  return Object.fromEntries([
    copy('PATH'), copy('HOME'), copy('LANG'), copy('LC_ALL'),
    ['CI', '1'],
    ['VERIFY_RUN_ID', process.env.VERIFY_RUN_ID || 'unknown'],
  ].filter(Boolean))
}

function policyCommand(command, policy) {
  return policyDenial(command, policy)
}

function rejectedCommand(message) {
  return `printf '%s\\n' ${JSON.stringify(`Verify policy denied this command: ${message}`)} >&2; exit 126`
}

function positiveBudget(value, fallback) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : fallback
}

function numberFrom(...values) {
  for (const value of values) {
    const number = Number(value)
    if (Number.isFinite(number) && number >= 0) return number
  }
  return 0
}

function normalizeUsage(raw) {
  if (!raw || typeof raw !== 'object') return null
  const inputTokens = numberFrom(raw.inputTokens, raw.input, raw.promptTokens, raw.prompt_tokens)
  const outputTokens = numberFrom(raw.outputTokens, raw.output, raw.completionTokens, raw.completion_tokens)
  const reasoningTokens = numberFrom(raw.reasoningTokens, raw.reasoning, raw.reasoning_tokens)
  const totalTokens = numberFrom(raw.totalTokens, raw.total, raw.total_tokens) || inputTokens + outputTokens + reasoningTokens
  if (inputTokens <= 0 && outputTokens <= 0 && reasoningTokens <= 0 && totalTokens <= 0) return null
  return { inputTokens, outputTokens, reasoningTokens, totalTokens }
}

function estimateUsageCost(usage, pricing) {
  if (!pricing || !usage) return 0
  const normalized = normalizeUsage(usage) || usage
  const input = numberFrom(normalized?.inputTokens, normalized?.input, normalized?.promptTokens)
  const output = numberFrom(normalized?.outputTokens, normalized?.output, normalized?.completionTokens)
  return ((input * Number(pricing.inputUsdPerMillion || 0)) + (output * Number(pricing.outputUsdPerMillion || 0))) / 1_000_000
}

function toolNameOf(row) {
  return String(row.toolName || row.tool?.name || row.toolCall?.name || 'tool')
}

function toolInputOf(row) {
  return row.args ?? row.input ?? row.toolCall?.arguments ?? row.tool?.input
}

function toolPartIdOf(row, fallback) {
  return String(row.toolCallId || row.tool_call_id || row.tool?.id || fallback || '') || undefined
}

function previewValue(value, max = 900) {
  if (value == null) return undefined
  try {
    const text = typeof value === 'string' ? value : JSON.stringify(value)
    return String(text).slice(0, max)
  } catch {
    return String(value).slice(0, max)
  }
}

function textFromToolResult(value) {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map((item) => textFromToolResult(item)).filter(Boolean).join('\n')
  }
  if (!value || typeof value !== 'object') return ''
  if (typeof value.text === 'string') return value.text
  if (typeof value.output === 'string') return value.output
  if (typeof value.content !== 'undefined') return textFromToolResult(value.content)
  if (typeof value.result !== 'undefined') return textFromToolResult(value.result)
  return ''
}

function messageIdOf(row, fallback) {
  return String(row.message?.id || row.message?.messageId || row.message?.timestamp || fallback || '') || undefined
}

function accumulatedPartText(parts, partId, chunk) {
  const text = String(chunk || '')
  const previous = parts.get(partId) || ''
  let next = text
  if (previous) {
    if (text.startsWith(previous)) next = text
    else if (previous.endsWith(text) || previous.includes(text)) next = previous
    else next = previous + text
  }
  const clipped = next.slice(-12_000)
  parts.set(partId, clipped)
  return clipped
}

function resultPreview(row) {
  const value = row.result ?? row.output ?? row.toolResult ?? row.partialResult ?? null
  if (value == null) return undefined
  const text = textFromToolResult(value)
  if (text) return text.slice(0, 1_500)
  return previewValue(value, 1_500)
}

async function main() {
  const taskPath = arg('--task')
  if (!taskPath) throw new Error('Usage: node runner.mjs --task /workspace/verify-task.json')
  const task = JSON.parse(await readFile(resolve(taskPath), 'utf8'))
  const cwd = resolve('/workspace/repo')
  const policySmoke = process.env.VERIFY_POLICY_SMOKE === '1'
  const apiKey = process.env.VERIFY_MODEL_TOKEN
  if (!apiKey) throw new Error('VERIFY_MODEL_TOKEN is required for CritiqueCode runs.')
  const modelId = String(task.model?.id || process.env.VERIFY_MODEL_ID || '').trim()
  if (!modelId) throw new Error('A Verify model id is required for CritiqueCode runs.')
  const profile = profileForTask(task)

  const resultPath = process.env.VERIFY_PI_RESULT_PATH || '/tmp/critique-verify-pi-result.json'
  let seq = 0
  let assistantText = ''
  let toolCalls = 0
  let usage = {}
  let assistantMessageId = ''
  const usageTotals = { inputTokens: 0, outputTokens: 0, reasoningTokens: 0, totalTokens: 0, costUsd: 0 }
  let lastUsageKey = ''
  const lastToolUpdate = new Map()
  const streamedParts = new Map()
  let eventWrites = Promise.resolve()
  let budgetViolation = null
  let abortSession = () => undefined
  const agentMs = positiveBudget(task.budget?.agentMs, 120_000)
  const wallClockMs = positiveBudget(task.budget?.wallClockMs, Math.max(agentMs, 180_000))
  const maxToolCalls = positiveBudget(task.budget?.maxToolCalls, 800)
  const maxWorkUnits = positiveBudget(task.budget?.maxWorkUnits, 4_000)
  const maxModelCostUsd = positiveBudget(task.budget?.maxModelCostUsd, 0)
  const emit = (kind, activity, usage) => {
    seq += 1
    const line = `${JSON.stringify(canonicalEvent(kind, seq, activity, usage))}\n`
    eventWrites = eventWrites.then(() => appendFile(VERIFY_EVENTS_PATH, line))
    return eventWrites
  }
  if (process.env.VERIFY_EVENTS_INITIALIZED !== '1') await writeFile(VERIFY_EVENTS_PATH, '')
  await emit('agent.started', { text: 'CritiqueCode beta repair runtime started.' })

  // Resource discovery is intentionally anchored outside the customer repo.
  // This prevents .pi/extensions, .pi/packages and repository settings from
  // becoming executable control code in the Verify worker.
  const agentDir = '/opt/critique/pi/agent'
  const settingsManager = SettingsManager.inMemory({ compaction: { enabled: false } })
  const critiqueExtension = createCritiqueCodeExtension({
    task,
    cwd,
    safeEnv: agentEnvironment(),
    profile,
    emit,
    onBudgetExhausted: (reason) => {
      budgetViolation = reason
      abortSession()
    },
  })
  const loader = new DefaultResourceLoader({
    cwd: agentDir,
    agentDir,
    settingsManager,
    noExtensions: true,
    noSkills: true,
    noPromptTemplates: true,
    noThemes: true,
    noContextFiles: true,
    systemPromptOverride: () => buildCritiqueSystemPrompt(task, profile, policySmoke),
    // CritiqueCode's middleware is deliberately inline and baked into the
    // image. Customer repositories cannot replace or extend this factory.
    extensionFactories: [critiqueExtension.extensionFactory],
  })
  await loader.reload()

  const modelRuntime = await ModelRuntime.create({
    authPath: '/tmp/critique-pi-auth.json',
    modelsPath: null,
    refreshOnCreate: false,
  })
  const pricing = task.model?.pricing || {}
  modelRuntime.registerProvider('critique-verify', {
    name: 'Critique Verify model gateway',
    baseUrl: process.env.VERIFY_MODEL_ENDPOINT || 'https://openrouter.ai/api/v1',
    apiKey,
    api: 'openai-completions',
    models: [{
      id: modelId,
      name: modelId,
      reasoning: true,
      input: ['text'],
      cost: {
        input: Number(pricing.inputUsdPerMillion || 0),
        output: Number(pricing.outputUsdPerMillion || 0),
        cacheRead: 0,
        cacheWrite: 0,
      },
      contextWindow: 128000,
      maxTokens: profile.maxOutputTokens,
    }],
  })
  // The Pi process and all Bash children must not inherit the model token or
  // repository credentials after the in-memory provider has been constructed.
  delete process.env.VERIFY_MODEL_TOKEN
  delete process.env.OPENROUTER_API_KEY
  delete process.env.GITHUB_TOKEN
  delete process.env.E2B_API_KEY
  const model = modelRuntime.getModel('critique-verify', modelId)
  if (!model) throw new Error(`CritiqueCode could not resolve Verify model ${modelId}.`)

  const safeEnv = agentEnvironment()
  const guardedBash = createBashToolDefinition(cwd, {
    exposeSessionEnvironment: false,
    spawnHook: ({ command, cwd: commandCwd }) => {
      const denial = policyCommand(command, task.policy || {})
      return { command: denial ? rejectedCommand(denial) : command, cwd: commandCwd, env: safeEnv }
    },
  })

  const { session } = await createAgentSession({
    cwd,
    agentDir,
    model,
    modelRuntime,
    thinkingLevel: profile.thinkingLevel,
    resourceLoader: loader,
    settingsManager,
    sessionManager: SessionManager.inMemory(cwd),
    tools: ['read', 'grep', 'find', 'ls', 'bash', 'edit', 'write', 'critique_check', 'critique_record_evidence'],
    customTools: [guardedBash, ...critiqueExtension.customTools],
  })
  abortSession = () => { void session.abort() }

  function recordUsage(raw) {
    const normalized = normalizeUsage(raw)
    if (!normalized) return
    // Pi emits the same assistant message at message_end and agent_end. Keep
    // one copy, while accumulating separate model turns for a real live total.
    const key = JSON.stringify(normalized)
    if (key === lastUsageKey) return
    lastUsageKey = key
    const costUsd = estimateUsageCost(normalized, pricing)
    usageTotals.inputTokens += normalized.inputTokens
    usageTotals.outputTokens += normalized.outputTokens
    usageTotals.reasoningTokens += normalized.reasoningTokens
    usageTotals.totalTokens += normalized.totalTokens
    usageTotals.costUsd += costUsd
    usage = {
      inputTokens: usageTotals.inputTokens,
      outputTokens: usageTotals.outputTokens,
      reasoningTokens: usageTotals.reasoningTokens,
      totalTokens: usageTotals.totalTokens,
      costUsd: usageTotals.costUsd,
    }
    void emit('usage', undefined, usage)
    if (maxModelCostUsd && usageTotals.costUsd > maxModelCostUsd) {
      budgetViolation = `CritiqueCode exceeded the Verify model budget ($${maxModelCostUsd.toFixed(2)}).`
      abortSession()
    }
  }

  session.subscribe((event) => {
    const row = event
    if (row.type === 'message_update') {
      const update = row.assistantMessageEvent
      const messageId = messageIdOf(row, 'message_current')
      if (update?.type === 'text_delta' && typeof update.delta === 'string') {
        if (assistantMessageId && messageId && assistantMessageId !== messageId && !assistantText.endsWith('\n\n')) {
          assistantText += '\n\n'
        }
        assistantMessageId = messageId
        assistantText = (assistantText + update.delta).slice(-12000)
        const partId = `${messageId}:text:${update.contentIndex ?? 0}`
        void emit('agent.text', {
          text: accumulatedPartText(streamedParts, partId, update.delta),
          partId,
          messageId,
        })
      }
      if ((update?.type === 'thinking_delta' || update?.type === 'reasoning_delta') && typeof update.delta === 'string') {
        const partId = `${messageId}:thinking:${update.contentIndex ?? 0}`
        void emit('agent.reasoning', {
          text: accumulatedPartText(streamedParts, partId, update.delta),
          partId,
          messageId,
        })
      }
    }
    // Pi exposes both planning and execution lifecycle events. Count only
    // execution: counting both makes a 14-call budget fail after 7 real calls.
    if (row.type === 'tool_execution_start') {
      toolCalls += 1
      void emit('tool.started', {
        tool: toolNameOf(row),
        partId: toolPartIdOf(row, `tool_${toolCalls}`),
        inputPreview: previewValue(toolInputOf(row)),
      })
    }
    if (row.type === 'tool_execution_update') {
      const toolCallId = String(row.toolCallId || `${toolNameOf(row)}:${toolCalls}`)
      const outputPreview = resultPreview(row)
      const previous = lastToolUpdate.get(toolCallId)
      const now = Date.now()
      if (outputPreview && outputPreview !== previous?.output && now - (previous?.at || 0) >= 300) {
        lastToolUpdate.set(toolCallId, { output: outputPreview, at: now })
        void emit('tool.updated', {
          tool: toolNameOf(row),
          partId: toolPartIdOf(row, toolCallId),
          inputPreview: previewValue(toolInputOf(row)),
          outputPreview,
        })
      }
    }
    if (row.type === 'tool_execution_end') {
      const toolError = row.error || row.isError || row.result?.isError
      void emit(toolError ? 'tool.failed' : 'tool.completed', {
        tool: toolNameOf(row),
        partId: toolPartIdOf(row, `tool_${toolCalls}`),
        inputPreview: previewValue(toolInputOf(row)),
        error: toolError ? String(row.error || row.result?.error || 'Tool policy denied this call.') : undefined,
        outputPreview: resultPreview(row),
      })
    }
    if (row.type === 'message_end' && row.message?.role === 'assistant') recordUsage(row.message.usage)
    if (row.type === 'agent_end') recordUsage(row.message?.usage)
  })

  const wallClockTimer = setTimeout(() => {
    budgetViolation = `CritiqueCode exceeded the Verify wall-clock budget (${wallClockMs}ms).`
    abortSession()
  }, wallClockMs)
  wallClockTimer.unref?.()

  try {
    await emit('agent.status', { text: 'CritiqueCode is waiting for the model response…' })
    const agentTimer = setTimeout(() => {
      budgetViolation = `CritiqueCode exceeded the Verify agent time budget (${agentMs}ms).`
      void session.abort()
    }, agentMs)
    try {
      await session.prompt([
      `Repository: ${task.repository?.fullName || 'unknown'}`,
      `Base SHA: ${task.repository?.baseSha || 'unknown'}`,
      task.target?.title ? `Target: ${task.target.title}` : '',
      task.target?.body ? `Target context:\n${task.target.body}` : '',
      Array.isArray(task.acceptanceCriteria) && task.acceptanceCriteria.length ? `Acceptance criteria:\n${task.acceptanceCriteria.map((item) => `- ${item}`).join('\n')}` : '',
      `Request:\n${task.request}`,
      ].filter(Boolean).join('\n\n'))
    } finally {
      clearTimeout(agentTimer)
    }
    if (critiqueExtension.state.budgetViolation) throw new Error(critiqueExtension.state.budgetViolation)
    if (budgetViolation) throw new Error(budgetViolation)
    await emit('agent.completed', { text: 'CritiqueCode repair runtime completed.' })
    await eventWrites
    await writeFile(resultPath, JSON.stringify({
      status: 'completed',
      harness: 'pi',
      modelId,
      assistantText,
      usage,
      workUnits: critiqueExtension.state.workUnits,
      toolCalls: critiqueExtension.state.toolCalls,
      budget: { wallClockMs, agentMs, maxToolCalls, maxWorkUnits, maxModelCostUsd },
      checks: critiqueExtension.state.checks,
      claims: critiqueExtension.state.claims,
      evidence: { checks: critiqueExtension.state.checkRows, claims: critiqueExtension.state.claimRows },
      completedAt: new Date().toISOString(),
    }))
    // Pi's SDK can leave provider/session handles open after the final
    // artifact is durable. The parent E2B runner must not wait for those
    // handles until its outer deadline and misclassify a successful answer as
    // a sandbox timeout.
    process.exit(0)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    await emit('agent.failed', { error: message })
    await eventWrites
    await writeFile(resultPath, JSON.stringify({
      status: 'failed',
      harness: 'pi',
      modelId,
      assistantText,
      usage,
      workUnits: critiqueExtension.state.workUnits,
      toolCalls: critiqueExtension.state.toolCalls,
      budget: { wallClockMs, agentMs, maxToolCalls, maxWorkUnits, maxModelCostUsd },
      checks: critiqueExtension.state.checks,
      claims: critiqueExtension.state.claims,
      evidence: { checks: critiqueExtension.state.checkRows, claims: critiqueExtension.state.claimRows },
      error: message,
      completedAt: new Date().toISOString(),
    }))
    process.exit(1)
  } finally {
    clearTimeout(wallClockTimer)
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error))
  process.exitCode = 1
})
