/** Friendly automation client backed by durable Triggers. */
import api, { apiRequest } from './index'

const asArray = (payload, key) => Array.isArray(payload) ? payload : (Array.isArray(payload?.[key]) ? payload[key] : [])
const triggerFrom = (payload) => payload?.trigger || payload

export const triggersApi = {
  async list() { return asArray(await apiRequest(api.get('/api/triggers')), 'triggers') },
  get(triggerId) { return apiRequest(api.get(`/api/triggers/${triggerId}`)).then(triggerFrom) },
  create(trigger) { return apiRequest(api.post('/api/triggers', trigger)).then(triggerFrom) },
  update(triggerId, updates) { return apiRequest(api.patch(`/api/triggers/${triggerId}`, updates)).then(triggerFrom) },
  remove(triggerId) { return apiRequest(api.delete(`/api/triggers/${triggerId}`)) },
  pause(triggerId) { return apiRequest(api.post(`/api/triggers/${triggerId}/pause`)).then(triggerFrom) },
  resume(triggerId) { return apiRequest(api.post(`/api/triggers/${triggerId}/resume`)).then(triggerFrom) },
  fire(triggerId, sourceKey, payload = {}) { return apiRequest(api.post(`/api/triggers/${triggerId}/fire`, { source_key: sourceKey, payload })) }
}

export default triggersApi
