import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { plansApi } from '@/api/plans'
import { documentApi } from '@/api/document'
import {
  BACKGROUND_WORK_STATE,
  planGenerationToBackgroundWork,
  knowledgeJobToBackgroundWork
} from '@/domain/backgroundWork'

const POLL_INTERVAL_MS = 1200

function readableError(error, fallback) {
  return error?.response?.data?.message || error?.response?.data?.detail || error?.message || fallback
}

function newestFirst(left, right) {
  return String(right?.updated_at || right?.created_at || '').localeCompare(String(left?.updated_at || left?.created_at || ''))
}

/**
 * Own recovery and polling for all authenticated durable background work.
 * Inputs: Owner-scoped plan and personal knowledge job snapshots from canonical APIs.
 * Outputs: Unified work records, active count, lookup helpers, cancellation, and retry actions.
 * Called by: Authenticated app lifecycle, plan submission, document upload/rebuild, and the progress drawer.
 * Side effects: Polls only while active server-owned work exists; browser state remains a transient render cache.
 * Failure: Preserves last verified snapshots and surfaces a readable refresh error without inventing client progress.
 * Invariant: The backend is the sole authority for lifecycle, progress, terminal result, retry, and cancellation.
 */
export const useBackgroundProgressStore = defineStore('backgroundProgress', () => {
  const planGenerationJobs = ref({})
  const knowledgeJobs = ref({})
  const isRefreshing = ref(false)
  const lastError = ref('')
  const isStarted = ref(false)
  const pollingTimer = ref(null)
  let refreshPromise = null

  const recentWork = computed(() => [
    ...Object.values(planGenerationJobs.value).map((job) => planGenerationToBackgroundWork(job)),
    ...Object.values(knowledgeJobs.value).map((job) => knowledgeJobToBackgroundWork(job))
  ].sort(newestFirst))
  const activeWork = computed(() => recentWork.value.filter((work) => work.state === BACKGROUND_WORK_STATE.ACTIVE))
  const activeCount = computed(() => activeWork.value.length)

  function clearPolling() {
    if (pollingTimer.value) {
      globalThis.clearTimeout(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function schedulePolling() {
    clearPolling()
    if (!isStarted.value || activeCount.value === 0) return
    pollingTimer.value = globalThis.setTimeout(() => {
      refresh({ silent: true }).catch(() => {})
    }, POLL_INTERVAL_MS)
  }

  /** Upsert a server-owned plan generation snapshot into the temporary render cache. */
  function upsertPlanGeneration(job) {
    const generationId = typeof job?.generation_id === 'string' ? job.generation_id.trim() : ''
    if (!generationId) throw new Error('Plan generation response has no generation id.')
    planGenerationJobs.value = { ...planGenerationJobs.value, [generationId]: job }
    schedulePolling()
    return job
  }

  /** Upsert a server-owned personal knowledge task snapshot into the temporary render cache. */
  function upsertKnowledgeJob(job) {
    const jobId = typeof job?.job_id === 'string' ? job.job_id.trim() : ''
    if (!jobId) throw new Error('Knowledge processing response has no job id.')
    knowledgeJobs.value = { ...knowledgeJobs.value, [jobId]: job }
    schedulePolling()
    return job
  }

  /** Return one cached plan snapshot without a hidden network request. */
  function getPlanGeneration(generationId) {
    const id = typeof generationId === 'string' ? generationId.trim() : ''
    return id ? planGenerationJobs.value[id] || null : null
  }

  /** Return one cached knowledge task snapshot without a hidden network request. */
  function getKnowledgeJob(jobId) {
    const id = typeof jobId === 'string' ? jobId.trim() : ''
    return id ? knowledgeJobs.value[id] || null : null
  }

  /**
   * Recover all recent durable work in parallel from canonical server endpoints.
   * Inputs: Optional silent flag for timer-driven polling.
   * Outputs: Current server snapshots for both work families.
   * Called by: App start, document/plan entry points, and active-work polling.
   * Side effects: Replaces both browser caches only after both authoritative reads succeed.
   * Failure: Keeps prior caches intact and rejects the original transport error.
   */
  async function refresh({ silent = false } = {}) {
    if (refreshPromise) return refreshPromise
    isRefreshing.value = true
    if (!silent) lastError.value = ''
    refreshPromise = Promise.all([
      plansApi.listGenerations({ timeout: 15000 }),
      documentApi.listKnowledgeJobs(30)
    ])
      .then(([planResponse, knowledgeResponse]) => {
        const nextPlans = {}
        for (const job of Array.isArray(planResponse?.items) ? planResponse.items : []) {
          const id = typeof job?.generation_id === 'string' ? job.generation_id.trim() : ''
          if (id) nextPlans[id] = job
        }
        const nextKnowledge = {}
        for (const job of Array.isArray(knowledgeResponse?.jobs) ? knowledgeResponse.jobs : []) {
          const id = typeof job?.job_id === 'string' ? job.job_id.trim() : ''
          if (id) nextKnowledge[id] = job
        }
        planGenerationJobs.value = nextPlans
        knowledgeJobs.value = nextKnowledge
        return { plans: Object.values(nextPlans), knowledge: Object.values(nextKnowledge) }
      })
      .catch((error) => {
        lastError.value = readableError(error, '后台进度暂时无法更新。')
        throw error
      })
      .finally(() => {
        refreshPromise = null
        isRefreshing.value = false
        schedulePolling()
      })
    return refreshPromise
  }

  /** Start refresh recovery after authentication succeeds. */
  function start() {
    isStarted.value = true
    return refresh()
  }

  /** Stop polling and clear only transient browser snapshots at logout. */
  function stop() {
    isStarted.value = false
    clearPolling()
    planGenerationJobs.value = {}
    knowledgeJobs.value = {}
    lastError.value = ''
  }

  /** Request cooperative cancellation using the matching canonical job API. */
  async function cancelWork(work) {
    if (work?.kind === 'plan_generation') return upsertPlanGeneration(await plansApi.cancelGeneration(work.source_id, { timeout: 15000 }))
    if (work?.kind === 'knowledge_processing') return upsertKnowledgeJob(await documentApi.cancelKnowledgeJob(work.source_id))
    throw new Error('Unsupported background work type.')
  }

  /** Retry only completed-failure/cancelled knowledge work from its immutable stored source. */
  async function retryKnowledgeJob(jobId) {
    return upsertKnowledgeJob(await documentApi.retryKnowledgeJob(jobId))
  }

  return {
    recentWork,
    activeWork,
    activeCount,
    isRefreshing,
    lastError,
    isStarted,
    start,
    stop,
    refresh,
    upsertPlanGeneration,
    upsertKnowledgeJob,
    getPlanGeneration,
    getKnowledgeJob,
    cancelWork,
    retryKnowledgeJob
  }
})
