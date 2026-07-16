const ARTIFACT_KIND_LABELS = {
  result: '一般成果',
  document: '文档',
  link: '链接',
  file: '文件',
  image: '图片'
}

export function artifactKindLabel(kind) {
  return ARTIFACT_KIND_LABELS[String(kind || '').trim()] || '成果'
}

export function mergeDeclaredDeliverables(items = []) {
  const deliverables = new Map()

  for (const item of Array.isArray(items) ? items : []) {
    const title = String(item?.title || '').trim()
    if (!title) continue

    const key = title.toLocaleLowerCase()
    const existing = deliverables.get(key)
    if (!existing) {
      deliverables.set(key, {
        ...item,
        title,
        recorded: Boolean(item?.recorded),
        occurrenceCount: 1
      })
      continue
    }

    existing.recorded = existing.recorded && Boolean(item?.recorded)
    existing.occurrenceCount += 1
  }

  return [...deliverables.values()]
}
