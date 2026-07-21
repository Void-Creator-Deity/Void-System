/**
 * Client-side mapping for the server-owned Plan Draft contract.
 *
 * This module validates only the data needed to render and edit a draft. The backend
 * TaskExecution boundary remains the authority for publication and persistence rules.
 */
export const PLAN_DRAFT_STATUS = Object.freeze({
  READY: 'ready',
  PUBLISHED: 'published',
  DISCARDED: 'discarded'
})

const EXECUTION_MODES = new Set(['manual', 'assisted'])
const GOAL_PRIORITIES = new Set(['low', 'medium', 'high'])

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

function normalizeSteps(rawSteps) {
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
    const kind = 'manual'
    return {
      client_key: clientKey,
      title: requiredText(step.title),
      description: optionalText(step.description),
      kind,
      depends_on: stringList(step.depends_on),
      parallel_group: optionalText(step.parallel_group) || null,
      max_attempts: 1,
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

/**
 * Normalize an HTTP Plan Draft snapshot into the Advisor render model.
 * Input: A public Plan Draft record, or its payload while a generation is completing.
 * Output: Editable goal/run data plus immutable server identity, version and publication references.
 * Called by: Advisor generation recovery, history selection, save and publish responses.
 * Side effects: None.
 * Failure: Throws for malformed plans so the page can keep the prior authoritative draft visible.
 * Invariant: draft_id, status, version and published ids originate from the server and are never invented.
 */
export function normalizePlanDraft(record, fallbackMode = 'assisted') {
  const source = isPlainObject(record?.payload) ? record.payload : record
  if (!isPlainObject(source) || !isPlainObject(source.goal) || !isPlainObject(source.run)) {
    throw new Error('生成的方案不完整，请重新生成。')
  }
  const mode = EXECUTION_MODES.has(source.run.mode) ? source.run.mode : fallbackMode
  const goalTitle = requiredText(source.goal.title)
  const status = Object.values(PLAN_DRAFT_STATUS).includes(record?.status)
    ? record.status
    : PLAN_DRAFT_STATUS.READY
  return {
    goal: {
      title: goalTitle,
      description: optionalText(source.goal.description) || optionalText(source.summary),
      desired_outcome: optionalText(source.goal.desired_outcome) || goalTitle,
      priority: GOAL_PRIORITIES.has(source.goal.priority) ? source.goal.priority : 'medium',
      metadata: isPlainObject(source.goal.metadata) ? { ...source.goal.metadata } : {}
    },
    run: {
      title: optionalText(source.run.title) || goalTitle,
      objective: optionalText(source.run.objective) || optionalText(source.goal.desired_outcome) || goalTitle,
      mode,
      metadata: isPlainObject(source.run.metadata) ? { ...source.run.metadata } : {},
      steps: normalizeSteps(source.run.steps)
    },
    summary: optionalText(source.summary),
    estimated_duration: optionalText(source.estimated_duration),
    context: isPlainObject(source.context) ? { ...source.context } : {},
    meta: {
      ...((isPlainObject(source.meta) ? source.meta : {})),
      fallback: Boolean(source.meta?.used_fallback ?? source.meta?.fallback),
      needs_review: source.meta?.needs_review !== false
    },
    draft_id: optionalText(record?.draft_id),
    status,
    version: Number.isInteger(record?.version) && record.version >= 1 ? record.version : 1,
    published_goal_id: optionalText(record?.published_goal_id) || null,
    published_run_id: optionalText(record?.published_run_id) || null,
    created_at: optionalText(record?.created_at) || null,
    updated_at: optionalText(record?.updated_at) || null,
    published_at: optionalText(record?.published_at) || null
  }
}

/**
 * Prepare an Advisor draft for the PATCH contract without leaking view-only fields.
 * Input: A locally edited normalized Plan Draft.
 * Output: The complete canonical payload accepted by PlanDraftService.
 * Called by: Advisor before explicit save and indirectly by its publish workflow.
 * Side effects: None.
 * Failure: Throws on invalid local shape; backend validation remains authoritative.
 * Invariant: Dependencies are acyclic locally and all immutable resource identifiers are excluded.
 */
export function buildPlanDraftPayload(draft) {
  const normalized = normalizePlanDraft(draft, draft?.run?.mode || 'assisted')
  assertAcyclicSteps(normalized.run.steps)
  return {
    goal: normalized.goal,
    run: normalized.run,
    summary: normalized.summary,
    estimated_duration: normalized.estimated_duration,
    context: normalized.context,
    meta: {
      ...normalized.meta,
      used_fallback: Boolean(normalized.meta?.fallback)
    }
  }
}

/**
 * Create a retry-stable publication key for one server-owned Plan Draft.
 * Input: A non-empty draft id.
 * Output: Browser-generated opaque idempotency key safe to reuse after request uncertainty.
 * Called by: Advisor when the user first confirms publication.
 * Side effects: Uses browser randomness when available.
 * Failure: Falls back to a timestamp/random suffix in older web views.
 * Invariant: The key is scoped to the current draft and never stored as publication truth.
 */
export function createPublicationKey(draftId) {
  const id = requiredText(draftId, '方案缺少服务端标识，请重新打开后再试。')
  const entropy = globalThis.crypto?.randomUUID?.() || (Date.now() + '-' + Math.random().toString(36).slice(2, 10))
  return 'plan-draft-' + id + '-' + entropy
}
