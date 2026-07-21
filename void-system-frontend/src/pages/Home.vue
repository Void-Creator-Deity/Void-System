<template>
  <section class="dashboard">
    <header class="dashboard-header">
      <div>
        <p class="eyebrow">今天</p>
        <h1>把注意力留给下一件重要的事。</h1>
        <p class="dashboard-header__copy">从正在推进的行动继续，或先把一个想法整理成清晰、可完成的步骤。</p>
      </div>
      <div class="dashboard-header__actions">
        <el-button :icon="MagicStick" plain @click="router.push('/advisor')">整理方案</el-button>
        <el-button type="primary" :icon="List" @click="router.push('/tasks')">行动工作台</el-button>
      </div>
    </header>

    <div v-if="isLoading" class="dashboard-loading"><el-icon class="is-loading"><Loading /></el-icon><span>正在整理你的进展...</span></div>

    <template v-else>
      <section class="summary-strip" aria-label="进展概览">
        <div class="summary-metric"><span>活跃目标</span><strong>{{ activeGoalCount }}</strong><small>仍在推进</small></div>
        <div class="summary-metric"><span>当前行动</span><strong>{{ activeRunCount }}</strong><small>等待或进行中</small></div>
        <div class="summary-metric"><span>本周完成</span><strong>{{ completedThisWeek }}</strong><small>已经收尾</small></div>
        <button class="summary-balance" type="button" @click="router.push('/growth')"><span>可用积分</span><strong>{{ balance }}</strong><el-icon><ArrowRight /></el-icon></button>
      </section>

      <div class="dashboard-grid">
        <section class="priority-section" aria-labelledby="priority-title">
          <div class="section-heading"><div><p class="eyebrow">优先事项</p><h2 id="priority-title">接下来推进</h2></div><el-button text :icon="ArrowRight" @click="router.push('/tasks')">查看全部</el-button></div>
          <div v-if="priorityRuns.length" class="priority-list">
            <button v-for="run in priorityRuns" :key="run.run_id" class="priority-row" type="button" @click="router.push('/tasks')">
              <span class="priority-row__status" :class="'priority-row__status--' + run.status"><el-icon v-if="run.status === 'running'"><VideoPlay /></el-icon><el-icon v-else><Clock /></el-icon></span>
              <span class="priority-row__copy"><strong>{{ run.title || goalTitle(run.goal_id) }}</strong><small>{{ runDescription(run) }}</small></span>
              <span class="priority-row__meta"><el-tag size="small" effect="plain" :type="runStatusType(run.status)">{{ runStatusLabel(run.status) }}</el-tag><small>{{ runProgress(run) }}% 已完成</small></span>
              <el-icon class="priority-row__arrow"><ArrowRight /></el-icon>
            </button>
          </div>
          <div v-else class="empty-state"><el-icon><CircleCheck /></el-icon><h3>暂时没有待推进的行动</h3><p>创建一个目标，或把脑海里的想法交给规划助手整理。</p><el-button type="primary" @click="router.push('/advisor')">整理一个方案</el-button></div>
        </section>

        <aside class="dashboard-aside">
          <section class="quick-section" aria-labelledby="quick-title">
            <div class="section-heading"><div><p class="eyebrow">常用入口</p><h2 id="quick-title">继续工作</h2></div></div>
            <div class="quick-links">
              <button v-for="link in quickLinks" :key="link.to" type="button" class="quick-link" @click="router.push(link.to)"><el-icon><component :is="link.icon" /></el-icon><span><strong>{{ link.label }}</strong><small>{{ link.description }}</small></span><el-icon><ArrowRight /></el-icon></button>
            </div>
          </section>

          <section class="activity-section" aria-labelledby="activity-title">
            <div class="section-heading"><div><p class="eyebrow">最近动态</p><h2 id="activity-title">成长记录</h2></div><el-button text :icon="ArrowRight" @click="router.push('/growth')">查看</el-button></div>
            <div v-if="activities.length" class="activity-list"><div v-for="activity in activities" :key="activity.id || activity.created_at + activity.amount" class="activity-row"><span class="activity-row__mark" :class="Number(activity.amount) >= 0 ? 'activity-row__mark--plus' : 'activity-row__mark--minus'"></span><span><strong>{{ activityLabel(activity) }}</strong><small>{{ formatDate(activity.created_at) }}</small></span><b :class="Number(activity.amount) >= 0 ? 'is-positive' : 'is-negative'">{{ Number(activity.amount) >= 0 ? '+' : '' }}{{ activity.amount || 0 }}</b></div></div>
            <p v-else class="muted-copy">完成行动后，获得的成长记录会出现在这里。</p>
          </section>
        </aside>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, ChatDotRound, CircleCheck, Clock, Collection, Document, List, Loading, MagicStick, TrendCharts, VideoPlay } from '@element-plus/icons-vue'
import { goalsApi } from '@/api/goals'
import { runsApi } from '@/api/runs'
import { growthProfileApi } from '@/api/growthProfile'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'

const router = useRouter()
const goals = ref([])
const runs = ref([])
const balance = ref(0)
const activities = ref([])
const isLoading = ref(true)

const activeGoalCount = computed(() => goals.value.filter((goal) => goal.status === 'active').length)
const activeRunCount = computed(() => runs.value.filter((run) => !terminalRun(run)).length)
const completedThisWeek = computed(() => runs.value.filter((run) => run.status === 'completed' && isThisWeek(run.completed_at || run.updated_at)).length)
const priorityRuns = computed(() => runs.value
  .filter((run) => !terminalRun(run))
  .sort((left, right) => scoreRun(right) - scoreRun(left))
  .slice(0, 5))
const quickLinks = [
  { to: '/tasks', label: '行动', description: '查看目标、步骤和自动安排', icon: List },
  { to: '/advisor', label: '规划', description: '把一个想法整理成方案', icon: MagicStick },
  { to: '/documents', label: '资料', description: '管理个人参考资料', icon: Document },
  { to: '/qa', label: '知识问答', description: '从已有资料中寻找答案', icon: Collection },
  { to: '/growth', label: '成长', description: '查看能力与积分记录', icon: TrendCharts },
  { to: '/ai', label: '对话', description: '与助手一起思考和创作', icon: ChatDotRound }
]

function terminalRun(run) {
  return ['completed', 'failed', 'cancelled'].includes(run?.status)
}

function scoreRun(run) {
  const statusScore = ({ waiting_approval: 500, running: 400, queued: 300, paused: 200 })[run.status] || 100
  const updated = new Date(run.updated_at || run.created_at || 0).getTime()
  return statusScore + (Number.isFinite(updated) ? updated / 1e13 : 0)
}

function runProgress(run) {
  const total = Number(run?.step_count ?? run?.steps?.length ?? 0)
  const done = Number(run?.completed_steps ?? (run?.steps || []).filter((step) => ['completed', 'skipped'].includes(step.status)).length)
  return total ? Math.round(done / total * 100) : 0
}

function goalTitle(goalId) {
  return goals.value.find((goal) => goal.goal_id === goalId)?.title || '未命名目标'
}

function runDescription(run) {
  if (run.status === 'waiting_approval') return '有一步需要你确认后才能继续。'
  if (run.status === 'paused') return '已暂停，可以随时继续。'
  return goalTitle(run.goal_id)
}

function runStatusLabel(status) {
  return ({ queued: '准备开始', running: '进行中', paused: '已暂停', waiting_approval: '等待确认' })[status] || '待处理'
}

function runStatusType(status) {
  return ({ running: 'primary', waiting_approval: 'warning', paused: 'info', queued: '' })[status] || 'info'
}

function isThisWeek(value) {
  if (!value) return false
  const date = new Date(value)
  const now = new Date()
  const start = new Date(now)
  const day = (now.getDay() + 6) % 7
  start.setDate(now.getDate() - day)
  start.setHours(0, 0, 0, 0)
  return date >= start
}

function activityLabel(activity) {
  return activity.description || activity.source || (Number(activity.amount) >= 0 ? '完成行动获得积分' : '兑换消耗积分')
}

function formatDate(value) {
  if (!value) return '刚刚'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function loadDashboard() {
  isLoading.value = true
  try {
    const [loadedGoals, loadedRuns, loadedBalance, loadedActivity] = await Promise.all([
      goalsApi.list(),
      runsApi.list(),
      growthProfileApi.getGrowthPoints(),
      growthProfileApi.listGrowthPointActivity({ limit: 5 })
    ])
    goals.value = loadedGoals
    runs.value = loadedRuns
    balance.value = Number(loadedBalance?.growth_points || 0)
    activities.value = Array.isArray(loadedActivity?.history) ? loadedActivity.history.slice(0, 5) : []
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, '首页暂时无法加载。'))
  } finally {
    isLoading.value = false
  }
}

onMounted(loadDashboard)
</script>

<style scoped>
.dashboard { padding: 38px 0 54px; }.dashboard-header, .section-heading, .summary-strip, .priority-row, .quick-link, .activity-row { display: flex; align-items: center; }.dashboard-header { justify-content: space-between; gap: 24px; padding-bottom: 28px; border-bottom: 1px solid var(--border-color-light); }.eyebrow { margin: 0 0 6px; color: var(--color-primary); font-size: 12px; font-weight: 700; letter-spacing: 0; }.dashboard h1, .dashboard h2, .dashboard h3, .dashboard p { margin-top: 0; }.dashboard h1 { max-width: 620px; margin-bottom: 8px; color: var(--text-primary); font-size: 27px; line-height: 1.26; }.dashboard-header__copy { max-width: 610px; margin-bottom: 0; color: var(--text-secondary); font-size: 14px; line-height: 1.65; }.dashboard-header__actions { display: flex; flex: 0 0 auto; gap: 8px; }.dashboard-loading { display: grid; grid-template-columns: auto auto; justify-content: center; gap: 10px; padding: 110px 20px; color: var(--text-muted); }.summary-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(160px, 1.1fr); margin: 28px 0 34px; border-top: 1px solid var(--border-color-light); border-bottom: 1px solid var(--border-color-light); }.summary-metric, .summary-balance { display: grid; gap: 4px; min-height: 106px; padding: 20px; border-right: 1px solid var(--border-color-light); }.summary-metric > span, .summary-balance > span { color: var(--text-secondary); font-size: 13px; }.summary-metric strong, .summary-balance strong { color: var(--text-primary); font-size: 30px; line-height: 1.1; }.summary-metric small { color: var(--text-muted); font-size: 12px; }.summary-balance { grid-template-columns: 1fr auto; align-content: center; border: 0; color: inherit; background: color-mix(in srgb, var(--color-primary) 6%, transparent); cursor: pointer; text-align: left; }.summary-balance strong { grid-column: 1; color: var(--color-primary-dark); }.summary-balance .el-icon { grid-column: 2; grid-row: 1 / span 2; align-self: center; color: var(--color-primary); }.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.52fr) minmax(280px, .82fr); gap: 34px; }.priority-section { min-width: 0; }.dashboard-aside { display: grid; align-content: start; gap: 30px; padding-left: 30px; border-left: 1px solid var(--border-color-light); }.section-heading { justify-content: space-between; gap: 16px; margin-bottom: 14px; }.section-heading h2 { margin-bottom: 0; color: var(--text-primary); font-size: 17px; }.section-heading .eyebrow { margin-bottom: 3px; }.priority-list { border-top: 1px solid var(--border-color-light); }.priority-row { width: 100%; gap: 12px; padding: 16px 2px; border: 0; border-bottom: 1px solid var(--border-color-light); color: inherit; background: transparent; cursor: pointer; text-align: left; }.priority-row:hover strong { color: var(--color-primary-dark); }.priority-row__status { display: grid; flex: 0 0 30px; width: 30px; height: 30px; place-items: center; border: 1px solid var(--border-color); border-radius: 50%; color: var(--text-muted); }.priority-row__status--running { border-color: var(--color-primary); color: var(--color-primary); background: color-mix(in srgb, var(--color-primary) 8%, transparent); }.priority-row__copy { display: grid; min-width: 0; gap: 4px; }.priority-row__copy strong, .quick-link strong, .activity-row strong { overflow: hidden; color: var(--text-primary); font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }.priority-row__copy small, .quick-link small, .activity-row small { overflow: hidden; color: var(--text-secondary); font-size: 12px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }.priority-row__meta { display: grid; justify-items: end; gap: 5px; margin-left: auto; }.priority-row__meta small { color: var(--text-muted); font-size: 12px; }.priority-row__arrow { color: var(--text-muted); }.quick-links { border-top: 1px solid var(--border-color-light); }.quick-link { width: 100%; gap: 10px; padding: 12px 0; border: 0; border-bottom: 1px solid var(--border-color-light); color: inherit; background: transparent; cursor: pointer; text-align: left; }.quick-link > .el-icon:first-child { color: var(--color-primary); font-size: 18px; }.quick-link > span { display: grid; min-width: 0; flex: 1; gap: 3px; }.quick-link > .el-icon:last-child { color: var(--text-muted); font-size: 14px; }.activity-section { padding-top: 4px; }.activity-list { border-top: 1px solid var(--border-color-light); }.activity-row { gap: 9px; padding: 11px 0; border-bottom: 1px solid var(--border-color-light); }.activity-row__mark { width: 7px; height: 7px; border-radius: 50%; background: var(--color-success); }.activity-row__mark--minus { background: var(--color-warning); }.activity-row > span:nth-child(2) { display: grid; flex: 1; min-width: 0; gap: 3px; }.activity-row b { font-size: 13px; }.is-positive { color: var(--color-success); }.is-negative { color: var(--color-warning); }.muted-copy { margin-bottom: 0; color: var(--text-muted); font-size: 13px; line-height: 1.6; }.empty-state { display: grid; justify-items: start; gap: 9px; padding: 54px 0; color: var(--text-muted); }.empty-state > .el-icon { color: var(--color-primary); font-size: 30px; }.empty-state h3 { margin-bottom: 0; color: var(--text-primary); font-size: 17px; }.empty-state p { max-width: 370px; margin-bottom: 4px; color: var(--text-secondary); font-size: 13px; line-height: 1.6; }@media (max-width: 920px) { .dashboard-grid { grid-template-columns: 1fr; }.dashboard-aside { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; padding: 24px 0 0; border-top: 1px solid var(--border-color-light); border-left: 0; }.summary-strip { grid-template-columns: repeat(4, minmax(0, 1fr)); }.summary-balance { border-right: 0; } }@media (max-width: 640px) { .dashboard { padding: 26px 0 42px; }.dashboard-header { align-items: flex-start; flex-direction: column; }.dashboard-header__actions { width: 100%; }.dashboard-header__actions .el-button { flex: 1; }.dashboard h1 { font-size: 23px; }.summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }.summary-metric:nth-child(2) { border-right: 0; }.summary-metric:nth-child(3), .summary-balance { border-top: 1px solid var(--border-color-light); }.summary-balance { border-right: 0; }.dashboard-aside { grid-template-columns: 1fr; }.priority-row { align-items: flex-start; }.priority-row__meta { display: none; }.priority-row__arrow { margin-top: 8px; }.priority-row__copy small { white-space: normal; } }
/* The home screen is a starting point, so it stays spacious and scan-friendly. */
.dashboard { width: min(100%, 1120px); margin: 0 auto; padding: 46px 0 76px; }
.dashboard-header { padding-bottom: 32px; }
.dashboard h1 { max-width: 680px; font-size: clamp(28px, 3vw, 36px); letter-spacing: -.02em; }
.dashboard-header__copy { max-width: 650px; font-size: 15px; }
.summary-strip { margin-top: 30px; margin-bottom: 40px; background: color-mix(in srgb, var(--bg-secondary) 45%, transparent); }
.summary-metric, .summary-balance { min-height: 112px; padding: 22px; }
.summary-metric strong, .summary-balance strong { font-size: 32px; font-weight: 750; }
.dashboard-grid { gap: 44px; }
.dashboard-aside { padding-left: 38px; }
.priority-row { padding-block: 19px; }
.priority-row__status { width: 32px; height: 32px; }
.quick-link { padding-block: 15px; }
.empty-state { padding-block: 68px; }
@media (max-width: 920px) { .dashboard { padding-inline: 0; }.dashboard-aside { padding-left: 0; } }
</style>
