/** Goal lifecycle client. */
import api, { apiRequest } from './index'

const asArray = (payload, key) => Array.isArray(payload) ? payload : (Array.isArray(payload?.[key]) ? payload[key] : [])

export const goalsApi = {
  async list(params = {}) {
    return asArray(await apiRequest(api.get('/api/goals', { params })), 'goals')
  },

  async get(goalId) {
    const data = await apiRequest(api.get(`/api/goals/${goalId}`))
    return data?.goal ? data : { goal: data, runs: [] }
  },

  async create(goal) {
    const data = await apiRequest(api.post('/api/goals', goal))
    return data?.goal || data
  },

  async update(goalId, updates) {
    const data = await apiRequest(api.patch(`/api/goals/${goalId}`, updates))
    return data?.goal || data
  }
}

export default goalsApi
