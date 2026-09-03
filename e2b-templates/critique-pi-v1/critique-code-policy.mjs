function normalizedCommand(command) {
  return String(command || '').replace(/\s+/g, ' ').trim()
}

export function sensitivePath(candidate) {
  const normalized = String(candidate || '').replaceAll('\\', '/').replace(/^\.\//, '')
  return /(?:^|[\/\s'"])(?:\.env(?:[.\w-]*)?|\.git\/hooks(?:[\/\w.-]*)?|id_rsa(?:[.\w-]*)?|id_ed25519(?:[.\w-]*)?|credentials?(?:[.\w-]*)?|secrets?(?:[.\w-]*)?)(?=$|[\/\s'"])/i.test(normalized)
}

export function policyDenial(command, policy = {}, options = {}) {
  const normalized = normalizedCommand(command)
  if (/\bgit\s+push\b/i.test(normalized)) return 'Git push is forbidden: Verify publishing belongs to the control plane.'
  if (/\bgit\s+(?:reset|clean)\b/i.test(normalized)) return 'Destructive git cleanup is forbidden during a Verify repair.'
  if (sensitivePath(normalized)) return 'Credential and secret paths are forbidden in Verify.'
  if (/\b(?:printenv|env|set)\b|\/proc\/[^\s]*environ/i.test(normalized)) return 'Environment inspection is forbidden in Verify.'
  if (!options.allowScript && /\b(?:bash|sh|zsh|fish)\s+-c\b|\b(?:node|python(?:3)?|perl|ruby)\s+-[ec]\b|\b(?:eval|xargs)\b/i.test(normalized)) {
    return 'Shell indirection is forbidden in Verify; use the named structured tools.'
  }
  if (/\b(?:curl|wget|nc|netcat|ssh|scp|rsync|ftp|telnet)\b|\bgit\s+(?:clone|fetch|pull)\b/i.test(normalized) && !policy.allowNetwork) {
    return 'Network commands are disabled for this Verify plan.'
  }
  if (/\b(?:npm|pnpm|yarn|bun)\s+(?:install|add|remove|update|upgrade)\b/i.test(normalized) && !policy.allowDependencyInstall) {
    return 'Dependency installation is disabled for this Verify plan.'
  }
  if (/\b(?:sudo|shutdown|reboot|mount|umount)\b/i.test(normalized)) return 'System administration commands are forbidden in Verify.'
  if (/(?:^|[;&|])\s*rm\s+-[a-z]*r[a-z]*f?\b/i.test(normalized)) return 'Destructive recursive deletion is forbidden.'
  return null
}

export function budgetDenial(input) {
  if (input.toolCalls >= input.maxToolCalls) {
    return `CritiqueCode exceeded the Verify tool-call budget (${input.maxToolCalls}).`
  }
  if (input.workUnits + input.cost > input.maxWorkUnits) {
    return `CritiqueCode exceeded the Verify work-unit budget (${input.maxWorkUnits}).`
  }
  return null
}
