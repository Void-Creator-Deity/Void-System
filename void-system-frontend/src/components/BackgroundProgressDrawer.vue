<template>
  <el-drawer
    v-model="visible"
    class="background-progress-drawer"
    direction="rtl"
    size="min(100vw, 420px)"
    :with-header="false"
    append-to-body
  >
    <section class="progress-center" aria-label="后台进度">
      <header class="progress-center__header">
        <div>
          <p class="progress-center__eyebrow">后台进度</p>
          <h2>正在处理的内容</h2>
          <p>离开页面或刷新后，处理状态会自动恢复。</p>
        </div>
        <el-button text circle aria-label="关闭后台进度" @click="visible = false">
          <el-icon><Close /></el-icon>
        </el-button>
      </header>

      <div v-if="store.isRefreshing && !workItems.length" class="progress-center__empty" aria-live="polite">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>正在恢复后台进度。</p>
      </div>

      <div v-else-if="!workItems.length" class="progress-center__empty">
        <el-icon><CircleCheck /></el-icon>
        <p>当前没有需要等待的处理。</p>
      </div>

      <ul v-else class="progress-list">
        <li v-for="work in workItems" :key="work.work_id" class="progress-item" :data-state="work.state">
          <div class="progress-item__topline">
            <div>
              <p class="progress-item__title">{{ presentationFor(work).title }}</p>
              <p class="progress-item__topic">{{ work.title }}</p>
            </div>
            <span class="progress-item__status">{{ stateLabel(work) }}</span>
          </div>
          <p class="progress-item__copy">{{ presentationFor(work).copy }}</p>
          <el-progress
            v-if="work.state === BACKGROUND_WORK_STATE.ACTIVE"
            :percentage="work.progress"
            :stroke-width="5"
            :show-text="false"
          />
          <div class="progress-item__actions">
            <el-button
              v-if="work.state === BACKGROUND_WORK_STATE.READY && work.kind === BACKGROUND_WORK_KIND.PLAN_GENERATION && work.result_ref?.draft_id"
              type="primary"
              @click="openDraft(work.result_ref.draft_id)"
            >打开方案</el-button>
            <el-button
              v-else-if="work.state === BACKGROUND_WORK_STATE.READY && work.kind === BACKGROUND_WORK_KIND.KNOWLEDGE_PROCESSING"
              type="primary"
              @click="openDocuments()"
            >查看资料库</el-button>
            <el-button
              v-else-if="work.state === BACKGROUND_WORK_STATE.ACTIVE"
              text
              type="primary"
              :loading="cancellingId === work.work_id"
              @click="cancel(work)"
            >停止处理</el-button>
            <el-button
              v-else-if="work.kind === BACKGROUND_WORK_KIND.KNOWLEDGE_PROCESSING && (work.state === BACKGROUND_WORK_STATE.FAILED || work.state === BACKGROUND_WORK_STATE.CANCELLED)"
              text
              type="primary"
              :loading="retryingId === work.source_id"
              @click="retryKnowledge(work.source_id)"
            >重新处理</el-button>
          </div>
        </li>
      </ul>

      <p v-if="store.lastError" class="progress-center__error" role="status">{{ store.lastError }}</p>
    </section>
  </el-drawer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Close, Loading } from '@element-plus/icons-vue'
import { BACKGROUND_WORK_KIND, BACKGROUND_WORK_STATE, backgroundWorkPresentation } from '@/domain/backgroundWork'
import { useBackgroundProgressStore } from '@/stores/backgroundProgress'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue'])
const router = useRouter()
const store = useBackgroundProgressStore()
const cancellingId = ref('')
const retryingId = ref('')
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})
const workItems = computed(() => store.recentWork)

/**
 * Return user-facing display copy for a normalized background work item.
 * Input: A common work record from the global store.
 * Output: Stable short title and explanatory text for the progress drawer.
 * Called by: The drawer row template for every visible item.
 * Side effects: None.
 * Failure: Unknown job kinds fall back to the domain helper's generic copy.
 * Invariant: Text is derived from the server-owned terminal/active state, never local elapsed time.
 */
function presentationFor(work) {
  return backgroundWorkPresentation(work)
}

function stateLabel(work) {
  return ({
    [BACKGROUND_WORK_STATE.ACTIVE]: '处理中',
    [BACKGROUND_WORK_STATE.READY]: '已完成',
    [BACKGROUND_WORK_STATE.FAILED]: '未完成',
    [BACKGROUND_WORK_STATE.CANCELLED]: '已停止'
  })[work.state] || '处理中'
}

/**
 * Take the user to the Plan Draft embedded in the canonical action workspace.
 * Input: A durable Plan Draft id produced by a ready Plan Generation job.
 * Output: The shared Advisor loads that exact draft through its server endpoint.
 * Called by: A ready background-work row's primary action.
 * Side effects: Closes this drawer and changes the client route.
 * Failure: Missing ids are ignored because a malformed job cannot be opened safely.
 * Invariant: Navigation does not place draft payloads or result data in query strings.
 */
function openDraft(draftId) {
  if (!draftId) return
  visible.value = false
  router.push({ name: 'TaskWorkspace', query: { view: 'plan', draft: draftId } })
}

function openDocuments() {
  visible.value = false
  router.push({ name: 'DocumentManager' })
}

/**
 * Cooperatively stop an active server-owned generation job.
 * Input: Durable generation id selected from an active work row.
 * Output: Updates the shared store with the authoritative cancellation snapshot.
 * Called by: The global drawer's "停止生成" action.
 * Side effects: Performs one DELETE request; jobs already running at the model stop at backend checkpoints.
 * Failure: Shows a transport-safe notification and retains existing work for another attempt.
 * Invariant: Cancellation never deletes a ready draft or hides a failed state.
 */
async function cancel(work) {
  if (!work?.work_id || cancellingId.value) return
  cancellingId.value = work.work_id
  try {
    await store.cancelWork(work)
    ElMessage.info('已请求停止这项后台处理。')
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, '暂时无法停止处理，请稍后再试。'))
  } finally {
    cancellingId.value = ''
  }
}

async function retryKnowledge(jobId) {
  if (!jobId || retryingId.value) return
  retryingId.value = jobId
  try {
    await store.retryKnowledgeJob(jobId)
    ElMessage.success('已重新加入资料处理。')
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, '暂时无法重新处理资料，请稍后再试。'))
  } finally {
    retryingId.value = ''
  }
}
</script>

<style scoped>
.progress-center { display: grid; min-height: 100%; align-content: start; gap: 22px; padding: 4px 4px 24px; }
.progress-center__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding-bottom: 18px; border-bottom: 1px solid var(--border-color-light); }
.progress-center__eyebrow { margin: 0 0 6px; color: var(--color-primary-dark); font-size: 0.72rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.progress-center__header h2 { margin: 0; color: var(--text-primary); font-size: 1.25rem; line-height: 1.3; }
.progress-center__header p:not(.progress-center__eyebrow) { max-width: 280px; margin: 7px 0 0; color: var(--text-muted); font-size: 0.85rem; line-height: 1.55; }
.progress-center__empty { display: grid; min-height: 170px; place-items: center; align-content: center; gap: 10px; color: var(--text-muted); text-align: center; }
.progress-center__empty .el-icon { color: var(--color-primary); font-size: 1.45rem; }
.progress-center__empty p { margin: 0; }
.progress-list { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--border-color-light); }
.progress-item { display: grid; gap: 10px; padding: 18px 0; border-bottom: 1px solid var(--border-color-light); }
.progress-item__topline { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.progress-item__title { margin: 0; color: var(--text-primary); font-size: 0.97rem; font-weight: 800; line-height: 1.35; }
.progress-item__topic { margin: 4px 0 0; color: var(--text-secondary); font-size: 0.84rem; line-height: 1.45; }
.progress-item__status { flex: 0 0 auto; padding: 3px 7px; border-radius: 999px; color: #3f6596; background: rgba(63, 101, 150, .12); font-size: 0.72rem; font-weight: 750; }
.progress-item[data-state="ready"] .progress-item__status { color: #2f6e52; background: rgba(47, 110, 82, .12); }
.progress-item[data-state="failed"] .progress-item__status { color: #914c43; background: rgba(145, 76, 67, .12); }
.progress-item[data-state="cancelled"] .progress-item__status { color: #6d5b55; background: rgba(109, 91, 85, .12); }
.progress-item__copy { margin: 0; color: var(--text-secondary); font-size: 0.84rem; line-height: 1.55; }
.progress-item__actions { display: flex; align-items: center; min-height: 30px; }
.progress-center__error { margin: 0; padding-top: 12px; border-top: 1px solid var(--border-color-light); color: var(--color-danger); font-size: 0.83rem; line-height: 1.55; }
</style>
