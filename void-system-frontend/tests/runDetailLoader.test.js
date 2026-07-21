import assert from 'node:assert/strict'
import test from 'node:test'

import { isTerminalRun, loadRunDetail, loadRunDetailResource } from '../src/domain/runDetailLoader.js'

function createApi(overrides = {}) {
  const calls = []
  const api = {
    calls,
    async get(runId) { calls.push(['get', runId]); return { run_id: runId, status: 'running' } },
    async events(runId) { calls.push(['events', runId]); return [{ event_id: 'event-1' }] },
    async review(runId) { calls.push(['review', runId]); return { summary: { artifact_count: 1 } } },
    ...overrides
  }
  return api
}

test('terminal status detection is shared with the workspace', () => {
  assert.equal(isTerminalRun({ status: 'completed' }), true)
  assert.equal(isTerminalRun({ status: 'cancelled' }), true)
  assert.equal(isTerminalRun({ status: 'running' }), false)
})

test('unknown optional resources are programming errors', async () => {
  const api = createApi()
  await assert.rejects(
    loadRunDetailResource(api, { run_id: 'run-1', status: 'running' }, 'unknown'),
    /Unknown Run detail resource/
  )
})

test('loads the required Run and every optional resource', async () => {
  const api = createApi()
  const detail = await loadRunDetail(api, 'run-1')

  assert.equal(detail.run.run_id, 'run-1')
  assert.equal(detail.events.length, 1)
  assert.equal(detail.review.summary.artifact_count, 1)
  assert.deepEqual(detail.errors, { events: null, review: null })
  assert.equal('commands' in detail, false)
})

test('event failure preserves the Run and review', async () => {
  const failure = new Error('events unavailable')
  const api = createApi({ async events() { throw failure } })
  const detail = await loadRunDetail(api, 'run-1')

  assert.equal(detail.run.run_id, 'run-1')
  assert.deepEqual(detail.events, [])
  assert.equal('commands' in detail, false)
  assert.ok(detail.review)
  assert.equal(detail.errors.events, failure)
})

test('review failure preserves the Run and event history', async () => {
  const failure = new Error('review unavailable')
  const api = createApi({ async review() { throw failure } })
  const detail = await loadRunDetail(api, 'run-1')

  assert.equal(detail.run.run_id, 'run-1')
  assert.equal(detail.events.length, 1)
  assert.equal(detail.review, null)
  assert.equal(detail.errors.review, failure)
})

test('Run detail never requests retired commands', async () => {
  const api = createApi({ async get(runId) { return { run_id: runId, status: 'completed' } } })
  const detail = await loadRunDetail(api, 'run-1')

  assert.equal('commands' in detail, false)
  assert.equal(api.calls.some(([name]) => name === 'commands'), false)
})

test('required Run failure rejects the aggregate load', async () => {
  const failure = new Error('Run unavailable')
  const api = createApi({ async get() { throw failure } })

  await assert.rejects(loadRunDetail(api, 'run-1'), failure)
})

test('a single optional resource can be retried without refetching the Run', async () => {
  const api = createApi()
  const run = { run_id: 'run-1', status: 'running' }
  const result = await loadRunDetailResource(api, run, 'events')

  assert.equal(result.error, null)
  assert.equal(result.value.length, 1)
  assert.equal(api.calls.some(([name]) => name === 'get'), false)
})
