import test from 'node:test'
import assert from 'node:assert/strict'

const storage = new Map([
  ['access_token', 'expired-access-token'],
  ['refresh_token', 'refresh-token']
])

globalThis.localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: key => storage.delete(key)
}

const { default: api } = await import('../src/api/index.js')
const { streamPersona } = await import('../src/api/ai.js')

test('stream chat refreshes an expired access token once before retrying', async (t) => {
  const originalFetch = globalThis.fetch
  const originalPost = api.post
  let fetchCalls = 0
  let refreshCalls = 0

  t.after(() => {
    globalThis.fetch = originalFetch
    api.post = originalPost
  })

  api.post = async (url, body) => {
    refreshCalls += 1
    assert.equal(url, '/api/auth/refresh')
    assert.deepEqual(body, { refresh_token: 'refresh-token' })
    return {
      data: {
        success: true,
        data: {
          access_token: 'renewed-access-token',
          refresh_token: 'renewed-refresh-token',
          user: { user_id: 'user-1' }
        }
      }
    }
  }

  globalThis.fetch = async (_url, options) => {
    fetchCalls += 1
    if (fetchCalls === 1) {
      assert.equal(options.headers.Authorization, 'Bearer expired-access-token')
      return new Response(JSON.stringify({ message: 'expired' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      })
    }

    assert.equal(options.headers.Authorization, 'Bearer renewed-access-token')
    return new Response(
      'event: message\ndata: {"delta":"OK","finished":false}\n\nevent: done\ndata: {"finished":true}\n\n',
      { status: 200, headers: { 'Content-Type': 'text/event-stream' } }
    )
  }

  let text = ''
  await streamPersona('What is next?', 'session-1', delta => { text += delta })

  assert.equal(text, 'OK')
  assert.equal(fetchCalls, 2)
  assert.equal(refreshCalls, 1)
  assert.equal(storage.get('access_token'), 'renewed-access-token')
})
