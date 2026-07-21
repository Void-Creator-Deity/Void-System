/**
 * View-domain mapping for durable backend-owned work.
 * Browser state is only a render cache: the server owns lifecycle transitions, progress, results, retries, and cancellations.
 */
export const BACKGROUND_WORK_KIND = Object.freeze({
  PLAN_GENERATION: 'plan_generation',
  KNOWLEDGE_PROCESSING: 'knowledge_processing'
})

export const BACKGROUND_WORK_STATE = Object.freeze({
  ACTIVE: 'active',
  READY: 'ready',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
})

function text(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function boundedProgress(value) {
  return Math.max(0, Math.min(100, Number(value) || 0))
}

function lifecycleState(status, readyStatuses) {
  if (['queued', 'processing', 'generating', 'cancelling'].includes(status)) return BACKGROUND_WORK_STATE.ACTIVE
  if (readyStatuses.includes(status)) return BACKGROUND_WORK_STATE.READY
  if (status === 'failed') return BACKGROUND_WORK_STATE.FAILED
  return BACKGROUND_WORK_STATE.CANCELLED
}

/**
 * Convert a public Plan Generation snapshot into the common background-work model.
 * Inputs: Durable planning snapshot from plansApi.
 * Outputs: Render-safe record with server state unchanged.
 * Called by: Background progress store after submission, recovery, cancellation, and polling.
 * Side effects: None.
 * Failure: Throws for a missing generation id because that is a backend contract violation.
 */
export function planGenerationToBackgroundWork(job) {
  const generationId = text(job?.generation_id)
  if (!generationId) throw new Error('计划生成任务缺少服务端标识。')
  const status = text(job?.status) || 'queued'
  return {
    work_id: `${BACKGROUND_WORK_KIND.PLAN_GENERATION}:${generationId}`,
    kind: BACKGROUND_WORK_KIND.PLAN_GENERATION,
    source_id: generationId,
    state: lifecycleState(status, ['ready']),
    status,
    stage: text(job?.stage) || 'queued',
    progress: boundedProgress(job?.progress),
    title: text(job?.topic) || 'Preparing an action plan',
    description: text(job?.error_message),
    result_ref: text(job?.draft_id) ? { draft_id: text(job.draft_id) } : null,
    created_at: text(job?.created_at) || null,
    updated_at: text(job?.updated_at) || null,
    raw: job
  }
}

/**
 * Convert a personal knowledge job into the same background-work read model.
 * Inputs: Owner-scoped durable ingestion/rebuild snapshot from documentApi.
 * Outputs: Render-safe record which never exposes worker lease or vector internals.
 * Called by: Background progress store after upload, rebuild, recovery, cancellation, and retry.
 * Side effects: None.
 * Failure: Throws for a missing job id because client progress cannot identify it safely.
 */
export function knowledgeJobToBackgroundWork(job) {
  const jobId = text(job?.job_id)
  if (!jobId) throw new Error('知识处理任务缺少服务端标识。')
  const status = text(job?.status) || 'queued'
  return {
    work_id: `${BACKGROUND_WORK_KIND.KNOWLEDGE_PROCESSING}:${jobId}`,
    kind: BACKGROUND_WORK_KIND.KNOWLEDGE_PROCESSING,
    source_id: jobId,
    state: lifecycleState(status, ['completed']),
    status,
    stage: text(job?.stage) || 'queued',
    progress: boundedProgress(job?.progress),
    title: text(job?.document_title) || text(job?.document_name) || 'Personal knowledge material',
    description: text(job?.error_message),
    result_ref: text(job?.document_id) ? { document_id: text(job.document_id) } : null,
    created_at: text(job?.created_at) || null,
    updated_at: text(job?.updated_at) || null,
    raw: job
  }
}

/**
 * Produce short human-facing copy without revealing queues, leases, providers, or vector storage.
 * Inputs: Normalized durable background work record.
 * Outputs: A title and explanation suited to compact progress UI.
 * Called by: BackgroundProgressDrawer and page-level pending states.
 * Side effects: None.
 */
export function backgroundWorkPresentation(work) {
  if (work?.kind === BACKGROUND_WORK_KIND.KNOWLEDGE_PROCESSING) {
    if (work.state === BACKGROUND_WORK_STATE.READY) return { title: '资料已准备好', copy: '这份资料现在可以用于个人知识问答。' }
    if (work.state === BACKGROUND_WORK_STATE.FAILED) return { title: '资料处理未完成', copy: work.description || '这份资料可以重试，原始文件仍会保留。' }
    if (work.state === BACKGROUND_WORK_STATE.CANCELLED) return { title: '资料处理已停止', copy: '原始文件仍在资料库中，可以稍后重新处理。' }
    const stages = {
      queued: { title: '资料已加入处理', copy: '资料已安全保存，正在等待开始处理。' },
      preparing: { title: '正在准备资料', copy: '正在确认资料内容和处理条件。' },
      reading_source: { title: '正在读取资料', copy: '正在读取已保存的原始文件。' },
      extracting_content: { title: '正在提取内容', copy: '正在提取可供后续检索使用的内容。' },
      understanding_image: { title: '正在理解图片', copy: '正在整理图片中的可用信息。' },
      building_search_index: { title: '正在整理资料', copy: '正在将内容整理为可提问的知识。' },
      finalizing: { title: '正在完成资料准备', copy: '正在核对处理结果并保存。' }
    }
    return stages[work.stage] || { title: '正在处理资料', copy: '处理仍在后台进行，可以继续使用其他页面。' }
  }
  if (work?.kind === BACKGROUND_WORK_KIND.PLAN_GENERATION) {
    if (work.state === BACKGROUND_WORK_STATE.READY) return { title: '方案已准备好', copy: '可以打开并调整方案，再决定是否开始推进。' }
    if (work.state === BACKGROUND_WORK_STATE.FAILED) return { title: '方案未能生成', copy: work.description || '这次处理没有得到可用结果。' }
    if (work.state === BACKGROUND_WORK_STATE.CANCELLED) return { title: '方案生成已停止', copy: '这次请求不会再写入新的方案。' }
    const stages = {
      queued: { title: '方案已提交', copy: '正在等待生成服务开始处理。' },
      preparing_context: { title: '正在整理已确认资料', copy: '正在读取与目标相关且允许使用的信息。' },
      generating_steps: { title: '正在生成可执行步骤', copy: '正在生成方案，完成后会检查内容完整性。' },
      checking_result: { title: '正在核对方案', copy: '正在检查目标、步骤和完成条件是否完整。' }
    }
    return stages[work.stage] || { title: '正在生成方案', copy: '处理仍在后台进行，可以继续使用其他页面。' }
  }
  return { title: '正在处理', copy: '这项工作仍在后台进行。' }
}
