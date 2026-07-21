/** Personal context and system companion client. */
import api, { apiRequest } from './index'

const fromKey = (payload, key, fallback) => payload?.[key] ?? fallback

export const companionApi = {
  async getSettings() {
    const data = await apiRequest(api.get('/api/companion/settings'))
    return fromKey(data, 'settings', {})
  },

  async updateSettings(updates) {
    const data = await apiRequest(api.put('/api/companion/settings', updates))
    return fromKey(data, 'settings', {})
  },

  async getBriefing(itemBudget = 24) {
    const data = await apiRequest(api.get('/api/companion/briefing', { params: { item_budget: itemBudget } }))
    return fromKey(data, 'briefing', {})
  },

  async getContext(params = {}) {
    const data = await apiRequest(api.get('/api/companion/context', { params }))
    return fromKey(data, 'context', {})
  },

  async getProfile() {
    const data = await apiRequest(api.get('/api/companion/profile'))
    return fromKey(data, 'profile', { facets: [], patterns: [], hypotheses: [], signals: [], sources: {} })
  },

  async inferProfile(options = {}) {
    const data = await apiRequest(api.post('/api/companion/profile/hypotheses/infer', options))
    return data ?? { hypotheses: [] }
  },

  async reviewHypothesis(hypothesisId, decision, value = null, reason = '') {
    return apiRequest(api.patch(`/api/companion/profile/hypotheses/${hypothesisId}/review`, {
      decision,
      value,
      reason
    }))
  },

  async listMemories(params = {}) {
    const data = await apiRequest(api.get('/api/companion/memories', { params }))
    return fromKey(data, 'memories', [])
  },

  async createMemory(memory) {
    const data = await apiRequest(api.post('/api/companion/memories', memory))
    return fromKey(data, 'memory', data)
  },

  async updateMemory(memoryId, updates) {
    const data = await apiRequest(api.patch(`/api/companion/memories/${memoryId}`, updates))
    return fromKey(data, 'memory', data)
  },

  deleteMemory(memoryId) {
    return apiRequest(api.delete(`/api/companion/memories/${memoryId}`))
  },

  async listAccessLog(limit = 50) {
    const data = await apiRequest(api.get('/api/companion/access-log', { params: { limit } }))
    return fromKey(data, 'records', [])
  }
}

export default companionApi
