<template>
  <div class="void-page-container advisor-page">
    <div class="void-content">
      <header class="page-header">
        <h1 class="logo-text"><span class="void-text-gradient">任务顾问</span></h1>
        <p class="subtitle">通过系统引擎进行实时分析，生成结构化任务推进路径。</p>
      </header>

      <!-- Input Section -->
      <section class="selection-box void-card animate-float">
        <div class="input-group">
          <div class="input-icon">🧬</div>
          <el-input 
            v-model="userQuery" 
            placeholder="输入你的目标... (例如：精通 Rust 异步编程)"
            class="void-input"
            @keyup.enter="submitQuery"
            :disabled="isLoading"
            clearable
          />
          <el-button 
            type="primary" 
            @click="submitQuery"
            class="void-btn primary big"
            :loading="isLoading"
            :disabled="isLoading || !userQuery.trim()"
          >
            {{ isLoading ? '分析中' : '生成路径' }}
          </el-button>
        </div>
        <div class="input-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>建议：目标描述越具体，生成结果越可执行。默认 AI 自动判断任务规模，你也可以手动强制模式。</span>
        </div>
        <div class="mode-switcher">
          <span class="mode-switcher__label">生成模式：</span>
          <el-radio-group v-model="generationMode" size="small" :disabled="isLoading">
            <el-radio-button label="auto">自动判断</el-radio-button>
            <el-radio-button label="workflow_chain">强制任务链</el-radio-button>
            <el-radio-button label="single_task">强制单任务</el-radio-button>
          </el-radio-group>
        </div>
      </section>

      <!-- Quick Topics -->
      <section class="quick-topics" v-if="quickTopics.length > 0">
        <h3 class="section-label">预设领域</h3>
        <div class="topics-grid">
          <div 
            v-for="topic in quickTopics" 
            :key="topic.id"
            class="topic-chip void-card interactive"
            @click="useQuickTopic(topic.text)"
          >
            <span class="chip-icon">{{ topic.icon }}</span>
            <span class="chip-text">{{ topic.text }}</span>
          </div>
        </div>
      </section>

      <!-- Synthesis Progress Overlay -->
      <div v-if="isLoading" class="synthesis-overlay">
        <div class="synthesis-core">
          <div class="void-loading-ring void-loading-ring--xl" aria-hidden="true"></div>
          <h3 class="synthesis-title void-text-gradient">正在分析任务链路...</h3>
          <div class="void-progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <p class="synthesis-status">{{ loadingDescription }}{{ loadingDots }}</p>
          <el-button class="void-btn secondary" @click="cancelGeneration">取消生成</el-button>
        </div>
      </div>

      <!-- Result Section -->
      <section v-if="!isLoading && advisorResult" class="result-area animate-slide-up">
        <el-alert
          v-if="advisorResult?.meta?.auto_repaired"
          type="info"
          :closable="false"
          show-icon
          class="fallback-alert"
          title="检测到返回字段不完整，系统已自动修补缺失 key。"
        />

        <!-- Generated Manifest -->
        <div class="manifest-card void-card">
          <header class="manifest-header">
            <div class="manifest-info">
              <h2 class="manifest-title">任务路径: {{ advisorResult.query }}</h2>
              <div class="manifest-meta">
                <span class="tag"><el-icon><Calendar /></el-icon> {{ formattedDate }}</span>
                <span class="tag" v-if="estimatedDuration"><el-icon><Timer /></el-icon> 预计用时 {{ estimatedDuration }}</span>
              </div>
            </div>
            <el-button 
              type="primary" 
              class="void-btn primary big" 
              @click="publishTask" 
              :loading="isLoading" 
              :disabled="!isValidTaskStructure"
            >
              {{ publishButtonText }}
            </el-button>
          </header>

          <el-alert
            v-if="advisorResult?.meta?.fallback"
            type="warning"
            :closable="false"
            show-icon
            class="fallback-alert"
            title="当前为兜底草案，建议先检查步骤与奖励后再发布"
          />

          <div class="manifest-content">
            <div class="void-timeline">
              <div 
                v-for="(step, index) in learningSteps" 
                :key="index"
                class="timeline-item"
              >
                <div class="marker-lane">
                  <div class="marker-node">{{ index + 1 }}</div>
                  <div class="marker-line"></div>
                </div>
                <div class="content-lane">
                  <h4 class="step-title">{{ step.title }}</h4>
                  <p class="step-desc">{{ step.description }}</p>
                  <p class="step-meta">{{ formatStepMeta(step) }}</p>
                  <div v-if="getStepAttributePlan(step).length" class="step-attrplan">
                    <div class="step-attrplan__title">属性成长分配</div>
                    <ul class="step-attrplan__list">
                      <li v-for="row in getStepAttributePlan(step)" :key="`${step.title}-${row.attr_id}`" class="step-attrplan__item">
                        <span class="step-attrplan__name">{{ row.attr_name }}</span>
                        <span class="step-attrplan__points">+{{ row.points }} 点</span>
                      </li>
                    </ul>
                  </div>
                  <div v-if="getStepAttrDetails(step).length" class="step-attrdetail">
                    <div class="step-attrplan__title">属性关联依据</div>
                    <ul class="step-attrplan__list">
                      <li
                        v-for="row in getStepAttrDetails(step)"
                        :key="`${step.title}-${row.attr_id}-w`"
                        class="step-attrplan__item"
                      >
                        <span class="step-attrplan__name">{{ row.attr_name }}（{{ row.attr_id }}）</span>
                        <span class="step-attrplan__points">权重 {{ row.weight }}</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 原始数据 (存档) -->
        <div class="raw-data-card void-card">
          <h3 class="card-title"><el-icon><Memo /></el-icon> 原始结果数据</h3>
          <div class="data-terminal">
            <pre>{{ formattedFullResponse }}</pre>
          </div>
        </div>

        <div v-if="advisorDebugRows.length" class="raw-data-card void-card">
          <h3 class="card-title">生成调试信息</h3>
          <div class="debug-grid">
            <div v-for="row in advisorDebugRows" :key="row.label" class="debug-row">
              <span class="debug-label">{{ row.label }}</span>
              <span class="debug-value">{{ row.value }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 消息 -->
      <div v-if="errorMessage" class="void-card alert-box error animate-fade-in">
        <el-icon><Warning /></el-icon>
        <span>异常: {{ errorMessage }}</span>
      </div>
      <div v-if="successMessage" class="void-card alert-box success animate-fade-in">
        <el-icon><Check /></el-icon>
        <span>完成: {{ successMessage }}</span>
      </div>
    </div>

    <!-- History Sidebar -->
    <div class="history-sidebar" :class="{ open: showHistory }">
      <header class="sidebar-header">
        <h3 class="sidebar-title">历史存档</h3>
        <div class="sidebar-btns">
          <el-button circle class="void-btn ghost" icon="Delete" @click="clearHistory" title="清除所有存档" />
          <el-button circle class="void-btn ghost" icon="Close" @click="toggleHistory" title="关闭" />
        </div>
      </header>

      <div class="sidebar-content">
        <div v-if="historyList.length === 0" class="empty-state">
          <span class="icon">📋</span>
          <p>未找到存档记录。</p>
        </div>
        
        <div 
          v-for="item in historyList" 
          :key="item.id"
          class="history-card void-card interactive"
          @click="restoreFromHistory(item)"
        >
          <header class="card-header">
            <h4 class="item-query">{{ item.query }}</h4>
            <span class="item-date">{{ new Date(item.createdAt).toLocaleDateString() }}</span>
          </header>
          <div class="card-body">
            <p class="item-preview">{{ typeof item.response === 'string' ? item.response.substring(0, 60) : JSON.stringify(item.response).substring(0, 60) }}...</p>
            <div class="item-stats">
              <span class="count">{{ Array.isArray(item.steps) ? item.steps.length : 0 }} 节点</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Toggle Sidebar -->
    <button class="sidebar-toggle" @click="toggleHistory">
      <span class="icon">📋</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  InfoFilled,
  Warning,
  Check,
  Calendar,
  Timer,
  Memo,
  Delete,
  Close
} from '@element-plus/icons-vue'
import { getAdvisor } from '@/api/ai'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'
import api from '@/api/index'
import { getTaskCategories } from '@/api/taskCategories'

const safeParseHistory = () => {
  try {
    const raw = localStorage.getItem('advisor_history')
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    localStorage.removeItem('advisor_history')
    return []
  }
}


// ==================== Reactive State ====================
const userQuery = ref('')
const isLoading = ref(false)
const progressPercent = ref(0)
const advisorResult = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const loadingDescription = ref('正在合成任务本质')
const loadingDots = ref('')
const showHistory = ref(false)
const advisorAbortController = ref(null)
const generationMode = ref('auto')

// AI raw content and editing state
const aiRawResponse = ref('')

// Quick topics and categories
const quickTopics = ref([])
const isLoadingCategories = ref(false)

// History from localStorage
const historyList = ref(safeParseHistory())

// ==================== Animations ====================
const updateLoadingDots = () => {
  let dots = ''
  const interval = setInterval(() => {
    dots = dots.length < 3 ? dots + '.' : ''
    loadingDots.value = dots
  }, 500)
  return interval
}

// ==================== Watchers ====================

// ==================== Lifecycle ====================
onMounted(async () => {
  try {
    isLoadingCategories.value = true
    const categories = await getTaskCategories()
    
    if (Array.isArray(categories)) {
      quickTopics.value = categories.map((cat, idx) => ({
        id: cat.category_id || idx + 1,
        text: cat.category_name,
        icon: cat.icon || '🧬',
        isPreset: cat.is_preset
      }))
    } else {
      quickTopics.value = [
        { id: 1, text: '精通 Python 数据分析', icon: '🐍' },
        { id: 2, text: '英语能力提升路径', icon: '📚' },
        { id: 3, text: 'Vue 3 系统架构', icon: '💻' },
        { id: 4, text: '健身与健康管理网格', icon: '🏃‍♂️' }
      ]
    }
  } catch (error) {
    console.error('Failed to load categories:', error)
  } finally {
    isLoadingCategories.value = false
  }
})

// ==================== Computed ====================
const learningSteps = computed(() => {
  if (!advisorResult.value || !Array.isArray(advisorResult.value.steps)) return []
  return advisorResult.value.steps.filter((step) => (
    step &&
    typeof step === 'object' &&
    typeof step.title === 'string' &&
    typeof step.description === 'string' &&
    step.title.trim() &&
    step.description.trim()
  ))
})

const estimatedDuration = computed(() => {
  return advisorResult.value?.estimatedDuration || ''
})

const isValidTaskStructure = computed(() => {
  const result = advisorResult.value
  if (!result || !result.query || !Array.isArray(result.steps) || result.steps.length === 0) return false
  return result.steps.every((step) => (
    step &&
    typeof step === 'object' &&
    typeof step.title === 'string' &&
    typeof step.description === 'string' &&
    step.title.trim() &&
    step.description.trim()
  ))
})

const formattedDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', { 
    year: 'numeric', month: 'long', day: 'numeric' 
  })
})

const formattedFullResponse = computed(() => {
  if (!advisorResult.value) return '系统空闲。等待脉冲信号...'
  return JSON.stringify(advisorResult.value, null, 2)
})

const publishButtonText = computed(() => {
  if (advisorResult.value?.mode === 'single_task') return '发布单任务'
  if (advisorResult.value?.mode === 'workflow_chain') return '发布任务组'
  return '发布到任务系统'
})

const advisorDebugRows = computed(() => {
  const debug = advisorResult.value?.meta?.debug
  if (!debug || typeof debug !== 'object') return []
  const rows = []
  if (debug.mode) rows.push({ label: '生成模式', value: String(debug.mode) })
  if (debug.mode_reason) rows.push({ label: '模式原因', value: String(debug.mode_reason) })
  if (typeof debug.llm_call_count === 'number') rows.push({ label: 'LLM调用次数', value: String(debug.llm_call_count) })
  if (typeof debug.cache_hit_count === 'number') rows.push({ label: '缓存命中次数', value: String(debug.cache_hit_count) })
  if (typeof debug.batch_call_count === 'number') rows.push({ label: '批量调用次数', value: String(debug.batch_call_count) })
  if (typeof debug.max_review_rounds === 'number') rows.push({ label: '最大审查轮次', value: String(debug.max_review_rounds) })
  if (debug.stage_time_breakdown && typeof debug.stage_time_breakdown === 'object') {
    const t = debug.stage_time_breakdown
    rows.push({
      label: '阶段耗时',
      value: `S1 ${t.stage1_ms ?? 0}ms / S2 ${t.stage2_total_ms ?? 0}ms / S3 ${t.stage3_total_ms ?? 0}ms / Total ${t.total_ms ?? 0}ms`
    })
  }
  if (Array.isArray(debug.steps) && debug.steps.length) {
    const rounds = debug.steps.map((s) => `${(s?.idx ?? 0) + 1}:${s?.review_round ?? 0}`).join(' | ')
    rows.push({ label: '各步骤审查轮次', value: rounds })
  }
  return rows
})

// ==================== Actions ====================
const toNumberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

const formatStepMeta = (step) => {
  const minutes = toNumberOrNull(step?.estimated_time)
  const coins = toNumberOrNull(step?.reward_coins)
  const attrPoints = toNumberOrNull(step?.attribute_points)
  const parts = []
  parts.push(minutes == null ? '预计用时：未设置' : `预计用时：${minutes} 分钟`)
  parts.push(coins == null ? '系统币：未设置' : `系统币：+${coins}（VC）`)
  parts.push(attrPoints == null ? '属性成长：未设置' : `属性成长：+${attrPoints} 点`)
  return parts.join(' · ')
}

const getStepAttributePlan = (step) => {
  const criteria = step?.completion_criteria
  const plan = Array.isArray(step?.attribute_plan)
    ? step.attribute_plan
    : Array.isArray(criteria?.attribute_plan)
      ? criteria.attribute_plan
      : []
  return plan
    .map((row) => ({
      attr_id: row?.attr_id || row?.attrId || '',
      attr_name: row?.attr_name || row?.attrName || row?.attr_id || row?.attrId || '未命名属性',
      points: Number(row?.points ?? 0)
    }))
    .filter((row) => row.attr_id && row.points > 0)
}

const getStepAttrDetails = (step) => {
  const details = Array.isArray(step?.related_attrs_detail) ? step.related_attrs_detail : []
  return details
    .map((row) => ({
      attr_id: row?.attr_id || '',
      attr_name: row?.attr_name || row?.attr_id || '未命名属性',
      weight: Number(row?.weight ?? 0).toFixed(3)
    }))
    .filter((row) => row.attr_id && Number(row.weight) > 0)
}

const ensureStepSchema = (step, query, index) => {
  const normalizePriority = (raw) => {
    if (typeof raw === 'string') {
      const v = raw.trim().toLowerCase()
      if (['easy', 'medium', 'hard'].includes(v)) return v
      if (['1', 'low', '简单'].includes(v)) return 'easy'
      if (['2', 'normal', '中等'].includes(v)) return 'medium'
      if (['3', 'high', '困难'].includes(v)) return 'hard'
    }
    if (typeof raw === 'number') {
      if (raw <= 2) return 'easy'
      if (raw === 3) return 'medium'
      return 'hard'
    }
    return 'medium'
  }

  const normalizeRelatedAttrs = (raw) => {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
    const out = {}
    for (const [k, v] of Object.entries(raw)) {
      const attrId = String(k || '').trim()
      if (!attrId) continue
      const weight = Number(v)
      if (Number.isFinite(weight) && weight > 0) {
        out[attrId] = weight
      }
    }
    return out
  }

  const relatedAttrs = normalizeRelatedAttrs(step?.related_attrs)
  const title = (step?.title || '').trim() || `步骤${index + 1}：${query}`
  const description = (step?.description || '').trim() || `围绕“${query}”执行该步骤并记录可验证结果。`
  const estimatedTime = toNumberOrNull(step?.estimated_time)
  const rewardCoins = toNumberOrNull(step?.reward_coins)
  const attributePoints = toNumberOrNull(step?.attribute_points)
  const completionCriteria = step?.completion_criteria && typeof step.completion_criteria === 'object'
    ? step.completion_criteria
    : {}
  const deliverables = Array.isArray(completionCriteria.deliverables) && completionCriteria.deliverables.length
    ? completionCriteria.deliverables
    : ['执行记录', '结果证明']
  const checks = Array.isArray(completionCriteria.checks) && completionCriteria.checks.length
    ? completionCriteria.checks
    : ['内容与目标一致', '证据可核验']
  const evidence = Array.isArray(completionCriteria.evidence) && completionCriteria.evidence.length
    ? completionCriteria.evidence
    : ['截图', '文本说明']

  return {
    title,
    description,
    related_attrs: relatedAttrs,
    reward_coins: rewardCoins == null ? 20 : Math.max(0, rewardCoins),
    attribute_points: attributePoints == null ? 0 : Math.max(0, attributePoints),
    estimated_time: estimatedTime == null ? 30 : Math.max(1, estimatedTime),
    priority: normalizePriority(step?.priority),
    task_type: step?.task_type || 'main',
    completion_type: step?.completion_type || 'ai_eval',
    completion_criteria: {
      criteria: completionCriteria.criteria || `完成“${title}”并提交可验证成果。`,
      deliverables,
      checks,
      pass_threshold: completionCriteria.pass_threshold || '由评分AI综合判定',
      evidence,
      attribute_plan: Array.isArray(completionCriteria.attribute_plan)
        ? completionCriteria.attribute_plan
        : Array.isArray(step?.attribute_plan)
          ? step.attribute_plan
          : []
    },
    related_attrs_detail: Array.isArray(step?.related_attrs_detail) ? step.related_attrs_detail : []
  }
}

const normalizeResultAndRepairKeys = (parsed, query) => {
  const safe = normalizeAdvisorPayload(parsed, query)
  const repairedStepsRaw = Array.isArray(safe.steps) ? safe.steps : []
  const repairedSteps = repairedStepsRaw.map((step, index) => ensureStepSchema(step, safe.query || query, index))
  const noSteps = repairedSteps.length === 0
  const finalSteps = noSteps
    ? [ensureStepSchema({}, safe.query || query, 0)]
    : repairedSteps
  const hasMissingKeys = repairedStepsRaw.some((step) => (
    !step ||
    typeof step !== 'object' ||
    !step.title ||
    !step.description ||
    step.estimated_time == null ||
    step.reward_coins == null ||
    step.attribute_points == null ||
    !step.completion_criteria
  ))
  const repaired = noSteps || hasMissingKeys
  return {
    query: safe.query || query,
    response: safe.response || '路径合成成功。',
    steps: finalSteps,
    estimatedDuration: safe.estimatedDuration || `${finalSteps.reduce((s, x) => s + (x.estimated_time || 0), 0)} 分钟`,
    mode: safe.mode || (finalSteps.length === 1 ? 'single_task' : 'workflow_chain'),
    meta: {
      ...(safe.meta || {}),
      auto_repaired: repaired
    },
    createdAt: new Date()
  }
}

const normalizeAdvisorPayload = (result, query) => {
  const root = result?.data ? result.data : result
  const singleTask = root?.task || root?.single_task || root?.step
  const mode = root?.mode || (singleTask ? 'single_task' : 'workflow_chain')
  const steps = Array.isArray(root?.steps) ? root.steps : (singleTask ? [singleTask] : [])
  return {
    query: root?.query || query,
    response: root?.response || root?.message || '路径合成成功。',
    steps,
    estimatedDuration: root?.estimatedDuration || root?.estimated_duration || '',
    mode,
    meta: root?.meta || {}
  }
}

const saveToHistory = (result) => {
  const steps = Array.isArray(result?.steps) ? result.steps : []
  const historyItem = {
    id: Date.now(),
    query: result?.query || '',
    response: result?.response || '',
    createdAt: new Date().toISOString(),
    steps,
    mode: result?.mode || 'workflow_chain',
    meta: result?.meta || {}
  }
  
  historyList.value.unshift(historyItem)
  if (historyList.value.length > 20) historyList.value.pop()
  localStorage.setItem('advisor_history', JSON.stringify(historyList.value))
}

const parseAiResult = (result, query) => {
  aiRawResponse.value = typeof result === 'string' ? result : JSON.stringify(result, null, 2)
  
  try {
    const parsedRaw = typeof result === 'string' ? JSON.parse(result) : result
    const normalized = normalizeResultAndRepairKeys(parsedRaw, query)
    return normalized
  } catch (e) {
    return normalizeResultAndRepairKeys({}, query)
  }
}

const submitQuery = async () => {
  const query = userQuery.value.trim()
  if (!query) return ElMessage.warning('需要先定义目标')
  
  errorMessage.value = ''
  successMessage.value = ''
  isLoading.value = true
  progressPercent.value = 0
  advisorAbortController.value = new AbortController()
  
  let progressIdx = setInterval(() => {
    if (progressPercent.value < 90) progressPercent.value += Math.random() * 10
  }, 300)
  
  const dotsIdx = updateLoadingDots()
  
  try {
    const result = await getAdvisor(query, null, advisorAbortController.value.signal, { forceMode: generationMode.value })
    clearInterval(progressIdx)
    progressPercent.value = 100

    let parsed = parseAiResult(result, query)
    const shouldRetry = parsed?.meta?.auto_repaired && parsed?.steps?.length === 1
    if (shouldRetry) {
      try {
        const retryResult = await getAdvisor(query, null, advisorAbortController.value.signal, { forceMode: generationMode.value })
        const retried = parseAiResult(retryResult, query)
        if (!(retried?.meta?.auto_repaired && retried?.steps?.length === 1)) {
          parsed = retried
        }
      } catch {
        // 重试失败时保留首次自动修补结果
      }
    }

    advisorResult.value = parsed
    saveToHistory(advisorResult.value)
    ElMessage.success('合成已完成')
  } catch (error) {
    if (error?.name === 'CanceledError' || error?.name === 'AbortError' || /aborted|canceled/i.test(String(error?.message || ''))) {
      errorMessage.value = '已取消本次生成'
      ElMessage.warning(errorMessage.value)
    } else {
      errorMessage.value = formatAxiosErrorMessage(error, '神经链路故障')
      ElMessage.error(errorMessage.value)
    }
  } finally {
    setTimeout(() => {
      isLoading.value = false
      clearInterval(progressIdx)
      clearInterval(dotsIdx)
      loadingDots.value = ''
      advisorAbortController.value = null
    }, 500)
  }
}

const cancelGeneration = () => {
  advisorAbortController.value?.abort()
}

const publishTask = async () => {
  if (!isValidTaskStructure.value) return ElMessage.warning('结构不完整')
  
  isLoading.value = true
  try {
    const mode = advisorResult.value?.mode || 'workflow_chain'
    if (mode === 'single_task') {
      const step = advisorResult.value.steps[0]
      const payload = {
        task_name: step.title,
        description: step.description || '',
        priority: step.priority || 'medium',
        completion_type: step.completion_type || 'ai_eval',
        related_attrs: step.related_attrs || {},
        completion_criteria: step.completion_criteria || {}
      }
      const estimatedTime = toNumberOrNull(step.estimated_time)
      const rewardCoins = toNumberOrNull(step.reward_coins)
      const attributePoints = toNumberOrNull(step.attribute_points)
      if (estimatedTime != null && estimatedTime >= 1) payload.estimated_time = estimatedTime
      if (rewardCoins != null && rewardCoins >= 0) payload.reward_coins = rewardCoins
      if (attributePoints != null && attributePoints >= 0) payload.attribute_points = attributePoints
      await api.post('/api/tasks', payload)
      ElMessage.success('单任务已发布')
    } else {
      const steps = (advisorResult.value?.steps || []).map((step) => {
        const estimatedTime = toNumberOrNull(step?.estimated_time)
        const rewardCoins = toNumberOrNull(step?.reward_coins)
        const attributePoints = toNumberOrNull(step?.attribute_points)
        const relatedAttrs = step?.related_attrs && typeof step.related_attrs === 'object' ? step.related_attrs : {}
        const normalizedRelatedAttrs = Object.fromEntries(
          Object.entries(relatedAttrs).map(([k, v]) => [k, Number(v)]).filter(([, v]) => Number.isFinite(v) && v > 0)
        )
        return {
          title: step?.title || '未命名步骤',
          description: step?.description || '',
          related_attrs: normalizedRelatedAttrs,
          estimated_time: estimatedTime != null && estimatedTime >= 1 ? estimatedTime : 30,
          reward_coins: rewardCoins != null && rewardCoins >= 0 ? rewardCoins : 20,
          priority: ['easy', 'medium', 'hard'].includes(step?.priority) ? step.priority : 'medium',
          attribute_points: attributePoints != null && attributePoints >= 0 ? attributePoints : 0,
          completion_type: step?.completion_type || 'ai_eval',
          completion_criteria: step?.completion_criteria || {},
          task_type: ['main', 'side', 'daily'].includes(step?.task_type) ? step.task_type : 'main'
        }
      })
      const chainData = {
        chain_name: advisorResult.value.query.trim(),
        description: advisorResult.value.response || 'AI-generated evolution path',
        target_goal: advisorResult.value.query.trim(),
        steps
      }
      await api.post('/api/task-chains', chainData)
      ElMessage.success('任务组及子任务已发布')
    }
    advisorResult.value = null
    userQuery.value = ''
  } catch (error) {
    ElMessage.error('部署失败: ' + formatAxiosErrorMessage(error, error?.message || '未知错误'))
  } finally {
    isLoading.value = false
  }
}

const useQuickTopic = (topic) => {
  userQuery.value = topic
  submitQuery()
}

const restoreFromHistory = (item) => {
  const normalized = normalizeResultAndRepairKeys(item, item?.query || '历史任务')
  userQuery.value = normalized.query
  advisorResult.value = normalized
  showHistory.value = false
}

const clearHistory = async () => {
  try {
    await ElMessageBox.confirm('确认清除所有神经存档？', '警告', {
      confirmButtonText: '清除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    historyList.value = []
    localStorage.removeItem('advisor_history')
    ElMessage.success('Archives cleared')
  } catch (e) {}
}

const toggleHistory = () => (showHistory.value = !showHistory.value)
</script>

<style scoped>
.advisor-page {
  position: relative;
  min-height: 100vh;
}

.advisor-page::after {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 10% 10%, var(--color-primary-transparent) 0%, transparent 40%);
  pointer-events: none;
  z-index: 0;
}

.advisor-page .void-content {
  position: relative;
  z-index: 1;
}

.advisor-page .page-header .logo-text {
  font-size: 3rem;
  letter-spacing: -2px;
  margin-bottom: var(--spacing-xs);
}

/* Input Box */
.selection-box {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xxl);
}

.input-group {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.input-icon {
  font-size: 2rem;
  filter: drop-shadow(0 0 10px var(--color-primary));
}

.big {
  height: 52px;
  padding: 0 var(--spacing-xl);
}

.input-hint {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-muted);
  font-size: 0.9rem;
}

.mode-switcher {
  margin-top: var(--spacing-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.mode-switcher__label {
  font-size: 0.85rem;
  color: var(--text-muted);
}

/* Topics */
.quick-topics {
  margin-bottom: var(--spacing-xxl);
}

.section-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: var(--spacing-lg);
}

.topics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.topic-chip {
  padding: var(--spacing-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  transition: all var(--transition-normal);
}

.topic-chip:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  background: var(--bg-card-hover);
}

.chip-icon {
  font-size: 1.25rem;
}

.chip-text {
  font-weight: 600;
  color: var(--text-main);
}

/* Synthesis Overlay */
.synthesis-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-page-transparent);
  backdrop-filter: blur(20px);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.synthesis-core {
  text-align: center;
  width: 400px;
}

.synthesis-core .void-loading-ring--xl {
  margin: 0 auto var(--spacing-xl);
}

.synthesis-title {
  font-size: 1.5rem;
  margin-bottom: var(--spacing-lg);
}

.void-progress-bar {
  width: 100%;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: var(--spacing-md);
}

.progress-fill {
  height: 100%;
  background: var(--void-gradient);
  transition: width 0.3s ease;
}

.synthesis-status {
  color: var(--text-muted);
  font-family: var(--font-family-mono);
  font-size: 0.9rem;
}

/* Results */
.manifest-card {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.manifest-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-xxl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color-light);
}

.manifest-title {
  font-size: 1.75rem;
  margin: 0 0 var(--spacing-sm) 0;
}

.manifest-meta {
  display: flex;
  gap: var(--spacing-lg);
}

.tag {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Timeline */
.void-timeline {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: flex;
  gap: var(--spacing-xl);
}

.marker-lane {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.marker-node {
  width: 36px;
  height: 36px;
  background: var(--bg-page);
  border: 2px solid var(--color-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: var(--color-primary);
  z-index: 1;
}

.marker-line {
  flex: 1;
  width: 2px;
  background: linear-gradient(to bottom, var(--color-primary), var(--border-color-light));
  margin: var(--spacing-xs) 0;
}

.timeline-item:last-child .marker-line {
  display: none;
}

.content-lane {
  flex: 1;
  padding-bottom: var(--spacing-xxl);
}

.step-title {
  font-size: 1.25rem;
  color: var(--color-primary-light);
  margin: 0 0 var(--spacing-sm) 0;
}

.step-desc {
  color: var(--text-muted);
  line-height: 1.6;
}

.fallback-alert {
  margin-bottom: var(--spacing-lg);
}

.step-meta {
  margin: var(--spacing-sm) 0 0;
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.step-attrplan {
  margin-top: var(--spacing-sm);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
  background: var(--bg-secondary);
}

.step-attrdetail {
  margin-top: 8px;
  border: 1px dashed var(--border-color-light);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
  background: color-mix(in srgb, var(--bg-secondary) 80%, var(--bg-card));
}

.step-attrplan__title {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.step-attrplan__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.step-attrplan__item {
  display: flex;
  justify-content: space-between;
  font-size: 0.84rem;
  color: var(--text-main);
}

.step-attrplan__points {
  color: var(--color-primary);
  font-weight: 700;
}

/* Alert Boxes */
.alert-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.alert-box.warning { border-left: 4px solid var(--color-warning); }
.alert-box.error { border-left: 4px solid var(--color-error); }
.alert-box.success { border-left: 4px solid var(--color-success); }

.error-log {
  color: var(--color-error);
  font-size: 0.8rem;
  margin-top: var(--spacing-sm);
  font-family: var(--font-family-mono);
}

.hint-text {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-bottom: var(--spacing-md);
}

/* Raw Data */
.raw-data-card {
  padding: var(--spacing-lg);
}

.data-terminal {
  background: var(--bg-tertiary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  max-height: 250px;
  overflow-y: auto;
  font-family: var(--font-family-mono);
  font-size: 0.85rem;
}

.debug-grid {
  display: grid;
  gap: 8px;
}

.debug-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 0.85rem;
}

.debug-label {
  color: var(--text-muted);
}

.debug-value {
  color: var(--text-main);
  font-family: var(--font-family-mono);
}

/* History Sidebar */
.history-sidebar {
  position: fixed;
  top: 0;
  right: -400px;
  width: 400px;
  height: 100vh;
  background: var(--bg-card);
  backdrop-filter: blur(40px);
  border-left: 1px solid var(--border-color);
  z-index: 2000;
  transition: right var(--transition-normal) cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
}

.history-sidebar.open {
  right: 0;
}

.sidebar-header {
  padding: var(--spacing-xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color-light);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

.history-card {
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.item-query {
  font-size: 1rem;
  margin-bottom: var(--spacing-xs);
}

.item-date {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.item-preview {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: var(--spacing-md) 0;
}

.sidebar-toggle {
  position: fixed;
  right: var(--spacing-xl);
  bottom: var(--spacing-xl);
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--void-gradient);
  border: none;
  box-shadow: 0 0 20px var(--color-primary-transparent);
  z-index: 1500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: transform 0.3s ease;
}

.sidebar-toggle:hover {
  transform: scale(1.1) rotate(15deg);
}

@media (max-width: 768px) {
  .manifest-header {
    flex-direction: column;
    gap: var(--spacing-lg);
  }
}
</style>
