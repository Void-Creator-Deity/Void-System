/** Canonical Run, Step, Approval, and steering client. */
import api, { apiRequest } from './index'

const asArray = (payload, key) => Array.isArray(payload) ? payload : (Array.isArray(payload?.[key]) ? payload[key] : [])
const runFrom = (payload) => payload?.run || payload

export const runsApi = {
  async list(params = {}) {
    return asArray(await apiRequest(api.get('/api/runs', { params })), 'runs')
  },

  async get(runId) {
    return runFrom(await apiRequest(api.get(`/api/runs/${runId}`)))
  },

  async create(goalId, specification = {}) {
    return runFrom(await apiRequest(api.post(`/api/goals/${goalId}/runs`, specification)))
  },

  async events(runId) {
    return asArray(await apiRequest(api.get(`/api/runs/${runId}/events`)), 'events')
  },

  async review(runId) {
    const data = await apiRequest(api.get(`/api/runs/${runId}/review`))
    return data?.review || data
  },

  async saveReview(runId, values) {
    const data = await apiRequest(api.put(`/api/runs/${runId}/review`, values))
    return data?.review || data
  },

  start(runId) { return apiRequest(api.post(`/api/runs/${runId}/start`)).then(runFrom) },
  pause(runId) { return apiRequest(api.post(`/api/runs/${runId}/pause`)).then(runFrom) },
  resume(runId) { return apiRequest(api.post(`/api/runs/${runId}/resume`)).then(runFrom) },
  cancel(runId, reason = '') { return apiRequest(api.post(`/api/runs/${runId}/cancel`, { reason: reason || null })).then(runFrom) },

  retry(runId) { return apiRequest(api.post(`/api/runs/${runId}/retry`)).then(runFrom) },
  startStep(runId, stepId) { return apiRequest(api.post(`/api/runs/${runId}/steps/${stepId}/start`)).then(runFrom) },
  completeStep(runId, stepId, body = {}) { return apiRequest(api.post(`/api/runs/${runId}/steps/${stepId}/complete`, { output_data: body.output_data || {}, artifacts: body.artifacts || [] })).then(runFrom) },
  skipStep(runId, stepId) { return apiRequest(api.post(`/api/runs/${runId}/steps/${stepId}/skip`)).then(runFrom) },
  failStep(runId, stepId, errorSummary) { return apiRequest(api.post(`/api/runs/${runId}/steps/${stepId}/fail`, { error_summary: errorSummary })).then(runFrom) },
  retryStep(runId, stepId) { return apiRequest(api.post(`/api/runs/${runId}/steps/${stepId}/retry`)).then(runFrom) },

  resolveApproval(approvalId, decision, note = '') {
    return apiRequest(api.post(`/api/approvals/${approvalId}/resolve`, { decision, note: note || null })).then(runFrom)
  },

  async listCommands(runId, params = {}) {
    return asArray(await apiRequest(api.get(`/api/runs/${runId}/commands`, { params })), 'commands')
  },

  async submitCommand(runId, command) {
    const data = await apiRequest(api.post(`/api/runs/${runId}/commands`, command))
    return data?.command || data
  },

  async acknowledgeCommand(runId, commandId) {
    const data = await apiRequest(api.post(`/api/runs/${runId}/commands/${commandId}/acknowledge`))
    return data?.command || data
  }
}

export default runsApi
