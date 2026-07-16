import test from 'node:test'
import assert from 'node:assert/strict'

import {
  PUBLICATION_STATUS,
  buildGoalCreateInput,
  buildRunSpecification,
  normalizeHistoryEntry,
  normalizePlanDraft,
  resetMissingPublication
} from '../src/domain/planDraft.js'

const rawPlan = {
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
  }
}

test('legacy history keeps its stable draft identity and editable graph', () => {
  const entry = normalizeHistoryEntry({
    ...rawPlan,
    id: 'legacy-draft-7',
    createdAt: '2026-07-16T08:00:00.000Z'
  })

  assert.equal(entry.draft_id, 'legacy-draft-7')
  assert.equal(entry.id, 'legacy-draft-7')
  assert.deepEqual(entry.run.steps[1].depends_on, ['collect'])
  assert.deepEqual(entry.run.steps[1].completion_criteria.deliverables, ['公开链接'])
  assert.equal(entry.run.steps[1].requires_approval, true)
})

test('publication inputs are stable and preserve the user-reviewed graph', () => {
  const plan = normalizePlanDraft({ ...rawPlan, draft_id: 'draft-42' })
  const goal = buildGoalCreateInput(plan)
  const run = buildRunSpecification(plan)

  assert.equal(goal.idempotency_key, 'plan-goal-draft-42')
  assert.equal(goal.metadata.planning_draft_id, 'draft-42')
  assert.equal(run.idempotency_key, 'plan-draft-42')
  assert.deepEqual(run.steps[1].depends_on, ['collect'])
  assert.equal(run.steps[1].requires_approval, true)
  assert.deepEqual(run.steps[1].completion_criteria.deliverables, ['公开链接'])
})

test('missing resources reset only the invalid publication stages', () => {
  const plan = normalizePlanDraft({
    ...rawPlan,
    draft_id: 'draft-recovery',
    publication: {
      status: PUBLICATION_STATUS.PUBLISHED,
      goal_id: 'goal-1',
      run_id: 'run-1'
    }
  })

  const missingRun = resetMissingPublication(plan, 'run')
  assert.equal(missingRun.publication.status, PUBLICATION_STATUS.GOAL_CREATED)
  assert.equal(missingRun.publication.goal_id, 'goal-1')
  assert.equal(missingRun.publication.run_id, null)

  const missingGoal = resetMissingPublication(plan, 'goal')
  assert.equal(missingGoal.publication.status, PUBLICATION_STATUS.DRAFT)
  assert.equal(missingGoal.publication.goal_id, null)
  assert.equal(missingGoal.publication.run_id, null)
})


test('cyclic dependencies are rejected before publication', () => {
  const plan = normalizePlanDraft({
    ...rawPlan,
    draft_id: 'draft-cycle',
    run: {
      ...rawPlan.run,
      steps: [
        { client_key: 'a', title: 'A', depends_on: ['b'] },
        { client_key: 'b', title: 'B', depends_on: ['a'] }
      ]
    }
  })

  assert.throws(() => buildRunSpecification(plan), /不能互相等待/)
})
