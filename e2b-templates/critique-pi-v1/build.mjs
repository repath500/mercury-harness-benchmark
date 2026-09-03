import { Template, defaultBuildLogger } from 'e2b'
import { CRITIQUE_PI_BUILD_OPTIONS, CRITIQUE_PI_TEMPLATE_ID, template } from './template.mjs'

const result = await Template.build(template, CRITIQUE_PI_TEMPLATE_ID, {
  ...CRITIQUE_PI_BUILD_OPTIONS,
  onBuildLogs: defaultBuildLogger(),
})
console.log(JSON.stringify(result, null, 2))
