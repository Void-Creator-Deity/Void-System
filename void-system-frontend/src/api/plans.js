/**
 * Planning API client for durable generation jobs and server-owned Plan Drafts.
 *
 * Input: Authenticated browser requests and DTOs defined by the Planning HTTP contract.
 * Output: Authoritative generation or draft snapshots from the response envelope.
 * Called by: Advisor and the future global background-progress surface.
 * Side effects: Performs network writes only; it never creates browser-local durable plan state.
 * Failure: Propagates normalized axios errors so callers can branch on error_code.
 * Invariant: First-party planning UI uses Plan Draft endpoints for edits and publication.
 */
import api, { apiRequest } from './index'

export const plansApi = {
  start(topic, options = {}) {
    return apiRequest(api.post('/api/plan-generations', {
      topic,
      execution_mode: options.executionMode || 'assisted',
      max_steps: options.maxSteps || 8,
      advisor_prefs: options.preferences || {}
    }, options.config || {}))
  },

  listGenerations(config = {}) {
    return apiRequest(api.get('/api/plan-generations', config))
  },

  getGeneration(generationId, config = {}) {
    return apiRequest(api.get(`/api/plan-generations/${generationId}`, config))
  },

  cancelGeneration(generationId, config = {}) {
    return apiRequest(api.delete(`/api/plan-generations/${generationId}`, config))
  },

  /**
   * Load owner-scoped persisted Plan Draft history.
   * Input: Optional axios request configuration.
   * Output: `{ items }` with public draft summaries/payloads from the server.
   * Called by: Advisor initial recovery and its recent-drafts drawer.
   * Side effects: Performs a read request only.
   * Failure: The caller decides whether temporary history unavailability should block editing.
   * Invariant: The returned list is the durable source of truth, never localStorage.
   */
  listDrafts(config = {}) {
    return apiRequest(api.get('/api/plan-drafts', config))
  },

  /**
   * Read one editable Plan Draft by its server identifier.
   * Input: Owner-scoped draft id and optional request configuration.
   * Output: The current draft payload, version, status, and optional published resource ids.
   * Called by: Advisor when a generation completes or a history item is reopened.
   * Side effects: Performs a read request only.
   * Failure: Missing/foreign drafts surface the stable PLAN_DRAFT_NOT_FOUND error.
   * Invariant: The returned version must be sent back on the next update.
   */
  getDraft(draftId, config = {}) {
    return apiRequest(api.get(`/api/plan-drafts/${draftId}`, config))
  },

  /**
   * Persist one full Plan Draft edit using optimistic concurrency.
   * Input: Draft id, normalized editable payload, rendered version, optional request config.
   * Output: The incremented authoritative draft snapshot.
   * Called by: Advisor's explicit "完成调整" action.
   * Side effects: Replaces the server payload and increments its version.
   * Failure: PLAN_DRAFT_VERSION_CONFLICT requires the caller to reload instead of overwriting.
   * Invariant: Published drafts cannot be edited and the page never performs a partial local save.
   */
  updateDraft(draftId, payload, expectedVersion, config = {}) {
    return apiRequest(api.patch(`/api/plan-drafts/${draftId}`, {
      payload,
      expected_version: expectedVersion
    }, config))
  },

  /**
   * Atomically publish a persisted draft into the canonical Goal/Run model.
   * Input: Draft id and a stable idempotency key reused for a browser/network retry.
   * Output: Published draft snapshot containing authoritative Goal and Run ids.
   * Called by: Advisor's confirmation action after the user reviews a draft.
   * Side effects: The backend transaction creates Goal, Run, Steps, dependencies, and initial events.
   * Failure: Stable PLAN_DRAFT_* errors are propagated; no client-side recovery chain is attempted.
   * Invariant: Same draft/key resolves to one published Run, never a duplicate.
   */
  publishDraft(draftId, idempotencyKey, config = {}) {
    return apiRequest(api.post(`/api/plan-drafts/${draftId}/publish`, {
      idempotency_key: idempotencyKey
    }, config))
  }
}

export default plansApi
