import test from 'node:test'
import assert from 'node:assert/strict'

import {
  PLAN_DRAFT_STATUS,
  buildPlanDraftPayload,
  createPublicationKey,
  normalizePlanDraft
} from '../src/domain/planDraft.js'

const rawPayload = {
  goal: {
    title: '发布作品集',
    description: '整理并发布一个可访问的作品集。',
    desired_outcome: '获得一个可以分享的作品集链接。'
  },
  run: {
    mode: 'assisted',
    steps: [
      {
        client_key: 'collect',
        title: '整理素材',
        completion_criteria: { deliverables: ['素材清单'] }
      },
      {
        client_key: 'publish',
        title: '发布网站',
        depends_on: ['collect'],
        requires_approval: true,
        completion_criteria: { deliverables: ['公开链接'] }
      }
    ]
  },
  context: { sources: ['profile-summary'] },
  meta: { needs_review: true }
}

test('server Plan Draft record keeps authority fields and editable graph', () => {
  const draft = normalizePlanDraft({
    draft_id: 'draft-7',
    status: PLAN_DRAFT_STATUS.READY,
    version: 3,
    created_at: '2026-07-18T08:00:00.000Z',
    payload: rawPayload
  })

  assert.equal(draft.draft_id, 'draft-7')
  assert.equal(draft.status, PLAN_DRAFT_STATUS.READY)
  assert.equal(draft.version, 3)
  assert.deepEqual(draft.run.steps[1].depends_on, ['collect'])
  assert.deepEqual(draft.run.steps[1].completion_criteria.deliverables, ['公开链接'])
  assert.equal(draft.run.steps[1].requires_approval, true)
})

test('editable payload excludes immutable server publication fields', () => {
  const draft = normalizePlanDraft({
    draft_id: 'draft-42',
    status: PLAN_DRAFT_STATUS.PUBLISHED,
    version: 4,
    published_goal_id: 'goal-1',
    published_run_id: 'run-1',
    payload: rawPayload
  })
  const payload = buildPlanDraftPayload(draft)

  assert.equal(payload.goal.title, '发布作品集')
  assert.deepEqual(payload.run.steps[1].depends_on, ['collect'])
  assert.equal(payload.run.steps[1].requires_approval, true)
  assert.deepEqual(payload.context, { sources: ['profile-summary'] })
  assert.equal(Object.hasOwn(payload, 'draft_id'), false)
  assert.equal(Object.hasOwn(payload, 'published_run_id'), false)
})

test('cyclic dependencies are rejected before a stale edit reaches the API', () => {
  const draft = normalizePlanDraft({
    draft_id: 'draft-cycle',
    payload: {
      ...rawPayload,
      run: {
        ...rawPayload.run,
        steps: [
          { client_key: 'a', title: 'A', depends_on: ['b'] },
          { client_key: 'b', title: 'B', depends_on: ['a'] }
        ]
      }
    }
  })

  assert.throws(() => buildPlanDraftPayload(draft), /不能互相等待/)
})

test('publication keys are scoped to a server draft and vary per first attempt', () => {
  const first = createPublicationKey('draft-key')
  const second = createPublicationKey('draft-key')

  assert.match(first, /^plan-draft-draft-key-/)
  assert.match(second, /^plan-draft-draft-key-/)
  assert.notEqual(first, second)
})
