/** Canonical planning draft normalization and publication contracts. */

export const PUBLICATION_STATUS = Object.freeze({
  DRAFT: 'draft',
  GOAL_CREATED: 'goal_created',
  RUN_CREATED: 'run_created',
  PUBLISHED: 'published'
})

const EXECUTION_MODES = new Set(['manual', 'assisted', 'agent'])
const STEP_KINDS = new Set(['manual', 'agent', 'tool', 'review'])
const GOAL_PRIORITIES = new Set(['low', 'medium', 'high'])

export function createDraftId() {
  return globalThis.crypto?.randomUUID?.() || ('draft-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10))
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function requiredText(value, message = '生成的方案不完整，请重新生成。') {
  const text = typeof value === 'string' ? value.trim() : ''
  if (!text) throw new Error(message)
  return text
}

function optionalText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function stringList(value) {
  if (!Array.isArray(value)) return []
  return [...new Set(value.map((item) => String(item || '').trim()).filter(Boolean))]
}

function normalizeCompletionCriteria(value) {
  const criteria = isPlainObject(value) ? { ...value } : {}
  criteria.deliverables = stringList(criteria.deliverables)
  return criteria
}

function uniqueStepKey(value, index, usedKeys) {
  const preferred = optionalText(value) || ('step-' + (index + 1))
  let key = preferred.slice(0, 100)
  let suffix = 2
  while (usedKeys.has(key)) {
    const suffixText = '-' + suffix
    key = preferred.slice(0, 100 - suffixText.length) + suffixText
    suffix += 1
  }
  usedKeys.add(key)
  return key
}

function normalizeSteps(rawSteps, mode) {
  if (!Array.isArray(rawSteps) || !rawSteps.length) {
    throw new Error('方案中没有可以执行的步骤。')
  }
  const usedKeys = new Set()
  const keyAliases = new Map()
  const prepared = rawSteps.map((step, index) => {
    if (!isPlainObject(step)) throw new Error('生成的步骤不完整，请重新生成。')
    const originalKey = optionalText(step.client_key) || ('step-' + (index + 1))
    const clientKey = uniqueStepKey(originalKey, index, usedKeys)
    if (!keyAliases.has(originalKey)) keyAliases.set(originalKey, clientKey)
    const kind = STEP_KINDS.has(step.kind) ? step.kind : (mode === 'agent' ? 'agent' : 'manual')
    return {
      client_key: clientKey,
      title: requiredText(step.title),
      description: optionalText(step.description),
      kind,
      depends_on: stringList(step.depends_on),
      parallel_group: optionalText(step.parallel_group) || null,
      max_attempts: Number.isInteger(step.max_attempts) && step.max_attempts >= 1 && step.max_attempts <= 10
        ? step.max_attempts
        : (kind === 'agent' ? 3 : 1),
      requires_approval: Boolean(step.requires_approval),
      completion_criteria: normalizeCompletionCriteria(step.completion_criteria),
      input_data: isPlainObject(step.input_data) ? { ...step.input_data } : {}
    }
  })
  const validKeys = new Set(prepared.map((step) => step.client_key))
  return prepared.map((step) => ({
    ...step,
    depends_on: [...new Set(step.depends_on
      .map((key) => keyAliases.get(key) || key)
      .filter((key) => validKeys.has(key) && key !== step.client_key))]
  }))
}

function assertAcyclicSteps(steps) {
  const dependencies = new Map(steps.map((step) => [step.client_key, step.depends_on]))
  const visiting = new Set()
  const visited = new Set()

  function visit(key) {
    if (visiting.has(key)) throw new Error('步骤之间不能互相等待，请调整开始条件。')
    if (visited.has(key)) return
    visiting.add(key)
    for (const dependency of dependencies.get(key) || []) visit(dependency)
    visiting.delete(key)
    visited.add(key)
  }

  for (const key of dependencies.keys()) visit(key)
}

function normalizePublication(value) {
  const publication = isPlainObject(value) ? value : {}
  const goalId = optionalText(publication.goal_id) || null
  const runId = optionalText(publication.run_id) || null
  let status = Object.values(PUBLICATION_STATUS).includes(publication.status)
    ? publication.status
    : PUBLICATION_STATUS.DRAFT
  if (!goalId) status = PUBLICATION_STATUS.DRAFT
  else if (!runId && status !== PUBLICATION_STATUS.GOAL_CREATED) status = PUBLICATION_STATUS.GOAL_CREATED
  else if (runId && ![PUBLICATION_STATUS.RUN_CREATED, PUBLICATION_STATUS.PUBLISHED].includes(status)) {
    status = PUBLICATION_STATUS.RUN_CREATED
  }
  return {
    status,
    goal_id: goalId,
    run_id: runId,
    updated_at: optionalText(publication.updated_at) || null
  }
}

export function normalizePlanDraft(result, fallbackMode = 'assisted') {
  if (!isPlainObject(result) || !isPlainObject(result.goal) || !isPlainObject(result.run)) {
    throw new Error('生成的方案不完整，请重新生成。')
  }
  const mode = EXECUTION_MODES.has(result.run.mode) ? result.run.mode : fallbackMode
  const goalTitle = requiredText(result.goal.title)
  return {
    goal: {
      title: goalTitle,
      description: optionalText(result.goal.description) || optionalText(result.summary),
      desired_outcome: optionalText(result.goal.desired_outcome) || goalTitle,
      priority: GOAL_PRIORITIES.has(result.goal.priority) ? result.goal.priority : 'medium',
      metadata: isPlainObject(result.goal.metadata) ? { ...result.goal.metadata } : {}
    },
    run: {
      title: optionalText(result.run.title) || goalTitle,
      objective: optionalText(result.run.objective) || optionalText(result.goal.desired_outcome) || goalTitle,
      mode,
      metadata: isPlainObject(result.run.metadata) ? { ...result.run.metadata } : {},
      steps: normalizeSteps(result.run.steps, mode)
    },
    estimated_duration: optionalText(result.estimated_duration),
    meta: {
      fallback: Boolean(result.meta?.used_fallback ?? result.meta?.fallback),
      needs_review: result.meta?.needs_review !== false
    },
    draft_id: String(result.draft_id || result.id || createDraftId()),
    publication: normalizePublication(result.publication)
  }
}

export function normalizeHistoryEntry(item) {
  const draft = normalizePlanDraft(item)
  return {
    ...draft,
    id: draft.draft_id,
    createdAt: optionalText(item?.createdAt) || optionalText(item?.created_at) || new Date().toISOString(),
    updatedAt: optionalText(item?.updatedAt) || optionalText(item?.updated_at) || null
  }
}

export function buildGoalCreateInput(plan) {
  const title = requiredText(plan?.goal?.title, '目标名称不能为空。')
  const draftId = requiredText(plan?.draft_id, '方案缺少稳定标识，请重新生成。')
  return {
    ...plan.goal,
    title,
    description: optionalText(plan.goal.description),
    desired_outcome: optionalText(plan.goal.desired_outcome) || title,
    idempotency_key: 'plan-goal-' + draftId,
    metadata: { ...(plan.goal.metadata || {}), planning_draft_id: draftId }
  }
}

export function buildRunSpecification(plan) {
  const draftId = requiredText(plan?.draft_id, '方案缺少稳定标识，请重新生成。')
  const normalized = normalizeSteps(plan?.run?.steps, plan?.run?.mode || 'assisted')
  assertAcyclicSteps(normalized)
  return {
    ...plan.run,
    title: optionalText(plan.run.title) || requiredText(plan.goal.title),
    objective: optionalText(plan.run.objective) || optionalText(plan.goal.desired_outcome) || requiredText(plan.goal.title),
    idempotency_key: 'plan-' + draftId,
    metadata: { ...(plan.run.metadata || {}), planning_draft_id: draftId },
    steps: normalized
  }
}

export function resetMissingPublication(plan, resource) {
  if (resource === 'goal') {
    return {
      ...plan,
      publication: { status: PUBLICATION_STATUS.DRAFT, goal_id: null, run_id: null, updated_at: new Date().toISOString() }
    }
  }
  return {
    ...plan,
    publication: {
      status: plan?.publication?.goal_id ? PUBLICATION_STATUS.GOAL_CREATED : PUBLICATION_STATUS.DRAFT,
      goal_id: plan?.publication?.goal_id || null,
      run_id: null,
      updated_at: new Date().toISOString()
    }
  }
}
