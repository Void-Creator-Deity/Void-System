export const STEP_RESULT_KIND_OPTIONS = [
  { label: '一般成果', value: 'result' },
  { label: '文档', value: 'document' },
  { label: '链接', value: 'link' },
  { label: '文件', value: 'file' },
  { label: '图片', value: 'image' }
]

function deliverableTitle(item) {
  if (typeof item === 'string') return item.trim()
  return String(item?.title || item?.name || '').trim()
}

export function declaredDeliverables(step = {}) {
  const items = step?.completion_criteria?.deliverables
  return Array.isArray(items) ? items.map(deliverableTitle).filter(Boolean) : []
}

export function createStepCompletionDraft(step = {}) {
  const deliverables = declaredDeliverables(step)
  return {
    note: '',
    includeResult: deliverables.length > 0,
    resultTitle: deliverables[0] || '',
    resultKind: 'result',
    resultUrl: ''
  }
}

export function buildStepCompletionInput(draft = {}, step = {}) {
  const note = String(draft.note || '').trim()
  if (!note) throw new Error('请填写完成说明。')

  const input = {
    output_data: { summary: note },
    artifacts: []
  }

  if (!draft.includeResult) return input

  const title = String(draft.resultTitle || '').trim()
    || declaredDeliverables(step)[0]
    || `${String(step.title || '步骤').trim()}成果`

  input.artifacts.push({
    title: title.slice(0, 200),
    kind: String(draft.resultKind || 'result').trim().slice(0, 60) || 'result',
    uri: String(draft.resultUrl || '').trim().slice(0, 2000) || null,
    metadata: { source: 'user_step_completion' }
  })
  return input
}
