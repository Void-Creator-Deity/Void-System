/**
 * 助手回复 Markdown → HTML（含思考链折叠），与系统精灵一致：默认折叠，点击 summary 展开。
 * 兼容 Qwen 系 `</redacted_thinking>` / `</redacted_thinking>` 与 `</redacted_thinking>` / `</redacted_thinking>`。
 */
import { marked } from "marked"

/** @typedef {'hide' | 'collapse' | 'expand'} ThinkDisplayMode */

/** 内部统一用的开闭标签（与历史 redacted 命名一致） */
const T_OPEN = "<redacted_thinking>"
const T_CLOSE = "</redacted_thinking>"

/**
 * 将常见模型思考标签统一到 T_OPEN / T_CLOSE，避免抽块失败导致思考全文摊在正文里。
 * @param {string} s
 */
function normalizeThinkTagNames(s) {
  let t = String(s)
  // Qwen / 常见：`</redacted_thinking>` `</redacted_thinking>`（字符串拼接避免部分环境误处理）
  const qOpen = "<" + "think" + ">"
  const qClose = "<" + "/" + "think" + ">"
  t = t.replace(new RegExp(qOpen.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), T_OPEN)
  t = t.replace(new RegExp(qClose.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), T_CLOSE)
  return t
}

/**
 * @param {string} text
 * @param {{ thinkMode?: ThinkDisplayMode, summaryLabel?: string }} [opts]
 * @returns {string}
 */
export function markdownToHtmlWithThink(text, opts = {}) {
  const thinkMode = opts.thinkMode ?? "collapse"
  const summaryLabel = opts.summaryLabel ?? "✨ 虚空模型思维逻辑"

  if (!text) return ""

  let processed = normalizeThinkTagNames(text)

  if (thinkMode === "hide") {
    processed = processed.replace(
      new RegExp(`${escapeRe(T_OPEN)}[\\s\\S]*?${escapeRe(T_CLOSE)}`, "gi"),
      ""
    )
    processed = processed.replace(new RegExp(escapeRe(T_OPEN), "gi"), "")
    processed = processed.replace(new RegExp(escapeRe(T_CLOSE), "gi"), "")
    return marked.parse(processed)
  }

  const openRe = new RegExp(escapeRe(T_OPEN), "gi")
  const closeRe = new RegExp(escapeRe(T_CLOSE), "gi")
  const openCount = (processed.match(openRe) || []).length
  let closeCount = (processed.match(closeRe) || []).length
  if (openCount > closeCount) {
    processed += "\n" + T_CLOSE
  }

  const thinkBlocks = []
  const blockRe = new RegExp(
    `${escapeRe(T_OPEN)}([\\s\\S]*?)${escapeRe(T_CLOSE)}`,
    "gi"
  )
  processed = processed.replace(blockRe, (_m, content) => {
    thinkBlocks.push(content)
    const id = thinkBlocks.length - 1
    return `\n\n%%%VOID_THINK_${id}%%%\n\n`
  })

  let html = marked.parse(processed)
  // marked 易把占位包在 <p> 里，导致 <details> 嵌套非法、折叠失效；先剥掉包裹
  html = html.replace(/<p>\s*(%%%VOID_THINK_\d+%%%)\s*<\/p>/gi, "$1")

  const openAttr = thinkMode === "expand" ? " open" : ""
  thinkBlocks.forEach((content, index) => {
    const renderBlock = marked.parse(content)
    html = html.replace(
      `%%%VOID_THINK_${index}%%%`,
      `<details class="void-think-box"${openAttr}><summary><span>${summaryLabel}</span></summary><div class="think-content">${renderBlock}</div></details>`
    )
  })

  return html
}

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

/**
 * 系统精灵 / 知识库 / 文档问答共用：默认折叠思考链。
 * @param {string} text
 * @returns {string}
 */
export function renderAssistantMarkdown(text) {
  if (!text) return ""
  try {
    return markdownToHtmlWithThink(text, { thinkMode: "collapse" })
  } catch (e) {
    console.error("Markdown 解析失败:", e)
    return `<pre class="void-markdown-fallback">${String(text)}</pre>`
  }
}
