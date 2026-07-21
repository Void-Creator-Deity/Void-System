/**
 * Growth Profile API
 *
 * Keeps durable growth points and self-managed attributes behind a
 * product-facing interface with one canonical backend contract.
 */

import api, { apiRequest } from './index'

export const growthProfileApi = {
  getGrowthPoints() {
    return apiRequest(api.get('/api/growth/points/balance'))
  },

  listGrowthPointActivity(params = {}) {
    return apiRequest(api.get('/api/growth/points/activity', { params }))
  },

  getGrowthPointSummary() {
    return apiRequest(api.get('/api/growth/points/summary'))
  },

  listAttributes() {
    return apiRequest(api.get('/api/attributes'))
  },

  createAttribute(attribute) {
    return apiRequest(api.post('/api/attributes', attribute))
  },

  updateAttribute(attributeId, updates) {
    return apiRequest(api.put(`/api/attributes/${attributeId}`, updates))
  },

  deleteAttribute(attributeId) {
    return apiRequest(api.delete(`/api/attributes/${attributeId}`))
  }
}

export default growthProfileApi
