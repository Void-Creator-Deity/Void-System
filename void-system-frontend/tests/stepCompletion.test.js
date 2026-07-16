import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildStepCompletionInput,
  createStepCompletionDraft,
  declaredDeliverables
} from '../src/domain/stepCompletion.js'
import { artifactKindLabel, mergeDeclaredDeliverables } from '../src/domain/runReviewPresentation.js'

test('declared deliverables accept text and named objects', () => {
  assert.deepEqual(declaredDeliverables({
    completion_criteria: { deliverables: ['验收截图', { title: '发布链接' }, { name: '复盘记录' }] }
  }), ['验收截图', '发布链接', '复盘记录'])
})

test('draft preselects the first declared result without inventing a link', () => {
  const draft = createStepCompletionDraft({
    title: '发布版本',
    completion_criteria: { deliverables: ['发布说明'] }
  })

  assert.equal(draft.includeResult, true)
  assert.equal(draft.resultTitle, '发布说明')
  assert.equal(draft.resultUrl, '')
})

test('completion input keeps the note and permits a text-only result', () => {
  const input = buildStepCompletionInput({
    note: ' 已完成发布并核对页面内容。 ',
    includeResult: true,
    resultTitle: '',
    resultKind: 'document',
    resultUrl: ''
  }, {
    title: '发布版本',
    completion_criteria: { deliverables: ['发布说明'] }
  })

  assert.deepEqual(input.output_data, { summary: '已完成发布并核对页面内容。' })
  assert.deepEqual(input.artifacts, [{
    title: '发布说明',
    kind: 'document',
    uri: null,
    metadata: { source: 'user_step_completion' }
  }])
})

test('completion input requires a user-facing execution note', () => {
  assert.throws(() => buildStepCompletionInput({ note: '   ' }, { title: '核对结果' }), /请填写完成说明/)
})

test('review presentation hides artifact storage values from users', () => {
  assert.equal(artifactKindLabel('result'), '一般成果')
  assert.equal(artifactKindLabel('link'), '链接')
  assert.equal(artifactKindLabel('custom_internal_kind'), '成果')
})

test('review presentation merges repeated deliverables and requires every occurrence', () => {
  assert.deepEqual(mergeDeclaredDeliverables([
    { step_id: 'step-1', title: '验收记录', recorded: true },
    { step_id: 'step-2', title: '验收记录', recorded: false },
    { step_id: 'step-2', title: ' 发布链接 ', recorded: true }
  ]), [
    { step_id: 'step-1', title: '验收记录', recorded: false, occurrenceCount: 2 },
    { step_id: 'step-2', title: '发布链接', recorded: true, occurrenceCount: 1 }
  ])
})
