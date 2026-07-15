<template>
  <div class="advisor-page">
    <div class="advisor-shell">
      <header class="advisor-header">
        <div>
          <p class="advisor-eyebrow">行动规划</p>
          <h1>把想法整理成可完成的步骤</h1>
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
              aria-label="方案说明"
            />
            <p v-else-if="advisorResult.goal.description" class="plan-result__summary">{{ advisorResult.goal.description }}</p>
          </div>
          <div class="plan-result__actions">
            <span v-if="estimatedDuration" class="duration-chip"><el-icon><Clock /></el-icon>{{ estimatedDuration }}</span>
            <el-button :icon="EditPen" @click="isEditingPlan = !isEditingPlan">
              {{ isEditingPlan ? '完成调整' : '调整方案' }}
            </el-button>
            <el-button type="primary" :icon="CircleCheck" :loading="isPublishing" :disabled="!canPublish" @click="publishPlan">
              创建并开始
            </el-button>
          </div>
        </header>

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
                :aria-label="'第 ' + (index + 1) + ' 步说明'"
              />
              <p v-else>{{ step.description }}</p>
              <div class="step-meta">
                <span v-if="estimatedMinutes(step)"><el-icon><Clock /></el-icon>约 {{ estimatedMinutes(step) }} 分钟</span>
                <span>{{ index === 0 ? '可以立即开始' : '上一项完成后开始' }}</span>
              </div>
              <div v-if="getDeliverables(step).length" class="step-outcome">
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
          <span class="history-item__title">{{ item.goal.title }}</span>
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
import { formatAxiosErrorMessage } from '@/utils/apiPayload'

const HISTORY_KEY = 'advisor_plan_history_v2'
const HISTORY_LIMIT = 12
const executionModes = [
  { label: '自己推进', value: 'manual' },
  { label: '协作完成', value: 'assisted' },
  { label: '自动执行', value: 'agent' }
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

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function requiredText(value, message = '生成的方案不完整，请重新生成。') {
  const text = typeof value === 'string' ? value.trim() : ''
  if (!text) throw new Error(message)
  return text
}

function normalizeStep(step, index, mode) {
  if (!isPlainObject(step)) throw new Error('生成的步骤不完整，请重新生成。')
  const kind = ['manual', 'agent', 'tool', 'review'].includes(step.kind)
    ? step.kind
    : (mode === 'agent' ? 'agent' : 'manual')
  return {
    client_key: String(step.client_key || ('step-' + (index + 1))),
    title: requiredText(step.title),
    description: typeof step.description === 'string' ? step.description.trim() : '',
    kind,
    depends_on: Array.isArray(step.depends_on) ? step.depends_on.map(String) : [],
    parallel_group: step.parallel_group || null,
    max_attempts: Number.isInteger(step.max_attempts) ? step.max_attempts : (kind === 'agent' ? 3 : 1),
    requires_approval: Boolean(step.requires_approval),
    completion_criteria: isPlainObject(step.completion_criteria) ? step.completion_criteria : {},
    input_data: isPlainObject(step.input_data) ? step.input_data : {}
  }
}

function normalizePlan(result) {
  if (!isPlainObject(result) || !isPlainObject(result.goal) || !isPlainObject(result.run)) {
    throw new Error('生成的方案不完整，请重新生成。')
  }
  const mode = ['manual', 'assisted', 'agent'].includes(result.run.mode) ? result.run.mode : executionMode.value
  if (!Array.isArray(result.run.steps) || !result.run.steps.length) throw new Error('方案中没有可以执行的步骤。')
  return {
    goal: {
      title: requiredText(result.goal.title),
      description: typeof result.goal.description === 'string' ? result.goal.description.trim() : String(result.summary || '').trim(),
      desired_outcome: typeof result.goal.desired_outcome === 'string' && result.goal.desired_outcome.trim()
        ? result.goal.desired_outcome.trim()
        : requiredText(result.goal.title),
      priority: ['low', 'medium', 'high'].includes(result.goal.priority) ? result.goal.priority : 'medium',
      metadata: isPlainObject(result.goal.metadata) ? result.goal.metadata : {}
    },
    run: {
      title: typeof result.run.title === 'string' && result.run.title.trim() ? result.run.title.trim() : requiredText(result.goal.title),
      objective: typeof result.run.objective === 'string' && result.run.objective.trim() ? result.run.objective.trim() : requiredText(result.goal.title),
      mode,
      metadata: isPlainObject(result.run.metadata) ? result.run.metadata : {},
      steps: result.run.steps.map((step, index) => normalizeStep(step, index, mode))
    },
    estimated_duration: typeof result.estimated_duration === 'string' ? result.estimated_duration.trim() : '',
    meta: {
      fallback: Boolean(result.meta?.used_fallback ?? result.meta?.fallback),
      needs_review: result.meta?.needs_review !== false
    }
  }
}

function readHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    return Array.isArray(value)
      ? value.filter((item) => item?.id && item?.createdAt && item?.goal?.title && Array.isArray(item?.run?.steps)).slice(0, HISTORY_LIMIT)
      : []
  } catch {
    localStorage.removeItem(HISTORY_KEY)
    return []
  }
}

function saveHistory(result) {
  const entry = {
    ...JSON.parse(JSON.stringify(result)),
    id: String(Date.now()) + '-' + Math.random().toString(36).slice(2, 8),
    createdAt: new Date().toISOString()
  }
  historyList.value = [entry, ...historyList.value].slice(0, HISTORY_LIMIT)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(historyList.value))
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
    advisorResult.value = normalizePlan(result)
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

function buildRunSpecification(plan) {
  const steps = plan.run.steps.map((step, index) => {
    const clientKey = 'step-' + (index + 1)
    return {
      ...step,
      client_key: clientKey,
      title: step.title.trim(),
      description: String(step.description || '').trim(),
      depends_on: index ? ['step-' + index] : []
    }
  })
  return {
    ...plan.run,
    title: plan.goal.title.trim(),
    objective: plan.goal.desired_outcome || plan.goal.title.trim(),
    idempotency_key: 'advisor-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10),
    steps
  }
}

async function publishPlan() {
  if (!canPublish.value) {
    ElMessage.warning('目标名称和每一步都需要填写。')
    return
  }
  isPublishing.value = true
  let createdGoal = null
  try {
    const plan = advisorResult.value
    createdGoal = await goalsApi.create({
      ...plan.goal,
      title: plan.goal.title.trim(),
      description: String(plan.goal.description || '').trim()
    })
    let run = await runsApi.create(createdGoal.goal_id, buildRunSpecification(plan))
    run = await runsApi.start(run.run_id)
    ElMessage.success('目标已加入正在推进。')
    advisorResult.value = null
    userQuery.value = ''
    await router.push('/tasks')
  } catch (error) {
    if (createdGoal?.goal_id) {
      ElMessage.error('目标已创建，但行动未能开始。可以在目标页继续处理。')
      await router.push('/tasks')
    } else {
      ElMessage.error(formatAxiosErrorMessage(error, '创建目标失败，请稍后重试。'))
    }
  } finally {
    isPublishing.value = false
  }
}

function useQuickTopic(topic) {
  userQuery.value = topic
  submitQuery()
}

function addPlanStep() {
  const index = learningSteps.value.length
  learningSteps.value.push({
    client_key: 'step-' + (index + 1),
    title: '新的行动步骤',
    description: '',
    kind: advisorResult.value?.run?.mode === 'agent' ? 'agent' : 'manual',
    depends_on: index ? ['step-' + index] : [],
    parallel_group: null,
    max_attempts: advisorResult.value?.run?.mode === 'agent' ? 3 : 1,
    requires_approval: false,
    completion_criteria: {},
    input_data: {}
  })
}

function removePlanStep(index) {
  if (learningSteps.value.length <= 1) return
  learningSteps.value.splice(index, 1)
}

function estimatedMinutes(step) {
  const value = Number(step?.input_data?.estimated_minutes)
  return Number.isFinite(value) && value > 0 ? Math.round(value) : 0
}

function getDeliverables(step) {
  return Array.isArray(step?.completion_criteria?.deliverables) ? step.completion_criteria.deliverables : []
}

function kindLabel(kind) {
  return ({ manual: '自己完成', agent: '自动执行', tool: '工具协助', review: '需要确认' })[kind] || '自己完成'
}

function formatHistoryDate(value) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function restoreFromHistory(item) {
  try {
    advisorResult.value = normalizePlan(item)
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
.drawer-title { width: 100%; justify-content: space-between; gap: 16px; }.history-list { display: grid; gap: 10px; }.history-item { display: grid; gap: 6px; padding: 14px; }.history-item__title { overflow: hidden; color: var(--text-primary); font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }.history-item__meta { color: var(--text-muted); font-size: 0.82rem; }
@media (max-width: 680px) { .advisor-header h1 { font-size: 2rem; } .plan-result h2 { font-size: 1.55rem; } .advisor-page { padding-top: 24px; }.advisor-header, .plan-result__header, .composer-footer { align-items: stretch; flex-direction: column; }.advisor-header { gap: 18px; }.history-button { align-self: flex-end; }.composer-footer :deep(.el-segmented) { width: 100%; }.composer-footer :deep(.el-button) { width: 100%; }.topic-list { grid-template-columns: 1fr; }.plan-result__actions { justify-content: flex-start; }.plan-result__actions :deep(.el-button) { width: 100%; }.plan-step { grid-template-columns: 36px minmax(0, 1fr); gap: 12px; }.plan-step__number { width: 30px; height: 30px; }.plan-step__topline { align-items: flex-start; flex-direction: column; }.planning-state { align-items: flex-start; }.planning-state :deep(.el-button) { margin-left: 0; } }

.execution-choice { display: flex; align-items: center; gap: 10px; color: var(--text-muted); font-size: 0.82rem; font-weight: 700; }
.plan-result__intro { min-width: 0; flex: 1; }
.plan-title-input { max-width: 680px; }
.plan-title-input :deep(.el-input__wrapper) { padding: 4px 0; border-radius: 0; box-shadow: 0 1px 0 var(--border-color); background: transparent; }
.plan-title-input :deep(.el-input__inner) { height: auto; color: var(--text-primary); font-size: 1.55rem; font-weight: 800; line-height: 1.35; }
.plan-summary-input { max-width: 680px; margin-top: 10px; }
.plan-summary-input :deep(.el-textarea__inner), .step-description-input :deep(.el-textarea__inner) { border-radius: 6px; background: var(--bg-secondary); line-height: 1.65; }
.step-title-input { min-width: 0; flex: 1; }
.step-title-input :deep(.el-input__wrapper) { padding: 0; border-radius: 0; box-shadow: 0 1px 0 var(--border-color); background: transparent; }
.step-title-input :deep(.el-input__inner) { color: var(--text-primary); font-size: 1.02rem; font-weight: 700; }
.step-description-input { margin-top: 10px; }
.step-topline-actions { display: flex; flex: 0 0 auto; align-items: center; gap: 4px; }
.priority-badge--manual { color: #316d57; background: rgba(49, 109, 87, 0.12); }
.priority-badge--agent { color: #805f18; background: rgba(176, 124, 24, 0.14); }
.priority-badge--tool { color: #3f6596; background: rgba(63, 101, 150, 0.12); }
.priority-badge--review { color: #914c43; background: rgba(145, 76, 67, 0.12); }
.plan-editor-actions { display: flex; justify-content: center; padding: 18px 0 4px; }
@media (max-width: 680px) { .execution-choice { align-items: stretch; flex-direction: column; }.execution-choice :deep(.el-segmented) { width: 100%; }.plan-result__actions > .el-button { width: 100%; }.step-topline-actions { width: 100%; justify-content: space-between; } }
</style>
