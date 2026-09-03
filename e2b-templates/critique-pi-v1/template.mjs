import { Template } from 'e2b'

export const CRITIQUE_PI_TEMPLATE_ID = 'critique-pi-v1'
export const CRITIQUE_PI_BUILD_OPTIONS = { cpuCount: 2, memoryMB: 2048 }

export const template = Template()
  .fromNodeImage('22')
  .setUser('root')
  .setWorkdir('/workspace')
  .makeDir(['/workspace', '/opt/critique/verify', '/opt/critique/pi/agent'])
  .aptInstall(['git', 'jq', 'ripgrep'])
  .runCmd('npm install -g pnpm@10.10.0')
  // Template() resolves COPY sources from this file's directory. Keep these
  // paths local so builds work from the repo root as well as from this folder.
  .copy('package.json', '/opt/critique/verify/package.json')
  .runCmd('cd /opt/critique/verify && npm install --omit=dev --ignore-scripts')
  .copy('runner.mjs', '/opt/critique/verify/runner.mjs')
  .copy('critique-code-extension.mjs', '/opt/critique/verify/critique-code-extension.mjs')
  .copy('critique-code-policy.mjs', '/opt/critique/verify/critique-code-policy.mjs')
  .copy('runtime-manifest.json', '/opt/critique/runtime-manifest.json')
  .copy('record-runtime-versions.mjs', '/opt/critique/record-runtime-versions.mjs')
  .runCmd('node /opt/critique/record-runtime-versions.mjs')
