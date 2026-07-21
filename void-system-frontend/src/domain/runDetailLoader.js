const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled'])
const RESOURCE_NAMES = new Set(['events', 'review'])

export function isTerminalRun(run) {
  return TERMINAL_STATUSES.has(run?.status)
}

function resourceRequest(runsApi, run, resource) {
  if (resource === 'events') return runsApi.events(run.run_id)
  if (resource === 'review') return runsApi.review(run.run_id)
  throw new TypeError(`Unknown Run detail resource: ${resource}`)
}

export async function loadRunDetailResource(runsApi, run, resource) {
  if (!RESOURCE_NAMES.has(resource)) throw new TypeError(`Unknown Run detail resource: ${resource}`)
  try {
    return { value: await resourceRequest(runsApi, run, resource), error: null }
  } catch (error) {
    return { value: resource === 'review' ? null : [], error }
  }
}

export async function loadRunDetail(runsApi, runId, options = {}) {
  const run = options.run || await runsApi.get(runId)
  const [events, review] = await Promise.all([
    loadRunDetailResource(runsApi, run, 'events'),
    loadRunDetailResource(runsApi, run, 'review')
  ])

  return {
    run,
    events: events.value,
    review: review.value,
    errors: {
      events: events.error,
      review: review.error
    }
  }
}
