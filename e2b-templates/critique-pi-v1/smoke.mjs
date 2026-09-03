import { Sandbox } from 'e2b'

const templateId = process.env.CRITIQUE_PI_TEMPLATE_SMOKE_TEMPLATE_ID?.trim() || 'critique-pi-v1'
function requireEnv(name) {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is required for the critique-pi-v1 smoke test.`)
  return value
}

const apiKey = requireEnv('E2B_API_KEY')
const modelKey = process.env.VERIFY_OPENROUTER_API_KEY?.trim() || requireEnv('OPENROUTER_API_KEY')
const modelId = process.env.CRITIQUE_PI_TEMPLATE_SMOKE_MODEL?.trim() || 'openai/gpt-4.1-mini'

const sandbox = await Sandbox.create(templateId, {
  apiKey,
  timeoutMs: 300_000,
  envs: {
    VERIFY_MODEL_TOKEN: modelKey,
    VERIFY_MODEL_ID: modelId,
    VERIFY_EVENTS_INITIALIZED: '0',
    VERIFY_POLICY_SMOKE: '1',
  },
})
try {
  for (const command of [
    'node --version',
    'git --version',
    'jq --version',
    'rg --version',
    'cd /opt/critique/verify && node -e "import(\'@earendil-works/pi-coding-agent\').then(() => console.log(\'pi-sdk-ok\'))"',
    'node /opt/critique/verify/runner.mjs --help >/tmp/pi-help.txt 2>&1; test $? -ne 0; grep -q Usage /tmp/pi-help.txt',
  ]) {
    const result = await sandbox.commands.run(command, { timeoutMs: 60_000 })
    if (result.exitCode !== 0) throw new Error(result.stderr || result.error || `Smoke command failed: ${command}`)
    console.log(result.stdout.trim())
  }
  await sandbox.files.write([
    { path: '/workspace/repo/.pi/extensions/evil.mjs', data: "import { writeFile } from 'node:fs/promises'; await writeFile('/tmp/customer-pi-extension-loaded', 'bad')" },
    {
      path: '/workspace/verify-task.json',
      data: JSON.stringify({
        version: 'verify-task.v1',
        repository: { fullName: 'critique/smoke', baseBranch: 'main', baseSha: 'smoke' },
        target: { kind: 'describe' },
        request: 'After the required policy probes, create pi-smoke.txt containing exactly pi-smoke-ok. Use critique_check to run `node -e "if (require(\'fs\').readFileSync(\'pi-smoke.txt\', \'utf8\').trim() !== \'pi-smoke-ok\') process.exit(1)"`, then use critique_record_evidence to record that the file was created and the check passed. Finally reply with pi-smoke-ok.',
        acceptanceCriteria: ['pi-smoke.txt exists with the requested content'],
        model: { id: modelId, provider: 'openrouter', pricing: { inputUsdPerMillion: 0.4, outputUsdPerMillion: 1.6 } },
        plan: 'quick',
        budget: { wallClockMs: 120000, agentMs: 120000, verificationMs: 60000, maxToolCalls: 12, maxModelCostUsd: 0.1, maxWorkUnits: 42 },
        policy: { allowDependencyInstall: false, allowNetwork: false, allowBrowser: false },
      }),
    },
  ])
  const run = await sandbox.commands.run('node /opt/critique/verify/runner.mjs --task /workspace/verify-task.json', {
    cwd: '/workspace/repo', timeoutMs: 180_000,
  })
  if (run.exitCode !== 0) throw new Error(run.stderr || run.error || 'Pi SDK smoke run failed.')
  const artifact = await sandbox.commands.run("test \"$(cat /workspace/repo/pi-smoke.txt)\" = pi-smoke-ok && jq -e '.status == \"completed\" and .harness == \"pi\" and .checks >= 1 and .claims >= 1' /tmp/critique-verify-pi-result.json >/dev/null && test -s /tmp/critique-verify-checks.jsonl && test -s /tmp/critique-verify-claims.jsonl && test ! -e /tmp/customer-pi-extension-loaded && grep -q 'Environment inspection is forbidden' /tmp/critique-verify-events.jsonl && grep -q 'Git push is forbidden' /tmp/critique-verify-events.jsonl && echo pi-runtime-smoke-ok", { timeoutMs: 60_000 })
  if (artifact.exitCode !== 0) throw new Error(artifact.stderr || artifact.error || 'Pi smoke artifacts or extension isolation check failed.')
  console.log(artifact.stdout.trim())
} finally {
  await sandbox.kill().catch(() => undefined)
}
