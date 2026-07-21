<template>
  <div class="advisor-page" :class="{ 'advisor-page--embedded': embedded }">
    <div class="advisor-shell">
      <header class="advisor-header">
        <div>
          <p class="advisor-eyebrow">行动规划</p>
          <component :is="embedded ? 'h2' : 'h1'">把想法整理成可完成的步骤</component>
          <p class="advisor-subtitle">说清楚你想得到的结果，系统会先给出一份可调整的方案，确认后再加入正在推进。</p>
        </div>
        <el-tooltip content="查看最近生成的方案" placement="bottom">
          <el-button class="history-button" :icon="Clock" circle aria-label="查看方案历史" @click="showHistory = true" />
        </el-tooltip>
      </header>

      <section class="planner-composer" aria-label="创建行动方案">
        <label class="field-label" for="advisor-goal">这次想完成什么？</label>
        <el-input
          id="advisor-goal"
          v-model="userQuery"
          class="goal-input"
          :disabled="isLoading"
          :autosize="{ minRows: 3, maxRows: 6 }"
          type="textarea"
          resize="none"
          placeholder="例如：在 6 周内完成一个可以公开展示的 Vue 3 作品"
          @keydown.ctrl.enter.prevent="submitQuery"
          @keydown.meta.enter.prevent="submitQuery"
        />
        <div class="composer-footer">
          <div class="execution-choice">
            <span>推进方式</span>
            <el-segmented v-model="executionMode" :options="executionModes" :disabled="isLoading" />
          </div>
          <el-button type="primary" :icon="MagicStick" :loading="isLoading" :disabled="!userQuery.trim()" @click="submitQuery">
            生成方案
          </el-button>
        </div>
      </section>

      <section v-if="quickTopics.length" class="suggestion-section" aria-labelledby="topic-heading">
        <div class="section-heading">
          <div>
            <p class="section-kicker">从这里开始</p>
            <h2 id="topic-heading">常见方向</h2>
          </div>
        </div>
        <div class="topic-list">
          <button v-for="topic in quickTopics" :key="topic.id" class="topic-option" type="button" :disabled="isLoading" @click="useQuickTopic(topic.text)">
            <span>{{ topic.text }}</span>
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>
      </section>

      <section v-if="isLoading" class="planning-state" aria-live="polite">
        <div class="planning-state__indicator"><el-icon class="is-loading"><Loading /></el-icon></div>
        <div class="planning-state__body">
          <p class="planning-state__title">{{ generationPresentation.title }}</p>
          <p class="planning-state__copy">{{ generationPresentation.copy }}</p>
          <el-progress class="planning-state__progress" :percentage="generationProgress" :stroke-width="5" :show-text="false" />
        </div>
        <el-button text type="primary" @click="cancelGeneration">停止等待</el-button>
      </section>

      <section v-if="advisorResult && !isLoading" class="plan-result" aria-labelledby="plan-title">
        <header class="plan-result__header">
          <div class="plan-result__intro">
            <p class="section-kicker">方案草稿</p>
            <el-input
              v-if="isEditingPlan"
              v-model="advisorResult.goal.title"
              class="plan-title-input"
              maxlength="160"
              aria-label="目标名称"
            />
            <h2 v-else id="plan-title">{{ advisorResult.goal.title }}</h2>
            <el-input
              v-if="isEditingPlan"
              v-model="advisorResult.goal.description"
              class="plan-summary-input"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              maxlength="2000"
              placeholder="补充背景、限制或需要留意的事情"
              aria-label="方案说明"
            />
            <p v-else-if="advisorResult.goal.description" class="plan-result__summary">{{ advisorResult.goal.description }}</p>
            <div v-if="isEditingPlan" class="plan-goal-fields">
              <label class="editor-field editor-field--wide">
                <span>完成时希望看到什么</span>
                <el-input
                  v-model="advisorResult.goal.desired_outcome"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 4 }"
                  maxlength="2000"
                  placeholder="例如：获得一个可以分享的公开链接"
                />
              </label>
              <div class="editor-field">
                <span>重要程度</span>
                <el-segmented v-model="advisorResult.goal.priority" :options="priorityOptions" size="small" />
              </div>
            </div>
            <div
              v-else-if="advisorResult.goal.desired_outcome && advisorResult.goal.desired_outcome !== advisorResult.goal.title"
              class="goal-outcome"
            >
              <span>完成结果</span>
              <p>{{ advisorResult.goal.desired_outcome }}</p>
            </div>
          </div>
          <div class="plan-result__actions">
            <span v-if="estimatedDuration" class="duration-chip"><el-icon><Clock /></el-icon>{{ estimatedDuration }}</span>
            <el-button v-if="canEditPlan" :icon="EditPen" :loading="isSavingDraft" @click="togglePlanEditing">
              {{ isEditingPlan ? '完成调整' : '调整方案' }}
            </el-button>
            <el-button type="primary" :icon="CircleCheck" :loading="isPublishing" :disabled="!canUsePublicationAction" @click="publishPlan">
              {{ publicationActionLabel }}
            </el-button>
          </div>
        </header>

        <el-alert
          v-if="publicationNotice"
          class="plan-alert"
          type="info"
          :closable="false"
          show-icon
          :title="publicationNotice"
        />

        <el-alert
          v-if="advisorResult.meta?.fallback"
          class="plan-alert"
          type="warning"
          :closable="false"
          show-icon
          title="当前使用了基础方案，请在开始前确认目标和每一步是否适合你。"
        />

        <ol class="plan-steps">
          <li v-for="(step, index) in learningSteps" :key="step.client_key || index" class="plan-step">
            <div class="plan-step__number">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="plan-step__body">
              <div class="plan-step__topline">
                <el-input v-if="isEditingPlan" v-model="step.title" class="step-title-input" maxlength="160" :aria-label="'第 ' + (index + 1) + ' 步名称'" />
                <h3 v-else>{{ step.title }}</h3>
                <div class="step-topline-actions">
                  <span class="priority-badge priority-badge--manual">{{ kindLabel() }}</span>
                  <el-tooltip v-if="isEditingPlan" content="移除这一步" placement="top">
                    <el-button text type="danger" :icon="Delete" :disabled="learningSteps.length <= 1" :aria-label="'移除第 ' + (index + 1) + ' 步'" @click="removePlanStep(index)" />
                  </el-tooltip>
                </div>
              </div>
              <el-input
                v-if="isEditingPlan"
                v-model="step.description"
                class="step-description-input"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 5 }"
                maxlength="2000"
                placeholder="写清楚这一步要做什么"
                :aria-label="'第 ' + (index + 1) + ' 步说明'"
              />
              <p v-else>{{ step.description }}</p>
              <div v-if="isEditingPlan" class="step-editor-grid">
                <label class="editor-field">
                  <span>开始前需要完成</span>
                  <el-select
                    v-model="step.depends_on"
                    multiple
                    clearable
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="无需等待其他步骤"
                    aria-label="步骤依赖"
                  >
                    <el-option
                      v-for="dependency in availableDependencies(step)"
                      :key="dependency.client_key"
                      :label="dependency.title || '未命名步骤'"
                      :value="dependency.client_key"
                    />
                  </el-select>
                </label>
                <label class="editor-field editor-field--wide">
                  <span>完成后留下什么</span>
                  <el-select
                    v-model="step.completion_criteria.deliverables"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    placeholder="输入交付物后按回车，例如：公开链接"
                    aria-label="步骤交付物"
                  />
                </label>
                <el-checkbox v-model="step.requires_approval" class="approval-choice">完成后请我确认，再继续后面的步骤</el-checkbox>
              </div>
              <div v-else class="step-meta">
                <span v-if="estimatedMinutes(step)"><el-icon><Clock /></el-icon>约 {{ estimatedMinutes(step) }} 分钟</span>
                <span>{{ dependencySummary(step) }}</span>
                <span v-if="step.requires_approval"><el-icon><CircleCheck /></el-icon>完成后由你确认</span>
              </div>
              <div v-if="!isEditingPlan && getDeliverables(step).length" class="step-outcome">
                <span>完成标志</span>
                <p>{{ getDeliverables(step).join('、') }}</p>
              </div>
            </div>
          </li>
        </ol>
        <div v-if="isEditingPlan" class="plan-editor-actions">
          <el-button :icon="Plus" @click="addPlanStep">添加一步</el-button>
        </div>
      </section>

      <section v-if="!advisorResult && !isLoading" class="empty-plan" aria-label="方案提示">
        <el-icon><Document /></el-icon>
        <p>从一个具体结果开始，行动方案会在这里展开。</p>
      </section>
    </div>

    <el-drawer v-model="showHistory" title="最近方案" direction="rtl" size="min(420px, 92vw)">
      <template #header>
        <div class="drawer-title">
          <div>
            <p class="section-kicker">可恢复的服务端记录</p>
            <h2>最近方案</h2>
          </div>
        </div>
      </template>
      <div v-if="historyList.length" class="history-list">
        <button v-for="item in historyList" :key="item.draft_id" class="history-item" type="button" @click="restoreFromHistory(item)">
          <span class="history-item__topline">
            <span class="history-item__title">{{ item.goal.title }}</span>
            <span class="history-item__status" :data-status="item.status">{{ publicationStatusLabel(item.status) }}</span>
          </span>
          <span class="history-item__meta">{{ formatHistoryDate(item.created_at) }} · {{ item.run.steps.length }} 步</span>
        </button>
      </div>
      <el-empty v-else description="还没有生成过方案" />
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, CircleCheck, Clock, Delete, Document, EditPen, Loading, MagicStick, Plus } from '@element-plus/icons-vue'
import { plansApi } from '@/api/plans'
import { backgroundWorkPresentation, planGenerationToBackgroundWork } from '@/domain/backgroundWork'
import { useBackgroundProgressStore } from '@/stores/backgroundProgress'
import {
  PLAN_DRAFT_STATUS,
  buildPlanDraftPayload,
  createPublicationKey,
  normalizePlanDraft
} from '@/domain/planDraft'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'

const props = defineProps({ embedded: { type: Boolean, default: false } })
const emit = defineEmits(['published'])
const embedded = computed(() => props.embedded)

const executionModes = [
  { label: '自己完成', value: 'manual' },
  { label: '和系统一起', value: 'assisted' }
]
const priorityOptions = [
  { label: '一般', value: 'low' },
  { label: '重要', value: 'medium' },
  { label: '优先', value: 'high' }
]
const quickTopics = [
  { id: 'project', text: '完成一个可以公开展示的个人作品' },
  { id: 'habit', text: '建立一个能够长期坚持的健康习惯' },
  { id: 'learning', text: '系统掌握一项新的专业技能' },
  { id: 'knowledge', text: '整理散落资料并形成可复用的知识体系' }
]

const router = useRouter()
const route = useRoute()
const backgroundProgress = useBackgroundProgressStore()
const userQuery = ref('')
const executionMode = ref('assisted')
const isPublishing = ref(false)
const isSavingDraft = ref(false)
const isEditingPlan = ref(false)
const advisorResult = ref(null)
const showHistory = ref(false)
const historyList = ref([])
const activeGenerationId = ref('')
const openingGenerationId = ref('')
const publicationKey = ref('')

const learningSteps = computed(() => advisorResult.value?.run?.steps || [])
const isLoading = computed(() => Boolean(activeGenerationId.value) && !['failed', 'cancelled'].includes(generation.value?.status || 'queued'))
const estimatedDuration = computed(() => {
  const value = String(advisorResult.value?.estimated_duration || '').trim()
  return value && value !== '—' ? value : ''
})
const canPublish = computed(() => {
  const goal = advisorResult.value?.goal
  return advisorResult.value?.status === PLAN_DRAFT_STATUS.READY && !isSavingDraft.value && Boolean(
    goal?.title?.trim() && learningSteps.value.length && learningSteps.value.every((step) => step?.title?.trim())
  )
})
const canUsePublicationAction = computed(() => canPublish.value || advisorResult.value?.status === PLAN_DRAFT_STATUS.PUBLISHED)
const generation = computed(() => backgroundProgress.getPlanGeneration(activeGenerationId.value))
const generationWork = computed(() => {
  const job = generation.value
  return job ? planGenerationToBackgroundWork(job) : null
})
const generationProgress = computed(() => generationWork.value?.progress || 0)
const generationPresentation = computed(() => generationWork.value
  ? backgroundWorkPresentation(generationWork.value)
  : { title: '正在生成方案', copy: '处理仍在后台进行，可以继续使用其他页面。' })
const canEditPlan = computed(() => advisorResult.value?.status === PLAN_DRAFT_STATUS.READY && !isPublishing.value && !isSavingDraft.value)
const publicationActionLabel = computed(() => advisorResult.value?.status === PLAN_DRAFT_STATUS.PUBLISHED ? '打开行动' : '开始推进')
const publicationNotice = computed(() => advisorResult.value?.status === PLAN_DRAFT_STATUS.PUBLISHED
  ? '这份方案已经开始推进，可以直接打开对应行动。'
  : '')

/**
 * Apply a server Plan Draft snapshot to the page without fabricating local publication state.
 * Input: A public Plan Draft response and an optional flag controlling composer synchronization.
 * Output: Updates the current render model, selected execution mode, and retry-key lifecycle.
 * Called by: Draft history loading, generation completion, explicit save, and publish responses.
 * Side effects: Replaces the in-memory view state only; durable history stays on the server.
 * Failure: Throws malformed payload errors to the caller.
 * Invariant: Advisor always displays the latest normalized server draft and only server ids are used.
 */
function applyDraft(record, { syncComposer = true } = {}) {
  const draft = normalizePlanDraft(record, executionMode.value)
  advisorResult.value = draft
  if (syncComposer) {
    userQuery.value = draft.goal.desired_outcome || draft.goal.title
    executionMode.value = draft.run.mode
  }
  if (draft.status === PLAN_DRAFT_STATUS.PUBLISHED) publicationKey.value = ''
  return draft
}

function clearActiveGeneration() {
  activeGenerationId.value = ''
  openingGenerationId.value = ''
}

/**
 * Refresh durable Plan Draft history from the owner-scoped backend endpoint.
 * Input: None; authentication is supplied by the shared API client.
 * Output: Updates the drawer list with records that the user can still review or open.
 * Called by: Page recovery, generation completion, draft save, and publication completion.
 * Side effects: Performs one HTTP read and replaces the local display cache.
 * Failure: Rethrows transport errors so initial recovery can remain non-blocking while explicit actions surface errors.
 * Invariant: No localStorage or sessionStorage is used for plan history.
 */
async function loadDraftHistory() {
  const response = await plansApi.listDrafts({ timeout: 15000 })
  const items = Array.isArray(response?.items) ? response.items : []
  historyList.value = items
    .map((item) => normalizePlanDraft(item, executionMode.value))
    .filter((item) => item.status !== PLAN_DRAFT_STATUS.DISCARDED)
  return historyList.value
}

/**
 * Retrieve and render one authoritative draft before allowing a user to act on it.
 * Input: Server draft id and optional history-drawer closing choice.
 * Output: The normalized current draft.
 * Called by: Global progress navigation, persisted-history selection, and publish conflict recovery.
 * Side effects: Reads one owner-scoped Draft and updates the page's transient display state.
 * Failure: Propagates stable PLAN_DRAFT_NOT_FOUND/transport errors to the caller for user-visible handling.
 * Invariant: The client never reconstructs a Draft from a generation result or a legacy task-chain response.
 */
async function openDraft(draftId, { closeHistory = false } = {}) {
  const record = await plansApi.getDraft(draftId, { timeout: 15000 })
  const draft = applyDraft(record)
  isEditingPlan.value = false
  publicationKey.value = ''
  if (closeHistory) showHistory.value = false
  return draft
}

/**
 * React to one server-owned generation state change selected by the page.
 * Input: The current Plan Generation snapshot from the shared background-progress store.
 * Output: Opens its persisted Plan Draft once ready or releases page-local selection for terminal states.
 * Called by: A watcher over the global store; the page never owns a polling timer.
 * Side effects: Reads the ready Draft, refreshes history, and may show a one-time status notification.
 * Failure: Keeps the global work item available when its Draft cannot be opened, so recovery remains possible.
 * Invariant: Completion resolves only through draft_id; job.result and browser-local plan payloads are never used.
 */
async function handleGenerationUpdate(job) {
  if (!job?.generation_id || openingGenerationId.value === job.generation_id) return
  if (job.status === 'ready') {
    if (!job.draft_id) {
      openingGenerationId.value = job.generation_id
      ElMessage.error('方案生成已结束，但结果没有可恢复的草稿标识。请重新生成并反馈此问题。')
      clearActiveGeneration()
      return
    }
    openingGenerationId.value = job.generation_id
    try {
      await openDraft(job.draft_id)
      await loadDraftHistory()
      ElMessage.success('方案已生成，可以先调整再开始。')
      clearActiveGeneration()
    } catch (error) {
      openingGenerationId.value = ''
      ElMessage.error(formatAxiosErrorMessage(error, '方案已经生成，但暂时无法打开。请从后台进度重新进入。'))
    }
    return
  }
  if (job.status === 'failed') {
    openingGenerationId.value = job.generation_id
    ElMessage.error(job.error_message || '暂时无法生成方案，请稍后重试。')
    clearActiveGeneration()
    return
  }
  if (job.status === 'cancelled') {
    openingGenerationId.value = job.generation_id
    ElMessage.info('已停止等待这次生成。')
    clearActiveGeneration()
  }
}

watch(generation, (job) => {
  void handleGenerationUpdate(job)
})

/**
 * Submit one new durable plan-generation job and begin rendering its server progress.
 * Input: Trimmed user goal, selected execution mode, and fixed maximum step count.
 * Output: Selects the returned generation job; the final plan arrives through its Plan Draft reference.
 * Called by: Composer primary action and quick-topic buttons.
 * Side effects: Creates a database-backed generation job and starts polling it.
 * Failure: Leaves any prior persisted draft intact and shows a transport-safe message.
 * Invariant: The request is quick; no model execution is awaited in the browser request.
 */
async function submitQuery() {
  const query = userQuery.value.trim()
  if (!query || isLoading.value) {
    if (!query) ElMessage.warning('先写下这次想完成的结果。')
    return
  }

  isEditingPlan.value = false
  publicationKey.value = ''
  try {
    const job = await plansApi.start(query, {
      executionMode: executionMode.value,
      maxSteps: 8,
      config: { timeout: 15000 }
    })
    backgroundProgress.upsertPlanGeneration(job)
    activeGenerationId.value = job.generation_id
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, error?.message || '暂时无法提交生成方案，请稍后重试。'))
  }
}

async function cancelGeneration() {
  const generationId = activeGenerationId.value
  if (!generationId) return
  try {
    await backgroundProgress.cancelPlanGeneration(generationId)
    clearActiveGeneration()
    ElMessage.info('已请求停止这次生成。处理状态会保留在后台进度中。')
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, error?.message || '暂时无法停止等待，请稍后重试。'))
  }
}

/**
 * Persist the complete edited Plan Draft using its rendered optimistic version.
 * Input: Current in-memory draft with user edits.
 * Output: Replaces it with the server-normalized, incremented version snapshot.
 * Called by: Explicit edit completion and immediately before a user publishes while editing.
 * Side effects: PATCHes the entire editable payload; does not create Goal or Run records.
 * Failure: A version conflict leaves the editor open so the user does not unknowingly overwrite another edit.
 * Invariant: The API payload excludes UI-only and publication fields; backend validation is final authority.
 */
async function saveCurrentDraft() {
  const current = advisorResult.value
  if (!current?.draft_id) throw new Error('方案缺少服务端标识，请重新打开后再试。')
  isSavingDraft.value = true
  try {
    const saved = await plansApi.updateDraft(
      current.draft_id,
      buildPlanDraftPayload(current),
      current.version,
      { timeout: 15000 }
    )
    return applyDraft(saved, { syncComposer: false })
  } finally {
    isSavingDraft.value = false
  }
}

async function togglePlanEditing() {
  if (!canEditPlan.value) return
  if (!isEditingPlan.value) {
    isEditingPlan.value = true
    return
  }
  try {
    await saveCurrentDraft()
    isEditingPlan.value = false
    await loadDraftHistory()
    ElMessage.success('方案修改已保存。')
  } catch (error) {
    if (error?.response?.data?.error_code === 'PLAN_DRAFT_VERSION_CONFLICT') {
      ElMessage.warning('这份方案已在其他位置更新。当前编辑尚未保存，请重新打开最新版本后再调整。')
      return
    }
    ElMessage.error(formatAxiosErrorMessage(error, '方案修改未保存，请检查内容后重试。'))
  }
}

function addPlanStep() {
  const index = learningSteps.value.length
  const existingKeys = new Set(learningSteps.value.map((step) => step.client_key))
  let sequence = index + 1
  while (existingKeys.has('step-' + sequence)) sequence += 1
  const previousKey = learningSteps.value[index - 1]?.client_key
  learningSteps.value.push({
    client_key: 'step-' + sequence,
    title: '新的行动步骤',
    description: '',
    kind: 'manual',
    depends_on: previousKey ? [previousKey] : [],
    parallel_group: null,
    max_attempts: 1,
    requires_approval: false,
    completion_criteria: { deliverables: [] },
    input_data: {}
  })
}

function removePlanStep(index) {
  if (learningSteps.value.length <= 1) return
  const [removed] = learningSteps.value.splice(index, 1)
  for (const step of learningSteps.value) {
    step.depends_on = (step.depends_on || []).filter((key) => key !== removed.client_key)
  }
}

function availableDependencies(step) {
  return learningSteps.value.filter((candidate) => candidate.client_key !== step.client_key)
}

function dependencySummary(step) {
  const dependencies = (step.depends_on || [])
    .map((key) => learningSteps.value.find((candidate) => candidate.client_key === key)?.title)
    .filter(Boolean)
  return dependencies.length ? dependencies.join('、') + '完成后开始' : '可以立即开始'
}

function estimatedMinutes(step) {
  const value = Number(step?.input_data?.estimated_minutes)
  return Number.isFinite(value) && value > 0 ? Math.round(value) : 0
}

function getDeliverables(step) {
  return Array.isArray(step?.completion_criteria?.deliverables) ? step.completion_criteria.deliverables : []
}

function kindLabel() {
  return '自己完成'
}

function publicationStatusLabel(status) {
  return ({
    [PLAN_DRAFT_STATUS.READY]: '待确认',
    [PLAN_DRAFT_STATUS.PUBLISHED]: '已开始',
    [PLAN_DRAFT_STATUS.DISCARDED]: '已放弃'
  })[status] || '待确认'
}

function formatHistoryDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date)
}

async function restoreFromHistory(item) {
  try {
    await openDraft(item.draft_id, { closeHistory: true })
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, '这份方案暂时无法打开，请稍后重试。'))
  }
}

function openPublishedRun() {
  const runId = advisorResult.value?.published_run_id
  if (!runId) {
    ElMessage.warning('这份方案尚未关联可打开的行动，请重新加载后再试。')
    return
  }
  emit('published', { run_id: runId, goal_id: advisorResult.value?.published_goal_id || null })
  router.push({ name: 'TaskWorkspace', query: { view: 'focus', run: runId } })
}

/**
 * Atomically publish the current server draft or open its existing Run.
 * Input: Current ready draft; unsaved edits are first persisted with optimistic versioning.
 * Output: A published snapshot whose Goal and Run ids come from one backend transaction.
 * Called by: Advisor primary confirmation action.
 * Side effects: Optionally PATCHes an edit then POSTs publish with a retry-stable key.
 * Failure: Re-reads the draft after an uncertain publish conflict instead of recreating individual resources.
 * Invariant: The browser never chains Goal creation, Run creation, and Run start requests.
 */
async function publishPlan() {
  if (!advisorResult.value || isPublishing.value) return
  if (advisorResult.value.status === PLAN_DRAFT_STATUS.PUBLISHED) {
    openPublishedRun()
    return
  }
  isPublishing.value = true
  try {
    if (isEditingPlan.value) {
      await saveCurrentDraft()
      isEditingPlan.value = false
    }
    const current = advisorResult.value
    const key = publicationKey.value || createPublicationKey(current.draft_id)
    publicationKey.value = key
    const published = await plansApi.publishDraft(current.draft_id, key, { timeout: 30000 })
    applyDraft(published, { syncComposer: false })
    await loadDraftHistory()
    ElMessage.success('方案已开始推进。')
    openPublishedRun()
  } catch (error) {
    if (error?.response?.data?.error_code === 'PLAN_DRAFT_ALREADY_PUBLISHED') {
      try {
        const latest = await plansApi.getDraft(advisorResult.value?.draft_id, { timeout: 15000 })
        const draft = applyDraft(latest, { syncComposer: false })
        if (draft.status === PLAN_DRAFT_STATUS.PUBLISHED) {
          await loadDraftHistory()
          openPublishedRun()
          return
        }
      } catch {
        // The original publish error below remains the actionable message.
      }
    }
    ElMessage.error(formatAxiosErrorMessage(error, '开始推进失败，请稍后重试。'))
  } finally {
    isPublishing.value = false
  }
}

function useQuickTopic(topic) {
  userQuery.value = topic
  submitQuery()
}

/**
 * Recover durable work after page refresh without relying on browser session storage.
 * Input: Owner-scoped draft and generation collections from the backend.
 * Output: Restores a running job first, otherwise opens the newest persisted draft.
 * Called by: Advisor mount once per page lifecycle.
 * Side effects: Performs bounded reads and begins polling only for active server jobs.
 * Failure: Keeps the composer usable when recovery is temporarily unavailable.
 * Invariant: Recovery order is server state, not recency inferred from local timestamps.
 */
async function restorePlanningState() {
  try {
    const requestedDraftId = typeof route.query.draft === 'string' ? route.query.draft : ''
    const drafts = await loadDraftHistory()
    if (requestedDraftId) {
      await openDraft(requestedDraftId)
      return
    }
    await backgroundProgress.refresh({ silent: true })
    const job = backgroundProgress.activeWork[0]?.raw
    if (job?.generation_id) {
      activeGenerationId.value = job.generation_id
      return
    }
    if (drafts[0]?.draft_id) await openDraft(drafts[0].draft_id)
  } catch {
    // Recovery is additive: a transient outage must not prevent creating a new durable request.
  }
}

watch(() => route.query.draft, (draftId) => {
  if (typeof draftId !== 'string' || !draftId || advisorResult.value?.draft_id === draftId) return
  openDraft(draftId).catch((error) => {
    ElMessage.error(formatAxiosErrorMessage(error, '这份方案暂时无法打开，请稍后重试。'))
  })
})

onMounted(() => {
  restorePlanningState()
})
</script>

<style scoped>
.advisor-page { min-height: 100%; padding: clamp(24px, 4vw, 48px) clamp(12px, 3vw, 24px) 56px; background: var(--bg-page); }
.advisor-shell { width: min(100%, 960px); margin: 0 auto; }
.advisor-page--embedded { min-height: 0; padding: 8px 0 56px; background: transparent; }
.advisor-page--embedded .advisor-header h2 { margin: 0; color: var(--text-primary); font-size: 1.7rem; line-height: 1.25; }
.advisor-header, .plan-result__header, .composer-footer, .section-heading, .plan-step__topline, .plan-result__actions, .step-meta, .drawer-title { display: flex; align-items: center; }
.advisor-header { justify-content: space-between; gap: 24px; margin-bottom: 32px; }
.advisor-eyebrow, .section-kicker { margin: 0 0 6px; color: var(--color-primary); font-size: 0.78rem; font-weight: 700; letter-spacing: 0; }
.advisor-header h1, .plan-result h2, .section-heading h2, .drawer-title h2 { margin: 0; color: var(--text-primary); font-size: 2.35rem; line-height: 1.18; }
.advisor-subtitle { max-width: 680px; margin: 12px 0 0; color: var(--text-secondary); font-size: 1rem; line-height: 1.65; }
.history-button { flex: 0 0 auto; color: var(--text-secondary); border-color: var(--border-color); background: var(--bg-secondary); }
.planner-composer { padding: clamp(18px, 3vw, 28px); border: 1px solid var(--border-color); border-top: 3px solid var(--color-primary); border-radius: 8px; background: var(--bg-card); box-shadow: var(--shadow-md); }
.field-label { display: block; margin-bottom: 10px; color: var(--text-primary); font-size: 0.95rem; font-weight: 700; }
.goal-input :deep(.el-textarea__inner) { min-height: 96px !important; padding: 14px 16px; color: var(--text-primary); line-height: 1.65; border-color: var(--border-color); background: var(--bg-secondary); box-shadow: none; }
.goal-input :deep(.el-textarea__inner:focus) { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--accent-glow); }
.composer-footer { justify-content: space-between; gap: 16px; margin-top: 16px; }
.composer-footer :deep(.el-segmented) { max-width: 100%; background: var(--bg-tertiary); }
.suggestion-section, .plan-result, .empty-plan { margin-top: 40px; }
.section-heading { justify-content: space-between; margin-bottom: 14px; }
.section-heading h2, .drawer-title h2 { font-size: 1.16rem; }
.topic-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.topic-option, .history-item { width: 100%; border: 1px solid var(--border-color-light); border-radius: 6px; color: var(--text-primary); background: var(--bg-secondary); cursor: pointer; font: inherit; text-align: left; transition: border-color var(--transition-fast), background var(--transition-fast), transform var(--transition-fast); }
.topic-option { display: flex; min-height: 50px; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; font-size: 0.92rem; }
.topic-option:hover:not(:disabled), .history-item:hover { border-color: var(--color-primary); background: color-mix(in srgb, var(--color-primary) 6%, var(--bg-secondary)); transform: translateY(-1px); }
.topic-option:disabled { cursor: wait; opacity: 0.65; }
.topic-option .el-icon { color: var(--color-primary); }
.planning-state { display: flex; align-items: center; gap: 14px; margin-top: 28px; padding: 18px 20px; border-left: 3px solid var(--color-primary); border-radius: 6px; background: color-mix(in srgb, var(--color-primary) 7%, var(--bg-secondary)); }
.planning-state__indicator { color: var(--color-primary); font-size: 1.3rem; }.planning-state__title { margin: 0; color: var(--text-primary); font-weight: 700; }.planning-state__copy { margin: 3px 0 0; color: var(--text-secondary); font-size: 0.9rem; }.planning-state :deep(.el-button) { margin-left: auto; }
.plan-result { border-top: 1px solid var(--border-color); padding-top: 30px; }
.plan-result__header { align-items: flex-start; justify-content: space-between; gap: 24px; }.plan-result h2 { font-size: 1.8rem; }.plan-result__summary { max-width: 650px; margin: 10px 0 0; color: var(--text-secondary); line-height: 1.65; }
.plan-result__actions { flex: 0 0 auto; flex-wrap: wrap; justify-content: flex-end; gap: 10px; }.duration-chip, .step-meta span, .priority-badge { display: inline-flex; align-items: center; gap: 5px; }.duration-chip { min-height: 32px; padding: 0 10px; border: 1px solid var(--border-color-light); border-radius: 999px; color: var(--text-secondary); font-size: 0.84rem; white-space: nowrap; }.plan-alert { margin-top: 20px; }
.plan-steps { display: grid; gap: 0; margin: 28px 0 0; padding: 0; list-style: none; border-top: 1px solid var(--border-color-light); }.plan-step { display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 16px; padding: 24px 0; border-bottom: 1px solid var(--border-color-light); }.plan-step__number { display: grid; width: 36px; height: 36px; place-items: center; border: 1px solid color-mix(in srgb, var(--color-primary) 40%, var(--border-color)); border-radius: 50%; color: var(--color-primary); font-size: 0.78rem; font-weight: 800; }.plan-step__topline { justify-content: space-between; gap: 12px; }.plan-step h3 { margin: 0; color: var(--text-primary); font-size: 1.05rem; line-height: 1.4; }.plan-step__body > p { margin: 8px 0 0; color: var(--text-secondary); line-height: 1.65; }
.priority-badge { padding: 3px 8px; border-radius: 999px; font-size: 0.76rem; white-space: nowrap; }.priority-badge--easy { color: #357a57; background: rgba(44, 122, 75, 0.12); }.priority-badge--medium { color: #8a631a; background: rgba(184, 121, 24, 0.13); }.priority-badge--hard { color: #9a493e; background: rgba(180, 72, 60, 0.12); }
.step-meta { flex-wrap: wrap; gap: 12px; margin-top: 14px; color: var(--text-muted); font-size: 0.84rem; }.step-meta span { white-space: nowrap; }.step-meta .el-icon { color: var(--color-primary); }.step-outcome { margin-top: 14px; padding: 10px 12px; border-left: 2px solid var(--color-primary-light); background: var(--bg-tertiary); }.step-outcome span { color: var(--text-muted); font-size: 0.76rem; font-weight: 700; }.step-outcome p { margin: 3px 0 0; color: var(--text-secondary); font-size: 0.88rem; line-height: 1.55; }
.empty-plan { display: grid; min-height: 160px; place-items: center; align-content: center; gap: 10px; border-top: 1px solid var(--border-color-light); color: var(--text-muted); text-align: center; }.empty-plan .el-icon { color: var(--color-primary); font-size: 1.45rem; }.empty-plan p { margin: 0; }
.drawer-title { width: 100%; justify-content: space-between; gap: 16px; }.history-list { display: grid; gap: 10px; }.history-item { display: grid; gap: 7px; padding: 14px; }.history-item__topline { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 10px; }.history-item__title { min-width: 0; overflow: hidden; color: var(--text-primary); font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }.history-item__meta { color: var(--text-muted); font-size: 0.82rem; }.history-item__status { flex: 0 0 auto; padding: 2px 7px; border-radius: 999px; color: #745717; background: rgba(180, 126, 28, 0.13); font-size: 0.72rem; font-weight: 700; }.history-item__status[data-status="published"] { color: #2f6e52; background: rgba(47, 110, 82, 0.12); }.history-item__status[data-status="discarded"] { color: #6d5b55; background: rgba(109, 91, 85, 0.12); }
@media (max-width: 680px) { .advisor-header h1 { font-size: 2rem; } .plan-result h2 { font-size: 1.55rem; } .advisor-page { padding-top: 24px; }.advisor-header, .plan-result__header, .composer-footer { align-items: stretch; flex-direction: column; }.advisor-header { gap: 18px; }.history-button { align-self: flex-end; }.composer-footer :deep(.el-segmented) { width: 100%; }.composer-footer :deep(.el-button) { width: 100%; }.topic-list { grid-template-columns: 1fr; }.plan-result__actions { justify-content: flex-start; }.plan-result__actions :deep(.el-button) { width: 100%; }.plan-step { grid-template-columns: 36px minmax(0, 1fr); gap: 12px; }.plan-step__number { width: 30px; height: 30px; }.plan-step__topline { align-items: flex-start; flex-direction: column; }.planning-state { align-items: flex-start; }.planning-state :deep(.el-button) { margin-left: 0; } }

.execution-choice { display: flex; align-items: center; gap: 10px; color: var(--text-muted); font-size: 0.82rem; font-weight: 700; }
.plan-result__intro { min-width: 0; flex: 1; }
.plan-title-input { max-width: 680px; }
.plan-title-input :deep(.el-input__wrapper) { padding: 4px 0; border-radius: 0; box-shadow: 0 1px 0 var(--border-color); background: transparent; }
.plan-title-input :deep(.el-input__inner) { height: auto; color: var(--text-primary); font-size: 1.55rem; font-weight: 800; line-height: 1.35; }
.plan-summary-input { max-width: 680px; margin-top: 10px; }
.plan-summary-input :deep(.el-textarea__inner), .step-description-input :deep(.el-textarea__inner) { border-radius: 6px; background: var(--bg-secondary); line-height: 1.65; }
.plan-goal-fields, .step-editor-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
.editor-field { display: grid; min-width: 0; gap: 7px; color: var(--text-secondary); font-size: 0.82rem; font-weight: 700; }
.editor-field--wide, .approval-choice { grid-column: 1 / -1; }
.editor-field :deep(.el-select), .editor-field :deep(.el-segmented) { width: 100%; }
.goal-outcome { max-width: 680px; margin-top: 16px; padding: 11px 0 0 14px; border-left: 2px solid var(--color-primary-light); }
.goal-outcome span { color: var(--text-muted); font-size: 0.76rem; font-weight: 700; }
.goal-outcome p { margin: 4px 0 0; color: var(--text-secondary); line-height: 1.6; }
.step-title-input { min-width: 0; flex: 1; }
.step-title-input :deep(.el-input__wrapper) { padding: 0; border-radius: 0; box-shadow: 0 1px 0 var(--border-color); background: transparent; }
.step-title-input :deep(.el-input__inner) { color: var(--text-primary); font-size: 1.02rem; font-weight: 700; }
.step-description-input { margin-top: 10px; }
.step-editor-grid { padding-top: 4px; }
.approval-choice { margin-right: 0; color: var(--text-secondary); font-weight: 500; }
.step-topline-actions { display: flex; flex: 0 0 auto; align-items: center; gap: 4px; }
.priority-badge--manual { color: #316d57; background: rgba(49, 109, 87, 0.12); }
.plan-editor-actions { display: flex; justify-content: center; padding: 18px 0 4px; }
@media (max-width: 680px) { .execution-choice { align-items: stretch; flex-direction: column; }.execution-choice :deep(.el-segmented) { width: 100%; }.plan-result__actions > .el-button { width: 100%; }.step-topline-actions { width: 100%; justify-content: space-between; }.plan-goal-fields, .step-editor-grid { grid-template-columns: minmax(0, 1fr); }.editor-field--wide, .approval-choice { grid-column: auto; } }
</style>
