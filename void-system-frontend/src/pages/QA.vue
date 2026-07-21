<template>
  <section class="knowledge-page">
    <header class="knowledge-page__header">
      <div>
        <p class="eyebrow">知识问答</p>
        <h1>从资料馆里找到答案</h1>
        <p>默认使用你的上传资料和已加入的共享馆藏，回答会保留可追溯的来源。</p>
      </div>
      <el-button :icon="DocumentAdd" plain @click="router.push('/documents')">打开资料馆</el-button>
    </header>

    <div class="knowledge-main">
      <form class="ask-form" @submit.prevent="ask">
        <div class="ask-form__heading">
          <div>
            <label for="knowledge-question">你想弄清什么？</label>
            <p>资料馆范围会随你的收藏和上传自动更新。</p>
          </div>
          <div class="library-scope-switch">
            <span>
              <strong>全局共享馆藏</strong>
              <small>{{ includeGlobalShared ? '本次也检索尚未加入的共享资料' : '只检索资料馆内的资料' }}</small>
            </span>
            <el-switch v-model="includeGlobalShared" aria-label="扩展到全部共享馆藏" />
          </div>
        </div>

        <el-input
          id="knowledge-question"
          v-model="question"
          placeholder="围绕资料馆中的内容提问"
          type="textarea"
          :autosize="{ minRows: 4, maxRows: 8 }"
          resize="none"
          :disabled="isLoading"
          @keydown.enter.exact.prevent="ask"
        />

        <div class="ask-form__footer">
          <span>{{ includeGlobalShared ? '本次回答会额外查看全部共享馆藏，不会将资料复制到你的资料馆。' : '本次只使用你的上传资料和已加入的共享馆藏。' }}</span>
          <el-button type="primary" native-type="submit" :icon="Promotion" :loading="isLoading" :disabled="!question.trim()">
            开始提问
          </el-button>
        </div>
      </form>

      <div v-if="isLoading" class="answer-loading" aria-live="polite">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在检索资料馆并整理答案...</span>
      </div>

      <div v-else-if="errorMessage" class="answer-error" role="alert">
        <el-icon><WarningFilled /></el-icon>
        <div>
          <h2>这次没有连上知识服务</h2>
          <p>{{ errorMessage }}</p>
        </div>
        <el-button :icon="Refresh" @click="ask">重新提问</el-button>
      </div>

      <article v-else-if="result" class="answer-panel">
        <header class="answer-panel__header">
          <div>
            <p class="eyebrow">{{ includeGlobalShared ? '已扩展至共享馆藏' : '资料馆范围' }}</p>
            <h2>回答</h2>
          </div>
          <span class="support-status" :class="{ 'support-status--limited': needsMoreContext }">{{ supportLabel }}</span>
        </header>

        <div class="answer-panel__body markdown-body" v-html="answerHtml"></div>

        <p v-if="needsMoreContext" class="answer-context-note">
          当前资料还不足以支撑更具体的回答。补充相关资料，加入需要的共享馆藏，或打开全局共享馆藏后再试。
        </p>

        <footer v-if="result.sources.length" class="sources">
          <h3>来源</h3>
          <ul>
            <li v-for="source in result.sources" :key="sourceKey(source)">
              <el-icon><Document /></el-icon>
              <div>
                <strong>{{ source.title || '未命名资料' }}</strong>
                <small>{{ source.source === 'shared' ? '共享馆藏' : '我的上传' }}<template v-if="source.tags?.length"> · {{ source.tags.join(' / ') }}</template></small>
              </div>
            </li>
          </ul>
        </footer>
      </article>

      <div v-else class="knowledge-empty">
        <el-icon><Reading /></el-icon>
        <h2>从资料馆开始</h2>
        <p>上传资料或把共享馆藏加入资料馆后，就可以在这里得到有来源依据的回答。</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, DocumentAdd, Loading, Promotion, Reading, Refresh, WarningFilled } from '@element-plus/icons-vue'
import { documentApi } from '@/api/document'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'
import { renderAssistantMarkdown } from '@/utils/markdownThink'

const router = useRouter()
const question = ref('')
const includeGlobalShared = ref(false)
const isLoading = ref(false)
const result = ref(null)
const errorMessage = ref('')

const answerHtml = computed(() => renderAssistantMarkdown(result.value?.answer || ''))
const needsMoreContext = computed(() => result.value?.support?.status === 'needs_more_context')
const supportLabel = computed(() => needsMoreContext.value ? '需要补充资料' : '已有资料支撑')

function normalizeSources(sources = []) {
  return sources.map((source) => ({
    ...source,
    title: source.title || source.file_name || source.document_name,
    tags: Array.isArray(source.tags) ? source.tags : []
  }))
}

async function ask() {
  const text = question.value.trim()
  if (!text || isLoading.value) return

  isLoading.value = true
  result.value = null
  errorMessage.value = ''
  try {
    const data = await documentApi.library.ask(text, { includeGlobalShared: includeGlobalShared.value })
    result.value = {
      answer: data.answer || data.content || '暂未得到可用回答。',
      sources: normalizeSources(data.sources),
      support: data.support || { status: data.sources?.length ? 'ready' : 'needs_more_context', source_count: data.sources?.length || 0 }
    }
  } catch (error) {
    const message = formatAxiosErrorMessage(error, '知识服务暂时不可用。')
    errorMessage.value = message + ' 你的问题还保留在输入框中，可以直接重试。'
    ElMessage.error(message)
  } finally {
    isLoading.value = false
  }
}

function sourceKey(source) {
  return [source.doc_id || source.document_id || source.title, source.chunk_index || ''].join('-')
}
</script>

<style scoped>
.knowledge-page { width: min(1040px, 100%); margin: 0 auto; padding: 44px 32px 56px; }
.knowledge-page__header { display: flex; justify-content: space-between; gap: 24px; align-items: flex-end; padding-bottom: 28px; border-bottom: 1px solid var(--border-color); }
.knowledge-page__header > div { max-width: 680px; }
.eyebrow { margin: 0 0 7px; color: var(--color-primary-dark); font-size: 12px; font-weight: 750; letter-spacing: 0; text-transform: uppercase; }
h1 { margin: 0; font-size: 38px; line-height: 1.15; }
h2 { margin: 0; font-size: 21px; }
.knowledge-page__header p:not(.eyebrow) { margin: 11px 0 0; color: var(--text-secondary); font-size: 15px; line-height: 1.6; }
.knowledge-main { min-width: 0; padding-top: 32px; }
.ask-form { padding: 22px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-secondary); box-shadow: var(--shadow-sm); }
.ask-form__heading { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin-bottom: 16px; }
.ask-form__heading label { display: block; color: var(--text-primary); font-size: 15px; font-weight: 700; }
.ask-form__heading p { margin: 5px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.5; }
.library-scope-switch { display: flex; flex: 0 0 auto; gap: 12px; align-items: center; padding: 9px 11px; border: 1px solid var(--border-color-light); border-radius: 6px; background: var(--bg-tertiary); }
.library-scope-switch span { display: grid; gap: 2px; }
.library-scope-switch strong { color: var(--text-primary); font-size: 12px; }
.library-scope-switch small { color: var(--text-muted); font-size: 11px; }
.ask-form :deep(.el-textarea__inner) { min-height: 116px !important; border-radius: 6px; font: inherit; line-height: 1.6; }
.ask-form__footer { display: flex; justify-content: space-between; gap: 18px; align-items: center; margin-top: 14px; }
.ask-form__footer > span { color: var(--text-muted); font-size: 12px; line-height: 1.5; }
.answer-loading, .knowledge-empty { display: grid; justify-items: center; gap: 12px; padding: 76px 22px; color: var(--text-muted); text-align: center; }
.answer-error { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 14px; margin-top: 22px; padding: 18px; border: 1px solid color-mix(in srgb, var(--color-danger) 24%, var(--border-color)); border-radius: 7px; background: color-mix(in srgb, var(--color-danger) 5%, var(--bg-secondary)); }
.answer-error > .el-icon { color: var(--color-danger); font-size: 22px; }
.answer-error h2 { margin: 0 0 4px; font-size: 15px; }
.answer-error p { margin: 0; color: var(--text-secondary); font-size: 13px; line-height: 1.55; }
.answer-loading { grid-template-columns: auto auto; justify-content: center; }
.answer-loading .el-icon { color: var(--color-primary); font-size: 19px; }
.answer-panel { margin-top: 28px; border-top: 2px solid var(--color-primary); }
.answer-panel__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 22px 0; border-bottom: 1px solid var(--border-color-light); }
.answer-panel__header .eyebrow { margin-bottom: 4px; }
.support-status { flex: 0 0 auto; padding: 5px 8px; border: 1px solid color-mix(in srgb, var(--color-success) 34%, var(--border-color)); border-radius: 999px; color: var(--color-success); background: color-mix(in srgb, var(--color-success) 8%, var(--bg-secondary)); font-size: 12px; font-weight: 700; }
.support-status--limited { border-color: color-mix(in srgb, var(--color-warning) 38%, var(--border-color)); color: var(--color-warning); background: color-mix(in srgb, var(--color-warning) 9%, var(--bg-secondary)); }
.answer-panel__body { padding: 28px 0; color: var(--text-primary); }
.answer-context-note { margin: -8px 0 24px; padding: 11px 13px; border-left: 2px solid var(--color-warning); color: var(--text-secondary); background: color-mix(in srgb, var(--color-warning) 8%, var(--bg-secondary)); font-size: 13px; line-height: 1.6; }
.sources { padding: 22px 0 0; border-top: 1px solid var(--border-color-light); }
.sources h3 { margin: 0 0 12px; font-size: 14px; }
.sources ul { display: grid; gap: 8px; padding: 0; list-style: none; }
.sources li { display: flex; align-items: center; gap: 10px; min-height: 46px; padding: 8px 10px; border-left: 2px solid color-mix(in srgb, var(--color-primary) 36%, transparent); background: var(--bg-tertiary); }
.sources li > .el-icon { color: var(--color-primary-dark); }
.sources li > div { display: grid; gap: 1px; min-width: 0; }
.sources strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.sources small { color: var(--text-muted); font-size: 11px; }
.knowledge-empty { padding-top: 86px; }
.knowledge-empty > .el-icon { color: var(--color-primary); font-size: 34px; }
.knowledge-empty h2 { color: var(--text-primary); }
.knowledge-empty p { max-width: 440px; margin: 0; color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
@media (max-width: 700px) { .knowledge-page { padding: 30px 18px 40px; } .knowledge-page__header, .ask-form__heading, .ask-form__footer { align-items: stretch; flex-direction: column; } .knowledge-page__header > .el-button, .ask-form__footer .el-button { width: 100%; } .library-scope-switch { justify-content: space-between; } h1 { font-size: 30px; } }
@media (max-width: 480px) { .ask-form { padding: 14px; } .answer-error { grid-template-columns: auto minmax(0, 1fr); } .answer-error .el-button { grid-column: 1 / -1; width: 100%; } .support-status { white-space: nowrap; } }
</style>
