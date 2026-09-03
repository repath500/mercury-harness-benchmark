import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'

function version(command, args = ['--version']) {
  try {
    return execFileSync(command, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
  } catch (error) {
    return `unavailable: ${error instanceof Error ? error.message : String(error)}`
  }
}

const packageJson = JSON.parse(readFileSync('/opt/critique/verify/package.json', 'utf8'))
const manifest = {
  recordedAt: new Date().toISOString(),
  pins: { piCodingAgent: packageJson.dependencies['@earendil-works/pi-coding-agent'], pnpm: '10.10.0' },
  versions: {
    node: version('node'),
    pnpm: version('pnpm'),
    git: version('git'),
    jq: version('jq'),
    rg: version('rg'),
  },
}
writeFileSync('/opt/critique/runtime-versions.json', `${JSON.stringify(manifest, null, 2)}\n`)
