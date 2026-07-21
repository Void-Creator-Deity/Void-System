import test from 'node:test'
import assert from 'node:assert/strict'

import { consumeCompleteSseEvents, eventData, streamEventDelta } from '../src/api/streaming.js'

test('cumulative stream content is converted to the missing suffix', () => {
  let text = ''
  for (const content of ['Hel', 'Hello', 'Hello, world']) {
    const delta = streamEventDelta(text, { content })
    text += delta
  }

  assert.equal(text, 'Hello, world')
})

test('explicit backend delta is append-only', () => {
  let text = ''
  for (const delta of ['Hel', 'lo', '!']) {
    const next = streamEventDelta(text, { delta })
    text += next
  }

  assert.equal(text, 'Hello!')
})

test('already-consumed content does not replay', () => {
  assert.equal(streamEventDelta('Hello', { content: 'Hello' }), '')
})

test('SSE events are consumed once across arbitrary network chunks', () => {
  const events = []
  let buffer = ''

  for (const chunk of [
    'event: message\ndata: {"content":"Hel"}\n\n',
    'event: message\ndata: {"content":"Hello"}\n\n',
    'event: message\ndata: {"content":"Hello, world"}',
    '\n\n'
  ]) {
    buffer = consumeCompleteSseEvents(buffer + chunk, rawEvent => {
      events.push(JSON.parse(eventData(rawEvent)))
    })
  }

  assert.equal(buffer, '')
  assert.deepEqual(events, [
    { content: 'Hel' },
    { content: 'Hello' },
    { content: 'Hello, world' }
  ])
})
