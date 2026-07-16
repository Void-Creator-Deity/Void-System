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
        <div>
          <p class="planning-state__title">正在梳理行动路径</p>
          <p class="planning-state__copy">正在结合目标和已有成长资料，整理出可以逐步完成的安排。</p>
        </div>
        <el-button text type="primary" @click="cancelGeneration">取消</el-button>
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
            <el-button v-if="canEditPlan" :icon="EditPen" @click="togglePlanEditing">
              {{ isEditingPlan ? '完成调整' : '调整方案' }}
            </el-button>
            <el-button type="primary" :icon="CircleCheck" :loading="isPublishing" :disabled="!canPublish" @click="publishPlan">
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
                  <span class="priority-badge" :class="'priority-badge--' + step.kind">{{ kindLabel(step.kind) }}</span>
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
                  <span>由谁完成</span>
                  <el-select v-model="step.kind" aria-label="步骤完成方式">
                    <el-option v-for="option in stepKindOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </label>
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
            <p class="section-kicker">本机记录</p>
            <h2>最近方案</h2>
          </div>
          <el-tooltip content="清空方案历史" placement="bottom">
            <el-button :icon="Delete" circle text type="danger" :disabled="!historyList.length" aria-label="清空方案历史" @click="clearHistory" />
          </el-tooltip>
        </div>
      </template>
      <div v-if="historyList.length" class="history-list">
        <button v-for="item in historyList" :key="item.id" class="history-item" type="button" @click="restoreFromHistory(item)">
          <span class="history-item__topline">
            <span class="history-item__title">{{ item.goal.title }}</span>
            <span class="history-item__status" :data-status="item.publication?.status">{{ publicationStatusLabel(item.publication?.status) }}</span>
          </span>
          <span class="history-item__meta">{{ formatHistoryDate(item.createdAt) }} · {{ item.run.steps.length }} 步</span>
        </button>
      </div>
      <el-empty v-else description="还没有生成过方案" />
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, CircleCheck, Clock, Delete, Document, EditPen, Loading, MagicStick, Plus } from '@element-plus/icons-vue'
import { plansApi } from '@/api/plans'
import { goalsApi } from '@/api/goals'
import { runsApi } from '@/api/runs'
import {
  PUBLICATION_STATUS,
  buildGoalCreateInput,
  buildRunSpecification,
  normalizeHistoryEntry,
  normalizePlanDraft,
  resetMissingPublication
} from '@/domain/planDraft'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'

const props = defineProps({ embedded: { type: Boolean, default: false } })
const emit = defineEmits(['published'])
const embedded = computed(() => props.embedded)

const HISTORY_KEY = 'advisor_plan_history_v2'
const HISTORY_LIMIT = 12
const executionModes = [
  { label: '自己完成', value: 'manual' },
  { label: '和系统一起', value: 'assisted' },
  { label: '交给系统', value: 'agent' }
]
const priorityOptions = [
  { label: '一般', value: 'low' },
  { label: '重要', value: 'medium' },
  { label: '优先', value: 'high' }
]
const stepKindOptions = [
  { label: '自己完成', value: 'manual' },
  { label: '交给系统', value: 'agent' },
  { label: '使用工具', value: 'tool' },
  { label: '检查确认', value: 'review' }
]
const quickTopics = [
  { id: 'project', text: '完成一个可以公开展示的个人作品' },
  { id: 'habit', text: '建立一个能够长期坚持的健康习惯' },
  { id: 'learning', text: '系统掌握一项新的专业技能' },
  { id: 'knowledge', text: '整理散落资料并形成可复用的知识体系' }
]

const router = useRouter()
const userQuery = ref('')
const executionMode = ref('assisted')
const isLoading = ref(false)
const isPublishing = ref(false)
const isEditingPlan = ref(false)
const advisorResult = ref(null)
const showHistory = ref(false)
const historyList = ref(readHistory())
const advisorAbortController = ref(null)

const learningSteps = computed(() => advisorResult.value?.run?.steps || [])
const estimatedDuration = computed(() => {
  const value = String(advisorResult.value?.estimated_duration || '').trim()
  return value && value !== '—' ? value : ''
})
const canPublish = computed(() => {
  const goal = advisorResult.value?.goal
  return Boolean(goal?.title?.trim() && learningSteps.value.length && learningSteps.value.every((step) => step?.title?.trim()))
})
const canEditPlan = computed(() => advisorResult.value?.publication?.status === PUBLICATION_STATUS.DRAFT && !isPublishing.value)
const publicationActionLabel = computed(() => {
  const status = advisorResult.value?.publication?.status
  if (status === PUBLICATION_STATUS.PUBLISHED) return '打开行动'
  if (status === PUBLICATION_STATUS.GOAL_CREATED || status === PUBLICATION_STATUS.RUN_CREATED) return '继续发布'
  return '创建并开始'
})
const publicationNotice = computed(() => {
  const status = advisorResult.value?.publication?.status
  if (status === PUBLICATION_STATUS.GOAL_CREATED) return '目标已经保存。继续发布会从创建行动这一步接着进行。'
  if (status === PUBLICATION_STATUS.RUN_CREATED) return '行动已经建立。继续发布会从启动这一步接着进行。'
  if (status === PUBLICATION_STATUS.PUBLISHED) return '这份方案已经发布，可以直接打开对应行动。'
  return ''
})

function readHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    if (!Array.isArray(value)) return []
    const normalized = []
    for (const item of value) {
      try {
        normalized.push(normalizeHistoryEntry(item))
      } catch {
        // A damaged local entry is skipped without hiding the remaining plans.
      }
    }
    const entries = normalized.slice(0, HISTORY_LIMIT)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries))
    return entries
  } catch {
    localStorage.removeItem(HISTORY_KEY)
    return []
  }
}

function saveHistory(result) {
  const copy = JSON.parse(JSON.stringify(result))
  const existing = historyList.value.find((item) => item.id === copy.draft_id)
  const entry = normalizeHistoryEntry({
    ...copy,
    id: copy.draft_id,
    createdAt: existing?.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString()
  })
  historyList.value = [entry, ...historyList.value.filter((item) => item.id !== entry.id)].slice(0, HISTORY_LIMIT)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(historyList.value))
}

function updatePublication(updates) {
  if (!advisorResult.value) return
  advisorResult.value.publication = {
    ...(advisorResult.value.publication || {}),
    ...updates,
    updated_at: new Date().toISOString()
  }
  saveHistory(advisorResult.value)
}

async function submitQuery() {
  const query = userQuery.value.trim()
  if (!query) {
    ElMessage.warning('先写下这次想完成的结果。')
    return
  }

  isLoading.value = true
  isEditingPlan.value = false
  advisorAbortController.value = new AbortController()
  try {
    const result = await plansApi.create(query, {
      executionMode: executionMode.value,
      maxSteps: 8,
      config: { signal: advisorAbortController.value.signal, timeout: 900000 }
    })
    advisorResult.value = normalizePlanDraft(result, executionMode.value)
    saveHistory(advisorResult.value)
    ElMessage.success('方案已生成，可以先调整再开始。')
  } catch (error) {
    if (error?.name === 'CanceledError' || error?.name === 'AbortError' || /aborted|canceled/i.test(String(error?.message || ''))) {
      ElMessage.info('已取消本次生成。')
    } else {
      ElMessage.error(formatAxiosErrorMessage(error, error?.message || '暂时无法生成方案，请稍后重试。'))
    }
  } finally {
    isLoading.value = false
    advisorAbortController.value = null
  }
}

function cancelGeneration() {
  advisorAbortController.value?.abort()
}

function isNotFoundError(error) {
  return Number(error?.response?.status) === 404
}

function repairPublication(resource) {
  advisorResult.value = resetMissingPublication(advisorResult.value, resource)
  isEditingPlan.value = false
  saveHistory(advisorResult.value)
}

async function ensurePublishedGoal() {
  let goalId = advisorResult.value?.publication?.goal_id
  if (goalId) {
    try {
      const existing = await goalsApi.get(goalId)
      return existing.goal
    } catch (error) {
      if (!isNotFoundError(error)) throw error
      repairPublication('goal')
      goalId = null
    }
  }

  const goal = await goalsApi.create(buildGoalCreateInput(advisorResult.value))
  updatePublication({
    status: PUBLICATION_STATUS.GOAL_CREATED,
    goal_id: goal.goal_id,
    run_id: null
  })
  return goal
}

async function ensurePublishedRun(goalId) {
  let runId = advisorResult.value?.publication?.run_id
  if (runId) {
    try {
      const existing = await runsApi.get(runId)
      if (existing.goal_id === goalId) return existing
      repairPublication('run')
      runId = null
    } catch (error) {
      if (!isNotFoundError(error)) throw error
      repairPublication('run')
      runId = null
    }
  }

  const run = await runsApi.create(goalId, buildRunSpecification(advisorResult.value))
  updatePublication({
    status: PUBLICATION_STATUS.RUN_CREATED,
    goal_id: goalId,
    run_id: run.run_id
  })
  return run
}

async function publishPlan() {
  if (!canPublish.value) {
    ElMessage.warning('目标名称和每一步都需要填写。')
    return
  }
  isPublishing.value = true
  isEditingPlan.value = false
  saveHistory(advisorResult.value)
  try {
    const draftId = advisorResult.value.draft_id
    const goal = await ensurePublishedGoal()
    let run = await ensurePublishedRun(goal.goal_id)
    if (run.status === 'queued') run = await runsApi.start(run.run_id)
    updatePublication({
      status: PUBLICATION_STATUS.PUBLISHED,
      goal_id: goal.goal_id,
      run_id: run.run_id
    })

    ElMessage.success('方案已经加入行动工作台。')
    emit('published', { goal, run, draftId })
    advisorResult.value = null
    userQuery.value = ''
    if (!props.embedded) await router.push({ path: '/tasks', query: { view: 'focus', run: run.run_id } })
  } catch (error) {
    const stage = advisorResult.value?.publication?.status
    const message = stage === PUBLICATION_STATUS.GOAL_CREATED
      ? '目标已经保存，但行动还没建立。再次点击会从这里继续。'
      : stage === PUBLICATION_STATUS.RUN_CREATED
        ? '行动已经建立，但还没启动。再次点击会从这里继续。'
        : formatAxiosErrorMessage(error, '发布方案失败，请稍后重试。')
    ElMessage.error(message)
  } finally {
    isPublishing.value = false
  }
}

function useQuickTopic(topic) {
  userQuery.value = topic
  submitQuery()
}

function togglePlanEditing() {
  if (!canEditPlan.value) return
  isEditingPlan.value = !isEditingPlan.value
  if (!isEditingPlan.value) saveHistory(advisorResult.value)
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
    kind: advisorResult.value?.run?.mode === 'agent' ? 'agent' : 'manual',
    depends_on: previousKey ? [previousKey] : [],
    parallel_group: null,
    max_attempts: advisorResult.value?.run?.mode === 'agent' ? 3 : 1,
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

function kindLabel(kind) {
  return ({ manual: '自己完成', agent: '交给系统', tool: '使用工具', review: '检查确认' })[kind] || '自己完成'
}

function publicationStatusLabel(status) {
  return ({
    [PUBLICATION_STATUS.DRAFT]: '待确认',
    [PUBLICATION_STATUS.GOAL_CREATED]: '可继续',
    [PUBLICATION_STATUS.RUN_CREATED]: '待启动',
    [PUBLICATION_STATUS.PUBLISHED]: '已发布'
  })[status] || '待确认'
}

function formatHistoryDate(value) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function restoreFromHistory(item) {
  try {
    advisorResult.value = normalizePlanDraft(item, executionMode.value)
    userQuery.value = advisorResult.value.goal.desired_outcome || advisorResult.value.goal.title
    executionMode.value = advisorResult.value.run.mode
    isEditingPlan.value = false
    showHistory.value = false
  } catch {
    ElMessage.warning('这份旧方案无法继续使用，请重新生成。')
  }
}

async function clearHistory() {
  try {
    await ElMessageBox.confirm('确定清空这台设备上的方案历史吗？', '清空方案历史', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning'
    })
    historyList.value = []
    localStorage.removeItem(HISTORY_KEY)
    ElMessage.success('方案历史已清空。')
  } catch {
    // Closing the confirmation dialog leaves the history untouched.
  }
}
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
.drawer-title { width: 100%; justify-content: space-between; gap: 16px; }.history-list { display: grid; gap: 10px; }.history-item { display: grid; gap: 7px; padding: 14px; }.history-item__topline { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 10px; }.history-item__title { min-width: 0; overflow: hidden; color: var(--text-primary); font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }.history-item__meta { color: var(--text-muted); font-size: 0.82rem; }.history-item__status { flex: 0 0 auto; padding: 2px 7px; border-radius: 999px; color: #745717; background: rgba(180, 126, 28, 0.13); font-size: 0.72rem; font-weight: 700; }.history-item__status[data-status="published"] { color: #2f6e52; background: rgba(47, 110, 82, 0.12); }.history-item__status[data-status="run_created"] { color: #3d638f; background: rgba(61, 99, 143, 0.12); }
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
.priority-badge--agent { color: #805f18; background: rgba(176, 124, 24, 0.14); }
.priority-badge--tool { color: #3f6596; background: rgba(63, 101, 150, 0.12); }
.priority-badge--review { color: #914c43; background: rgba(145, 76, 67, 0.12); }
.plan-editor-actions { display: flex; justify-content: center; padding: 18px 0 4px; }
@media (max-width: 680px) { .execution-choice { align-items: stretch; flex-direction: column; }.execution-choice :deep(.el-segmented) { width: 100%; }.plan-result__actions > .el-button { width: 100%; }.step-topline-actions { width: 100%; justify-content: space-between; }.plan-goal-fields, .step-editor-grid { grid-template-columns: minmax(0, 1fr); }.editor-field--wide, .approval-choice { grid-column: auto; } }
</style>
