/** Reviewable Goal and Run planning client. */
import api, { apiRequest } from './index'

export const plansApi = {
  create(topic, options = {}) {
    return apiRequest(api.post('/api/plans', {
      topic,
      execution_mode: options.executionMode || 'assisted',
      max_steps: options.maxSteps || 8,
      advisor_prefs: options.preferences || {}
    }, options.config || {}))
  }
}

export default plansApi
