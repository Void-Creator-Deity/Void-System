export function streamEventDelta(previousText, event) {
  if (typeof event?.delta === 'string') return event.delta

  const content = typeof event?.content === 'string' ? event.content : ''
  if (!content || previousText.endsWith(content)) return ''
  if (content.startsWith(previousText)) return content.slice(previousText.length)
  return content
}

export function eventData(rawEvent) {
  return rawEvent
    .split(/\r?\n/)
    .filter(line => line.startsWith('data:'))
    .map(line => line.slice(5).trim())
    .join('\n')
}

export function consumeCompleteSseEvents(buffer, onEvent) {
  let remaining = buffer
  let separator = /\r?\n\r?\n/.exec(remaining)

  while (separator) {
    const rawEvent = remaining.slice(0, separator.index)
    remaining = remaining.slice(separator.index + separator[0].length)
    onEvent(rawEvent)
    separator = /\r?\n\r?\n/.exec(remaining)
  }

  return remaining
}
