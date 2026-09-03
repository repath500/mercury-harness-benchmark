import assert from 'node:assert/strict'
import test from 'node:test'

import { budgetDenial, policyDenial, sensitivePath } from './critique-code-policy.mjs'

test('Verify policy blocks indirection, secret paths, and network commands', () => {
  assert.match(policyDenial('bash -c "echo hi"', { allowNetwork: false }), /Shell indirection/)
  assert.equal(policyDenial('node -e "console.log(1)"', { allowNetwork: false }, { allowScript: true }), null)
  assert.match(policyDenial('cat .env.local', { allowNetwork: false }), /secret paths/)
  assert.match(policyDenial('git fetch origin', { allowNetwork: false }), /Network commands/)
  assert.equal(policyDenial('npm test', { allowNetwork: false, allowDependencyInstall: false }), null)
  assert.equal(sensitivePath('.env.example'), true)
})

test('Verify budget denial happens before a tool exceeds either cap', () => {
  assert.equal(budgetDenial({ toolCalls: 0, workUnits: 0, cost: 1, maxToolCalls: 1, maxWorkUnits: 2 }), null)
  assert.match(budgetDenial({ toolCalls: 1, workUnits: 1, cost: 1, maxToolCalls: 1, maxWorkUnits: 2 }), /tool-call budget/)
  assert.match(budgetDenial({ toolCalls: 0, workUnits: 2, cost: 1, maxToolCalls: 10, maxWorkUnits: 2 }), /work-unit budget/)
})
