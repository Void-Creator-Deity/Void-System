<template>
  <section class="knowledge-page">
    <header class="knowledge-page__header">
      <div>
        <p class="eyebrow">知识问答</p>
        <h1>从你的资料里找到答案</h1>
        <p>选择资料范围并提出问题，回答会同时列出参考来源。</p>
      </div>
      <el-button :icon="DocumentAdd" plain @click="router.push('/documents')">管理我的资料</el-button>
    </header>

    <div class="knowledge-workspace">
      <aside class="knowledge-scope" aria-label="知识范围">
        <button
          v-for="option in scopes"
          :key="option.value"
          class="scope-option"
          :class="{ 'scope-option--active': scope === option.value }"
          type="button"
          @click="selectScope(option.value)"
        >
          <el-icon><component :is="option.icon" /></el-icon>
          <span>
            <strong>{{ option.label }}</strong>
            <small>{{ option.description }}</small>
          </span>
        </button>
      </aside>

      <div class="knowledge-main">
        <form class="ask-form" @submit.prevent="ask">
          <label for="knowledge-question">你想弄清什么？</label>
          <el-input
            id="knowledge-question"
            v-model="question"
            :placeholder="scope === 'personal' ? '围绕自己的资料提问' : '围绕共享知识库提问'"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 7 }"
            resize="none"
            :disabled="isLoading"
            @keydown.enter.exact.prevent="ask"
          />
          <div class="ask-form__footer">
            <span>{{ scope === 'personal' ? '只会使用你上传的资料。' : '共享答案来自管理员维护的参考资料。' }}</span>
            <el-button type="primary" native-type="submit" :icon="Promotion" :loading="isLoading" :disabled="!question.trim()">
              开始提问
            </el-button>
          </div>
        </form>

        <div v-if="isLoading" class="answer-loading" aria-live="polite">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在查找相关依据并整理答案...</span>
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
              <p class="eyebrow">{{ scope === 'personal' ? '我的资料' : '共享知识' }}</p>
              <h2>回答</h2>
            </div>
            <span class="support-status" :class="{ 'support-status--limited': needsMoreContext }">{{ supportLabel }}</span>
          </header>

          <div class="answer-panel__body markdown-body" v-html="answerHtml"></div>

          <p v-if="needsMoreContext" class="answer-context-note">
            当前资料还不足以支撑更具体的回答。补充相关资料，或换一种更明确的问法后再试。
          </p>

          <footer v-if="result.sources.length" class="sources">
            <h3>来源</h3>
            <ul>
              <li v-for="source in result.sources" :key="sourceKey(source)">
                <el-icon><Document /></el-icon>
                <div>
                  <strong>{{ source.title || '未命名资料' }}</strong>
                  <small v-if="source.tags?.length">{{ source.tags.join(' / ') }}</small>
                </div>
              </li>
            </ul>
          </footer>
        </article>

        <div v-else class="knowledge-empty">
          <el-icon><Reading /></el-icon>
          <h2>{{ scope === 'personal' ? '从自己的资料中开始' : '共享知识，随时可查' }}</h2>
          <p>{{ scope === 'personal' ? '上传参考资料后，就可以在这里得到有来源依据的回答。' : '提出一个明确的问题，检索并整合团队持续维护的参考内容。' }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Collection, Document, DocumentAdd, Loading, Promotion, Reading, Refresh, WarningFilled } from '@element-plus/icons-vue'
import { documentApi } from '@/api/document'
import { sharedKnowledgeApi } from '@/api/knowledge'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'
import { renderAssistantMarkdown } from '@/utils/markdownThink'

const router = useRouter()
const question = ref('')
const scope = ref('personal')
const isLoading = ref(false)
const result = ref(null)
const errorMessage = ref('')

const scopes = [
  { value: 'personal', label: '我的资料', description: '你上传的文档', icon: Document },
  { value: 'shared', label: '共享知识', description: '管理员维护的参考资料', icon: Collection }
]


const answerHtml = computed(() => renderAssistantMarkdown(result.value?.answer || ''))
const needsMoreContext = computed(() => result.value?.support?.status === 'needs_more_context')
const supportLabel = computed(() => needsMoreContext.value ? '需要补充资料' : '已有资料支撑')

function selectScope(nextScope) {
  if (scope.value === nextScope) return
  scope.value = nextScope
  result.value = null
  errorMessage.value = ''
}

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
    const data = scope.value === 'personal'
      ? await documentApi.ask(text)
      : await sharedKnowledgeApi.ask(text)
    result.value = {
      answer: data.answer || data.content || '暂未得到可用回答。',
      sources: normalizeSources(data.sources),
      support: data.support || { status: data.sources?.length ? 'ready' : 'needs_more_context', source_count: data.sources?.length || 0 }
    }
  } catch (error) {
    const message = formatAxiosErrorMessage(error, '知识服务暂时不可用。')
    errorMessage.value = `${message} 你的问题还保留在输入框中，可以直接重试。`
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
.knowledge-page { width: min(1180px, 100%); margin: 0 auto; padding: 42px 0 64px; }
.knowledge-page__header { display: flex; justify-content: space-between; gap: 24px; align-items: flex-end; padding-bottom: 30px; border-bottom: 1px solid var(--border-color); }
.knowledge-page__header > div { max-width: 640px; }
.eyebrow { margin-bottom: 7px; color: var(--color-primary-dark); font-size: 12px; font-weight: 750; letter-spacing: 0; text-transform: uppercase; }
h1 { font-size: 42px; line-height: 1.08; }
h2 { font-size: 21px; }
.knowledge-page__header p:not(.eyebrow) { margin-top: 11px; color: var(--text-secondary); font-size: 15px; }
.knowledge-workspace { display: grid; grid-template-columns: 236px minmax(0, 1fr); gap: 48px; padding-top: 32px; }
.knowledge-scope { display: grid; align-content: start; gap: 6px; }
.scope-option { display: flex; gap: 11px; width: 100%; padding: 12px; border: 1px solid transparent; border-radius: 7px; color: var(--text-secondary); background: transparent; text-align: left; cursor: pointer; transition: .18s ease; }
.scope-option:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.scope-option--active { border-color: color-mix(in srgb, var(--color-primary) 24%, var(--border-color)); color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 9%, var(--bg-secondary)); }
.scope-option > .el-icon { flex: 0 0 auto; margin-top: 2px; font-size: 18px; }
.scope-option span { display: grid; gap: 2px; min-width: 0; }
.scope-option strong { font-size: 14px; }
.scope-option small { color: var(--text-muted); font-size: 12px; line-height: 1.35; }
.knowledge-main { min-width: 0; }
.ask-form { padding: 20px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-secondary); box-shadow: var(--shadow-sm); }
.ask-form > label { display: block; margin-bottom: 10px; color: var(--text-primary); font-size: 14px; font-weight: 700; }
.ask-form :deep(.el-textarea__inner) { min-height: 98px !important; border-radius: 6px; font: inherit; line-height: 1.6; }
.ask-form__footer { display: flex; justify-content: space-between; gap: 18px; align-items: center; margin-top: 14px; }
.ask-form__footer > span { color: var(--text-muted); font-size: 12px; }
.answer-loading, .knowledge-empty { display: grid; justify-items: center; gap: 12px; padding: 76px 22px; color: var(--text-muted); text-align: center; }
.answer-error { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:14px; margin-top:22px; padding:18px; border:1px solid color-mix(in srgb,var(--color-danger) 24%,var(--border-color)); border-radius:7px; background:color-mix(in srgb,var(--color-danger) 5%,var(--bg-secondary)); }.answer-error > .el-icon { color:var(--color-danger); font-size:22px; }.answer-error h2 { margin:0 0 4px; font-size:15px; }.answer-error p { margin:0; color:var(--text-secondary); font-size:13px; line-height:1.55; }
.answer-loading { grid-template-columns: auto auto; justify-content: center; }
.answer-loading .el-icon { color: var(--color-primary); font-size: 19px; }
.answer-panel { margin-top: 26px; border-top: 2px solid var(--color-primary); }
.answer-panel__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 22px 0; border-bottom: 1px solid var(--border-color-light); }
.answer-panel__header .eyebrow { margin-bottom: 4px; }
.support-status { flex: 0 0 auto; padding: 5px 8px; border: 1px solid color-mix(in srgb, var(--color-success) 34%, var(--border-color)); border-radius: 999px; color: var(--color-success); background: color-mix(in srgb, var(--color-success) 8%, var(--bg-secondary)); font-size: 12px; font-weight: 700; }.support-status--limited { border-color: color-mix(in srgb, var(--color-warning) 38%, var(--border-color)); color: var(--color-warning); background: color-mix(in srgb, var(--color-warning) 9%, var(--bg-secondary)); }
.answer-panel__body { padding: 28px 0; color: var(--text-primary); }
.answer-context-note { margin: -8px 0 24px; padding: 11px 13px; border-left: 2px solid var(--color-warning); color: var(--text-secondary); background: color-mix(in srgb, var(--color-warning) 8%, var(--bg-secondary)); font-size: 13px; line-height: 1.6; }
.sources { padding: 22px 0 0; border-top: 1px solid var(--border-color-light); }
.sources h3 { margin-bottom: 12px; font-size: 14px; }
.sources ul { display: grid; gap: 8px; padding: 0; list-style: none; }
.sources li { display: flex; align-items: center; gap: 10px; min-height: 46px; padding: 8px 10px; border-left: 2px solid color-mix(in srgb, var(--color-primary) 36%, transparent); background: var(--bg-tertiary); }
.sources li > .el-icon { color: var(--color-primary-dark); }
.sources li > div { display: grid; gap: 1px; min-width: 0; }
.sources strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.sources small { color: var(--text-muted); font-size: 11px; }
.knowledge-empty { padding-top: 86px; }
.knowledge-empty > .el-icon { color: var(--color-primary); font-size: 34px; }
.knowledge-empty h2 { color: var(--text-primary); }
.knowledge-empty p { max-width: 440px; color: var(--text-secondary); font-size: 14px; }
@media (max-width: 820px) { .knowledge-page { padding-top: 28px; } .knowledge-page__header { align-items: flex-start; flex-direction: column; } .knowledge-workspace { grid-template-columns: 1fr; gap: 20px; } .knowledge-scope { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { h1 { font-size: 32px; } .answer-error { grid-template-columns:auto minmax(0,1fr); }.answer-error .el-button { grid-column:1/-1; width:100%; } .knowledge-page { padding-bottom: 36px; } .knowledge-page__header { padding-bottom: 22px; } .knowledge-page__header > .el-button { width: 100%; } .knowledge-scope { grid-template-columns: 1fr; } .ask-form { padding: 14px; } .ask-form__footer { align-items: stretch; flex-direction: column; } .ask-form__footer .el-button { width: 100%; } .sources li { align-items: flex-start; } }
</style>
