<template>
  <div class="companion-page" v-loading="loading.page">
    <header class="page-header">
      <div>
        <p class="page-kicker">个人上下文</p>
        <h1>系统精灵</h1>
        <p>帮你整理当前重点，也让你随时知道它记住了什么、为什么这样理解你。</p>
      </div>
      <div class="header-state" :class="{ 'header-state--paused': !settings.enabled }">
        <span class="state-dot" aria-hidden="true"></span>
        <span>{{ settings.enabled ? '陪伴已开启' : '陪伴已暂停' }}</span>
        <el-switch
          v-model="settings.enabled"
          aria-label="开启或暂停系统精灵"
          :loading="loading.settings"
          @change="saveSettings({ enabled: settings.enabled })"
        />
      </div>
    </header>

    <section class="briefing" aria-labelledby="briefing-title">
      <div class="briefing-copy">
        <span class="briefing-label">现在</span>
        <h2 id="briefing-title">{{ briefingHeadline }}</h2>
        <p>{{ briefingMessage }}</p>
      </div>
      <div class="briefing-actions" aria-label="建议操作">
        <button
          v-for="suggestion in suggestions"
          :key="suggestionKey(suggestion)"
          class="suggestion-button"
          type="button"
          @click="followSuggestion(suggestion)"
        >
          <span>
            <strong>{{ suggestionTitle(suggestion) }}</strong>
            <small>{{ suggestionReason(suggestion) }}</small>
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
    </section>

    <div class="workspace-grid">
      <main class="workspace-main">
        <section class="workspace-section" aria-labelledby="focus-title">
          <div class="section-heading">
            <div>
              <p class="section-kicker">行动线索</p>
              <h2 id="focus-title">正在推进</h2>
              <p>从目标和执行记录中提取，不会替你自动改变任务。</p>
            </div>
            <el-button text :icon="Refresh" :loading="loading.briefing" @click="refreshBriefing">刷新</el-button>
          </div>

          <div v-if="focusItems.length" class="focus-list">
            <button
              v-for="item in focusItems"
              :key="item.id"
              class="focus-row"
              type="button"
              @click="openReference(item.reference)"
            >
              <span class="focus-icon"><el-icon><Flag v-if="item.kind === 'goal'" /><VideoPlay v-else /></el-icon></span>
              <span class="focus-copy">
                <strong>{{ item.title }}</strong>
                <small>{{ localizeFocusSummary(item) }}</small>
              </span>
              <span class="focus-status">{{ focusStatus(item) }}</span>
              <el-icon class="row-arrow"><ArrowRight /></el-icon>
            </button>
          </div>
          <div v-else class="empty-inline">
            <span class="empty-icon"><el-icon><Compass /></el-icon></span>
            <div><strong>还没有正在推进的事项</strong><p>先创建一个清晰目标，系统精灵才有具体方向可以协助。</p></div>
            <el-button type="primary" @click="router.push('/tasks')">创建目标</el-button>
          </div>
        </section>

        <section class="workspace-section" aria-labelledby="profile-title">
          <div class="section-heading">
            <div>
              <p class="section-kicker">可解释画像</p>
              <h2 id="profile-title">系统怎样理解你</h2>
              <p>这些是有来源的候选判断。确认、修正或不采用后，原始判断仍会保留，方便追溯。</p>
            </div>
            <div class="section-counts" aria-label="画像审核统计">
              <span><strong>{{ profileStats.pending || 0 }}</strong> 待确认</span>
              <span><strong>{{ confirmedCount }}</strong> 已采纳</span>
            </div>
          </div>

          <div v-if="profileSuggestions.length" class="profile-suggestions" aria-live="polite">
            <article v-for="suggestion in profileSuggestions" :key="suggestion.suggestion_id" class="profile-suggestion">
              <div class="suggestion-main">
                <div class="claim-meta">
                  <span class="domain-label">来自你的行动记录</span>
                  <span class="review-label">等待你的决定</span>
                </div>
                <h3>{{ suggestion.summary }}</h3>
                <p>{{ suggestion.rationale }}</p>
                <small v-if="suggestion.first_observed_at || suggestion.last_observed_at">记录时间：{{ formatObservationRange(suggestion) }}</small>
              </div>
              <div class="claim-actions">
                <el-button type="success" plain :icon="Check" :loading="loading.review" @click="reviewSuggestion(suggestion, 'confirmed')">采用</el-button>
                <el-button :icon="EditPen" :loading="loading.review" @click="openSuggestionCorrection(suggestion)">调整</el-button>
                <el-button text :icon="Close" :loading="loading.review" @click="reviewSuggestion(suggestion, 'rejected')">停止使用这类模式</el-button>
              </div>
            </article>
          </div>

          <div class="profile-filter" role="tablist" aria-label="画像筛选">
            <button
              v-for="option in claimFilters"
              :key="option.value"
              type="button"
              :class="{ active: claimFilter === option.value }"
              @click="claimFilter = option.value"
            >{{ option.label }}</button>
          </div>

          <div v-if="filteredClaims.length" class="claim-list">
            <article v-for="claim in filteredClaims" :key="claim.claim_id" class="claim-row">
              <div class="claim-main">
                <div class="claim-meta">
                  <span class="domain-label">{{ domainLabel(claim.domain) }}</span>
                  <span class="review-label" :class="`review-label--${claim.review_status}`">{{ reviewLabel(claim.review_status) }}</span>
                  <span v-if="claim.context_eligible" class="context-label">可用于协助</span>
                </div>
                <h3>{{ claim.summary || claim.profile_key }}</h3>
                <p class="claim-value">{{ formatValue(claim.value) }}</p>
                <p v-if="claim.rationale" class="claim-rationale">{{ claim.rationale }}</p>
                <details v-if="claim.evidence_refs?.length" class="claim-evidence">
                  <summary>查看依据 · {{ claim.evidence_refs.length }} 条</summary>
                  <div v-for="(evidence, index) in claim.evidence_refs" :key="index">
                    <span>{{ evidenceLabel(evidence.type) }}</span>
                    <code>{{ evidence.id || evidence.source_ref || '已记录证据' }}</code>
                  </div>
                </details>
              </div>
              <div class="claim-actions">
                <template v-if="claim.review_status === 'pending'">
                  <el-button type="success" plain :icon="Check" @click="reviewClaim(claim, 'confirmed')">准确</el-button>
                  <el-button :icon="EditPen" @click="openCorrection(claim)">修正</el-button>
                  <el-button text :icon="Close" @click="reviewClaim(claim, 'rejected')">不采用</el-button>
                </template>
                <template v-else>
                  <el-button v-if="claim.review_status !== 'corrected'" :icon="EditPen" @click="openCorrection(claim)">修正</el-button>
                  <el-button text :icon="RefreshLeft" @click="reviewClaim(claim, 'pending')">重新审核</el-button>
                </template>
              </div>
            </article>
          </div>
          <div v-else class="empty-inline empty-inline--quiet">
            <span class="empty-icon"><el-icon><User /></el-icon></span>
            <div><strong>{{ claimFilter === 'all' ? '还没有形成画像判断' : '这个分类目前为空' }}</strong><p>系统会把明确记忆和后续证据整理成可审核的候选判断。</p></div>
          </div>
        </section>

        <section class="workspace-section" aria-labelledby="memory-title">
          <div class="section-heading">
            <div>
              <p class="section-kicker">长期记忆</p>
              <h2 id="memory-title">值得保留的信息</h2>
              <p>事实、偏好、经历和推断分开保存。你可以暂停使用、归档或彻底忘记。</p>
            </div>
            <el-button type="primary" :icon="Plus" @click="openMemoryEditor()">添加记忆</el-button>
          </div>

          <div class="memory-toolbar">
            <div class="profile-filter" role="tablist" aria-label="记忆筛选">
              <button type="button" :class="{ active: memoryFilter === 'active' }" @click="memoryFilter = 'active'">使用中</button>
              <button type="button" :class="{ active: memoryFilter === 'archived' }" @click="memoryFilter = 'archived'">已归档</button>
            </div>
            <span>{{ visibleMemories.length }} 条</span>
          </div>

          <div v-if="visibleMemories.length" class="memory-list">
            <article v-for="memory in visibleMemories" :key="memory.memory_id" class="memory-row">
              <span class="memory-type">{{ memoryTypeLabel(memory.memory_type) }}</span>
              <div class="memory-copy">
                <strong>{{ memory.title }}</strong>
                <p>{{ memory.content }}</p>
                <small>{{ memorySourceLabel(memory) }} · 更新于 {{ formatDate(memory.updated_at) }}</small>
              </div>
              <div class="memory-use">
                <el-switch
                  v-if="memory.status === 'active'"
                  :model-value="memory.use_in_context"
                  :aria-label="`是否在协助中使用记忆：${memory.title}`"
                  @change="toggleMemoryContext(memory, $event)"
                />
                <span v-if="memory.status === 'active'">{{ memory.use_in_context ? '参与协助' : '暂不使用' }}</span>
              </div>
              <el-dropdown trigger="click" @command="handleMemoryCommand($event, memory)">
                <el-button text circle aria-label="记忆操作"><el-icon><MoreFilled /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit"><el-icon><EditPen /></el-icon>编辑</el-dropdown-item>
                    <el-dropdown-item v-if="memory.status === 'active'" command="archive"><el-icon><Folder /></el-icon>归档</el-dropdown-item>
                    <el-dropdown-item v-else command="restore"><el-icon><RefreshLeft /></el-icon>恢复</el-dropdown-item>
                    <el-dropdown-item divided command="delete"><el-icon><Delete /></el-icon>彻底忘记</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </article>
          </div>
          <div v-else class="empty-inline empty-inline--quiet">
            <span class="empty-icon"><el-icon><Memo /></el-icon></span>
            <div><strong>{{ memoryFilter === 'active' ? '还没有长期记忆' : '没有已归档记忆' }}</strong><p>{{ memoryFilter === 'active' ? '只保存未来确实会有帮助的信息，不需要事无巨细。' : '归档后的记忆不会参与上下文。' }}</p></div>
          </div>
        </section>
      </main>

      <aside class="context-sidebar" aria-label="系统精灵控制与透明度">
        <section class="sidebar-section">
          <div class="sidebar-heading">
            <div><p class="section-kicker">互动方式</p><h2>怎么陪你</h2></div>
          </div>
          <label class="control-field">
            <span>表达方式</span>
            <el-segmented v-model="settings.tone" :options="toneOptions" :disabled="loading.settings" @change="saveSettings({ tone: settings.tone })" />
          </label>
          <label class="control-field">
            <span>主动程度</span>
            <el-segmented v-model="settings.initiative" :options="initiativeOptions" :disabled="loading.settings" @change="saveSettings({ initiative: settings.initiative })" />
          </label>
        </section>

        <section class="sidebar-section">
          <div class="sidebar-heading">
            <div><p class="section-kicker">数据权限</p><h2>可以参考什么</h2></div>
            <el-tooltip content="权限只控制系统精灵组装上下文，不会删除原始数据。" placement="top">
              <el-icon class="help-icon"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          <div class="permission-list">
            <label v-for="permission in permissionOptions" :key="permission.key" class="permission-row">
              <span><strong>{{ permission.label }}</strong><small>{{ permission.description }}</small></span>
              <el-switch
                v-model="settings.permissions[permission.key]"
                :disabled="loading.settings || !settings.enabled"
                :aria-label="`允许系统精灵参考${permission.label}`"
                @change="savePermissions"
              />
            </label>
          </div>
        </section>

        <section class="sidebar-section">
          <div class="sidebar-heading">
            <div><p class="section-kicker">本次简报</p><h2>实际使用了什么</h2></div>
            <span class="audit-id" :title="briefing.context?.audit_id || ''">{{ briefing.context?.item_count || 0 }} 项</span>
          </div>
          <p v-if="!settings.enabled" class="context-note"><el-icon><Lock /></el-icon>陪伴已暂停，本次没有读取个人上下文。</p>
          <div v-else-if="contextSources.length" class="source-list">
            <div v-for="source in contextSources" :key="source.section" class="source-row" :class="{ 'source-row--muted': source.decision !== 'included' }">
              <span><strong>{{ permissionLabel(source.section) }}</strong><small>{{ sourceDecisionLabel(source) }}</small></span>
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
          <p v-else class="context-note">当前没有可用于简报的数据。</p>
          <details class="access-details" @toggle="loadAccessWhenOpened">
            <summary><span><el-icon><View /></el-icon>最近访问记录</span><el-icon><ArrowRight /></el-icon></summary>
            <div v-if="accessRecords.length" class="access-list">
              <div v-for="record in accessRecords" :key="record.audit_id" class="access-row">
                <span>{{ purposeLabel(record.purpose) }}</span>
                <small>{{ formatDateTime(record.created_at) }} · {{ accessSummary(record) }}</small>
              </div>
            </div>
            <p v-else class="access-empty">还没有访问记录。</p>
          </details>
        </section>
      </aside>
    </div>

    <el-dialog v-model="correctionDialog.open" title="修正这条理解" width="min(92vw, 520px)" class="void-dialog" destroy-on-close>
      <div class="dialog-form">
        <div class="original-value"><span>系统原判断</span><p>{{ formatValue(correctionDialog.claim?.value) }}</p></div>
        <label><span>你认为更准确的说法</span><el-input v-model="correctionDialog.value" type="textarea" :rows="3" maxlength="500" show-word-limit /></label>
        <label><span>补充说明 <small>可选</small></span><el-input v-model="correctionDialog.reason" maxlength="500" placeholder="例如：只在某些场景下是这样" /></label>
      </div>
      <template #footer>
        <el-button @click="correctionDialog.open = false">取消</el-button>
        <el-button type="primary" :loading="loading.review" @click="submitCorrection">保存修正</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="memoryDialog.open" :title="memoryDialog.memoryId ? '编辑记忆' : '添加一条记忆'" width="min(92vw, 560px)" class="void-dialog" destroy-on-close>
      <div class="dialog-form">
        <label><span>记忆类型</span><el-select v-model="memoryDialog.form.memory_type"><el-option v-for="option in memoryTypeOptions" :key="option.value" :label="option.label" :value="option.value" /></el-select></label>
        <label><span>标题</span><el-input v-model="memoryDialog.form.title" maxlength="160" placeholder="一句话说明要记住什么" /></label>
        <label><span>具体内容</span><el-input v-model="memoryDialog.form.content" type="textarea" :rows="4" maxlength="4000" show-word-limit placeholder="写下未来协助时真正有用的信息" /></label>
        <label class="switch-field"><span><strong>参与后续协助</strong><small>关闭后仍会保留，但不会放进本次协助参考。</small></span><el-switch v-model="memoryDialog.form.use_in_context" /></label>
        <label class="switch-field"><span><strong>帮助系统理解我</strong><small>开启后，这条记忆会成为一项可查看、可撤回的画像信息。</small></span><el-switch v-model="memoryDialog.form.contribute_to_profile" /></label>
      </div>
      <template #footer>
        <el-button @click="memoryDialog.open = false">取消</el-button>
        <el-button type="primary" :loading="loading.memory" @click="saveMemory">{{ memoryDialog.memoryId ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowRight,
  Check,
  CircleCheck,
  Close,
  Compass,
  Delete,
  EditPen,
  Flag,
  Folder,
  InfoFilled,
  Lock,
  Memo,
  MoreFilled,
  Plus,
  Refresh,
  RefreshLeft,
  User,
  VideoPlay,
  View
} from '@element-plus/icons-vue'
import companionApi from '@/api/companion'
import { getApiErrorMessage } from '@/api'

const router = useRouter()
const loading = reactive({ page: true, settings: false, briefing: false, review: false, memory: false, access: false })
const settings = reactive({ enabled: true, tone: 'calm', initiative: 'balanced', permissions: {} })
const briefing = ref({})
const profile = ref({ raw_claims: [], effective_claims: [], groups: {}, stats: {} })
const profileSuggestions = ref([])
const memories = ref([])
const accessRecords = ref([])
const claimFilter = ref('pending')
const memoryFilter = ref('active')

const claimFilters = [
  { label: '待确认', value: 'pending' },
  { label: '已采纳', value: 'accepted' },
  { label: '不采用', value: 'rejected' },
  { label: '全部', value: 'all' }
]
const toneOptions = [{ label: '冷静', value: 'calm' }, { label: '温和', value: 'warm' }, { label: '直接', value: 'direct' }]
const initiativeOptions = [{ label: '安静', value: 'quiet' }, { label: '适度', value: 'balanced' }, { label: '主动', value: 'proactive' }]
const permissionOptions = [
  { key: 'profile', label: '帮助系统理解我', description: '只基于你允许使用的数据，所有理解都可查看、修正或关闭' },
  { key: 'goals', label: '目标', description: '你希望达成的结果' },
  { key: 'runs', label: '执行进度', description: '正在进行的计划和步骤' },
  { key: 'growth', label: '成长记录', description: '能力与长期变化' },
  { key: 'memories', label: '长期记忆', description: '你明确保留的信息' },
  { key: 'knowledge', label: '个人资料库', description: '上传和收藏的资料' },
  { key: 'rewards', label: '奖励与资源', description: '余额和已获得资源' }
]
const memoryTypeOptions = [
  { label: '稳定事实', value: 'fact' },
  { label: '个人偏好', value: 'preference' },
  { label: '经历片段', value: 'episode' },
  { label: '系统推断', value: 'inference' }
]
const domainLabels = { basic: '基本事实', interests: '兴趣与回避', working_style: '工作与学习', communication: '沟通偏好', values: '价值与驱力', current_phase: '当前阶段' }
const reviewLabels = { pending: '待确认', confirmed: '已确认', corrected: '已修正', rejected: '不采用' }
const memoryLabels = { fact: '事实', preference: '偏好', episode: '经历', inference: '推断' }
const permissionLabels = Object.fromEntries(permissionOptions.map((item) => [item.key, item.label]))

const correctionDialog = reactive({ open: false, claim: null, value: '', reason: '' })
const emptyMemory = () => ({ memory_type: 'fact', title: '', content: '', use_in_context: true, contribute_to_profile: false })
const memoryDialog = reactive({ open: false, memoryId: null, form: emptyMemory() })

const profileStats = computed(() => profile.value?.stats || {})
const confirmedCount = computed(() => (profileStats.value.confirmed || 0) + (profileStats.value.corrected || 0))
const effectiveById = computed(() => new Map((profile.value?.effective_claims || []).map((item) => [item.claim_id, item])))
const displayClaims = computed(() => (profile.value?.raw_claims || []).map((raw) => ({ ...raw, ...(effectiveById.value.get(raw.claim_id) || {}) })))
const filteredClaims = computed(() => displayClaims.value.filter((claim) => {
  if (claimFilter.value === 'all') return true
  if (claimFilter.value === 'accepted') return ['confirmed', 'corrected'].includes(claim.review_status)
  return claim.review_status === claimFilter.value
}))
const visibleMemories = computed(() => memories.value.filter((memory) => memory.status === memoryFilter.value))
const focusItems = computed(() => briefing.value?.focus_items || [])
const suggestions = computed(() => briefing.value?.suggestions || [])
const contextSources = computed(() => briefing.value?.context?.sources || [])
const briefingHeadline = computed(() => {
  if (!settings.enabled) return '系统精灵已暂停'
  if (focusItems.value.some((item) => item.kind === 'run')) return '先把正在进行的事情接上'
  if (focusItems.value.some((item) => item.kind === 'goal')) return '把一个目标变成可执行计划'
  return '选一件真正值得推进的事'
})
const briefingMessage = computed(() => {
  if (!settings.enabled) return '个人上下文不会被读取；已有记忆和画像仍由你保管。'
  if (focusItems.value.some((item) => item.kind === 'run')) return '系统找到了尚未结束的执行记录，可以从最近一步继续，不必重新整理。'
  if (focusItems.value.some((item) => item.kind === 'goal')) return '方向已经存在，下一步是把目标拆成能检查结果的行动。'
  return '从一个一周内能看到证据的小目标开始，后续规划和复盘会更清楚。'
})

function normalizeSettings(value = {}) {
  settings.enabled = value.enabled ?? true
  settings.tone = value.tone || 'calm'
  settings.initiative = value.initiative || 'balanced'
  settings.permissions = Object.fromEntries(permissionOptions.map((item) => [item.key, value.permissions?.[item.key] ?? false]))
}

async function loadPage() {
  loading.page = true
  try {
    const [settingsResult, profileResult, suggestionsResult, memoryResult] = await Promise.allSettled([
      companionApi.getSettings(), companionApi.getProfile(), companionApi.listProfileSuggestions(), companionApi.listMemories({ limit: 200 })
    ])
    if (settingsResult.status === 'fulfilled') normalizeSettings(settingsResult.value)
    else throw settingsResult.reason
    if (profileResult.status === 'fulfilled') profile.value = profileResult.value
    if (suggestionsResult.status === 'fulfilled') profileSuggestions.value = suggestionsResult.value
    if (memoryResult.status === 'fulfilled') memories.value = memoryResult.value
    await refreshBriefing(false)
    await loadAccessLog(false)
    const partialFailures = [profileResult, suggestionsResult, memoryResult].filter((item) => item.status === 'rejected').length
    if (partialFailures) ElMessage.warning('部分个人数据暂时没有加载，已保留可用内容')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '系统精灵暂时无法加载'))
  } finally {
    loading.page = false
  }
}

async function refreshBriefing(showMessage = true) {
  loading.briefing = true
  try {
    briefing.value = await companionApi.getBriefing()
    if (showMessage) ElMessage.success('简报已更新')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '简报暂时无法更新'))
  } finally {
    loading.briefing = false
  }
}

async function saveSettings(updates) {
  loading.settings = true
  try {
    normalizeSettings(await companionApi.updateSettings(updates))
    await refreshBriefing(false)
    await loadAccessLog(false)
    ElMessage.success('陪伴设置已更新')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '设置没有保存成功'))
    normalizeSettings(await companionApi.getSettings())
  } finally {
    loading.settings = false
  }
}

function savePermissions() {
  return saveSettings({ permissions: { ...settings.permissions } })
}

async function refreshProfileUnderstanding() {
  const [profileValue, suggestionsValue] = await Promise.all([
    companionApi.getProfile(),
    companionApi.listProfileSuggestions()
  ])
  profile.value = profileValue
  profileSuggestions.value = suggestionsValue
}

async function reviewSuggestion(suggestion, decision, value = null, reason = '') {
  loading.review = true
  try {
    await companionApi.reviewProfileSuggestion(suggestion.suggestion_id, decision, value, reason)
    await refreshProfileUnderstanding()
    const messages = { confirmed: '已采用这项理解', rejected: '系统将停止使用这类模式' }
    ElMessage.success(messages[decision] || '理解方式已更新')
    await refreshBriefing(false)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '这项理解没有保存成功'))
  } finally {
    loading.review = false
  }
}

function openSuggestionCorrection(suggestion) {
  correctionDialog.claim = { ...suggestion, suggestion_id: suggestion.suggestion_id, isSuggestion: true }
  correctionDialog.value = formatValue(suggestion.value?.label || suggestion.summary)
  correctionDialog.reason = ''
  correctionDialog.open = true
}

async function reviewClaim(claim, decision) {
  loading.review = true
  try {
    await companionApi.reviewClaim(claim.claim_id, decision)
    await refreshProfileUnderstanding()
    const messages = { confirmed: '已确认这条理解', rejected: '这条理解将不再被采用', pending: '已恢复为待审核' }
    ElMessage.success(messages[decision] || '画像已更新')
    await refreshBriefing(false)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '画像审核没有保存成功'))
  } finally {
    loading.review = false
  }
}

function openCorrection(claim) {
  correctionDialog.claim = claim
  correctionDialog.value = formatValue(claim.value)
  correctionDialog.reason = ''
  correctionDialog.open = true
}

async function submitCorrection() {
  if (!correctionDialog.value.trim()) return ElMessage.warning('请填写更准确的说法')
  loading.review = true
  try {
    if (correctionDialog.claim.isSuggestion) {
      await companionApi.reviewProfileSuggestion(correctionDialog.claim.suggestion_id, 'corrected', correctionDialog.value.trim(), correctionDialog.reason.trim())
      await refreshProfileUnderstanding()
    } else {
      await companionApi.reviewClaim(correctionDialog.claim.claim_id, 'corrected', correctionDialog.value.trim(), correctionDialog.reason.trim())
      await refreshProfileUnderstanding()
    }
    correctionDialog.open = false
    ElMessage.success('已保存你的修正')
    await refreshBriefing(false)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '修正没有保存成功'))
  } finally {
    loading.review = false
  }
}

function openMemoryEditor(memory = null) {
  memoryDialog.memoryId = memory?.memory_id || null
  memoryDialog.form = memory ? {
    memory_type: memory.memory_type,
    title: memory.title,
    content: memory.content,
    use_in_context: memory.use_in_context,
    contribute_to_profile: memory.metadata?.contribute_to_profile === true
  } : emptyMemory()
  memoryDialog.open = true
}

async function saveMemory() {
  const form = memoryDialog.form
  if (!form.title.trim() || !form.content.trim()) return ElMessage.warning('请填写标题和具体内容')
  loading.memory = true
  try {
    const payload = { ...form, title: form.title.trim(), content: form.content.trim() }
    if (memoryDialog.memoryId) {
      await companionApi.updateMemory(memoryDialog.memoryId, payload)
      ElMessage.success('记忆已更新')
    } else {
      await companionApi.createMemory({ ...payload, source_type: 'manual', confidence: 1 })
      ElMessage.success('已添加长期记忆')
    }
    memoryDialog.open = false
    memories.value = await companionApi.listMemories({ limit: 200 })
    profile.value = await companionApi.getProfile()
    await refreshBriefing(false)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '记忆没有保存成功'))
  } finally {
    loading.memory = false
  }
}

async function toggleMemoryContext(memory, enabled) {
  try {
    const updated = await companionApi.updateMemory(memory.memory_id, { use_in_context: enabled })
    Object.assign(memory, updated)
    profile.value = await companionApi.getProfile()
    await refreshBriefing(false)
    ElMessage.success(enabled ? '这条记忆会参与后续协助' : '这条记忆已暂停使用')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '记忆状态没有更新成功'))
  }
}

async function handleMemoryCommand(command, memory) {
  if (command === 'edit') return openMemoryEditor(memory)
  if (command === 'archive' || command === 'restore') {
    try {
      await companionApi.updateMemory(memory.memory_id, { status: command === 'archive' ? 'archived' : 'active', use_in_context: command === 'restore' ? memory.use_in_context : false })
      memories.value = await companionApi.listMemories({ limit: 200 })
      profile.value = await companionApi.getProfile()
      await refreshBriefing(false)
      ElMessage.success(command === 'archive' ? '记忆已归档' : '记忆已恢复')
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '记忆状态没有更新成功'))
    }
    return
  }
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm('彻底忘记后无法恢复。相关画像依据也会停止使用。', '彻底忘记这条记忆？', { confirmButtonText: '彻底忘记', cancelButtonText: '取消', type: 'warning' })
      await companionApi.deleteMemory(memory.memory_id)
      memories.value = await companionApi.listMemories({ limit: 200 })
      profile.value = await companionApi.getProfile()
      await refreshBriefing(false)
      ElMessage.success('这条记忆已被忘记')
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error, '记忆没有删除成功'))
    }
  }
}

async function loadAccessLog(showError = true) {
  loading.access = true
  try { accessRecords.value = await companionApi.listAccessLog(20) }
  catch (error) { if (showError) ElMessage.error(getApiErrorMessage(error, '访问记录暂时无法加载')) }
  finally { loading.access = false }
}

function loadAccessWhenOpened(event) {
  if (event.target.open) loadAccessLog()
}

function openReference(reference) {
  if (!reference) return
  if (reference.type === 'goal' || reference.type === 'run') router.push('/tasks')
}

function followSuggestion(suggestion) {
  if (suggestion.kind === 'create_goal' || suggestion.kind === 'plan_goal') return router.push('/tasks')
  if (suggestion.kind === 'continue_run' || suggestion.kind === 'start_run') return router.push('/tasks')
  router.push('/tasks')
}

function suggestionKey(suggestion) { return `${suggestion.kind}:${suggestion.reference?.id || 'new'}` }
function suggestionTitle(suggestion) {
  const labels = { create_goal: '创建一个聚焦目标', plan_goal: '为这个目标制定计划', continue_run: '继续当前执行', start_run: '开始已准备的计划' }
  return labels[suggestion.kind] || suggestion.title || '查看下一步'
}
function suggestionReason(suggestion) {
  const labels = { create_goal: '先明确一个可观察结果', plan_goal: '它还没有执行计划', continue_run: '已有进度，无需重新开始', start_run: '步骤已经准备好' }
  return labels[suggestion.kind] || suggestion.reason || '进入行动工作区'
}
function localizeFocusSummary(item) {
  if (item.kind === 'run') return `已完成 ${item.data?.completed_steps || 0} / ${item.data?.step_count || 0} 个步骤`
  if (item.kind === 'goal') return item.data?.run_count ? `已有 ${item.data.run_count} 次执行` : '还没有执行计划'
  return item.summary || ''
}
function focusStatus(item) {
  const status = item.data?.status
  return ({ running: '进行中', queued: '待开始', paused: '已暂停', active: '目标' })[status] || (item.kind === 'goal' ? '目标' : '待处理')
}
function domainLabel(value) { return domainLabels[value] || value || '画像' }
function reviewLabel(value) { return reviewLabels[value] || value || '待确认' }
function memoryTypeLabel(value) { return memoryLabels[value] || value || '记忆' }
function permissionLabel(value) { return permissionLabels[value] || value }
function evidenceLabel(value) { return ({ memory: '长期记忆', observation: '行为证据', task: '任务记录', conversation: '对话确认' })[value] || '证据' }
function purposeLabel(value) { return ({ companion_briefing: '生成系统精灵简报', companion_context: '组装个人上下文' })[value] || '读取个人上下文' }
function sourceDecisionLabel(source) {
  if (source.decision === 'excluded') return '未使用：你没有允许此类信息参与协助'
  if (source.decision === 'empty') return '暂未使用：当前没有可用内容'
  if (source.truncated) return '已使用 ' + source.included + ' 项；其余内容留在本次范围之外'
  return '已使用 ' + source.included + ' 项' + (source.available ? '' : '（当前无额外内容）')
}
function accessSummary(record) {
  const omitted = record.omitted_sections || []
  const permissionCount = omitted.filter((item) => item.reason === 'permission').length
  const budgetCount = omitted.filter((item) => item.reason === 'budget').length
  const detail = [
    permissionCount ? permissionCount + ' 类未授权' : '',
    budgetCount ? budgetCount + ' 类未纳入本次范围' : ''
  ].filter(Boolean)
  return String(record.item_count || 0) + ' 项' + (detail.length ? '，' + detail.join('，') : '')
}
function memorySourceLabel(memory) { return memory.source_type === 'manual' ? '由你添加' : memory.source_type === 'run_evaluation' ? '来自执行复盘' : '来自系统记录' }
function formatValue(value) {
  if (value == null) return '未填写'
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}：${item}`).join('；')
  return String(value)
}
function formatObservationRange(item) {
  const start = formatDate(item.first_observed_at)
  const end = formatDate(item.last_observed_at)
  return start === end ? start : start + ' 至 ' + end
}
function formatDate(value) { return value ? new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(new Date(value)) : '未知时间' }
function formatDateTime(value) { return value ? new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '未知时间' }

onMounted(loadPage)
</script>

<style scoped>
.companion-page { width: min(100%, 1240px); margin: 0 auto; padding: 30px 0 72px; color: var(--text-primary); }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 28px; padding: 0 2px 26px; border-bottom: 1px solid var(--border-color); }
.page-kicker, .section-kicker { margin: 0 0 6px; color: var(--color-primary); font-size: 12px; font-weight: 800; }
.page-header h1 { margin: 0; font-size: 30px; line-height: 1.15; }
.page-header p:not(.page-kicker) { max-width: 700px; margin: 9px 0 0; color: var(--text-secondary); line-height: 1.65; }
.header-state { display: flex; align-items: center; flex: 0 0 auto; gap: 9px; min-height: 42px; padding: 0 12px; border: 1px solid color-mix(in srgb, var(--color-success) 28%, var(--border-color)); border-radius: 7px; color: var(--color-success); background: color-mix(in srgb, var(--color-success) 6%, var(--bg-secondary)); font-size: 13px; font-weight: 700; }
.header-state--paused { border-color: var(--border-color); color: var(--text-muted); background: var(--bg-secondary); }
.state-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.briefing { display: grid; grid-template-columns: minmax(0, 1fr) minmax(360px, .85fr); gap: 44px; padding: 30px 2px; border-bottom: 1px solid var(--border-color); }
.briefing-copy { align-self: center; }
.briefing-label { display: inline-flex; margin-bottom: 10px; padding: 4px 7px; border-radius: 4px; color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 10%, var(--bg-secondary)); font-size: 11px; font-weight: 800; }
.briefing h2 { max-width: 660px; margin: 0; font-size: 25px; line-height: 1.3; }
.briefing p { max-width: 680px; margin: 10px 0 0; color: var(--text-secondary); line-height: 1.65; }
.briefing-actions { display: grid; align-content: center; gap: 7px; }
.suggestion-button { display: flex; align-items: center; width: 100%; min-height: 58px; gap: 14px; padding: 9px 12px; border: 1px solid var(--border-color-light); border-radius: 7px; color: var(--text-primary); background: var(--bg-secondary); cursor: pointer; text-align: left; transition: border-color .16s ease, background .16s ease, transform .16s ease; }
.suggestion-button:hover { border-color: color-mix(in srgb, var(--color-primary) 30%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 4%, var(--bg-secondary)); transform: translateY(-1px); }
.suggestion-button > span { display: grid; flex: 1; min-width: 0; gap: 2px; }
.suggestion-button strong { font-size: 14px; }
.suggestion-button small { color: var(--text-muted); font-size: 12px; }
.suggestion-button .el-icon, .row-arrow { color: var(--text-muted); }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1fr) 318px; gap: 42px; align-items: start; }
.workspace-main { min-width: 0; }
.workspace-section { padding: 34px 2px 38px; border-bottom: 1px solid var(--border-color); }
.section-heading, .sidebar-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 22px; }
.section-heading h2, .sidebar-heading h2 { margin: 0; font-size: 19px; line-height: 1.3; }
.section-heading > div:first-child > p:not(.section-kicker) { max-width: 680px; margin: 7px 0 0; color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
.section-counts { display: flex; flex: 0 0 auto; gap: 15px; color: var(--text-muted); font-size: 12px; }
.section-counts strong { color: var(--text-primary); font-size: 15px; }
.focus-list, .claim-list, .memory-list { margin-top: 22px; }
.focus-row { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto 18px; align-items: center; width: 100%; min-height: 62px; gap: 12px; padding: 9px 4px; border: 0; border-bottom: 1px solid var(--border-color-light); color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.focus-row:hover { background: color-mix(in srgb, var(--color-primary) 4%, transparent); }
.focus-icon, .empty-icon { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 6px; color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 10%, var(--bg-secondary)); }
.focus-copy { display: grid; min-width: 0; gap: 3px; }
.focus-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
.focus-copy small { color: var(--text-muted); font-size: 12px; }
.focus-status { padding: 4px 7px; border-radius: 4px; color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 8%, transparent); font-size: 11px; font-weight: 700; }
.empty-inline { display: flex; align-items: center; gap: 13px; min-height: 96px; margin-top: 20px; padding: 16px; border: 1px dashed var(--border-color); border-radius: 7px; background: color-mix(in srgb, var(--bg-secondary) 68%, transparent); }
.empty-inline > div { flex: 1; }
.empty-inline strong { font-size: 14px; }
.empty-inline p { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.5; }
.empty-inline--quiet { min-height: 86px; }
.profile-suggestions { margin-top: 22px; border-top: 1px solid var(--border-color-light); }
.profile-suggestion { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; padding: 20px 2px; border-bottom: 1px solid var(--border-color-light); }
.suggestion-main { min-width: 0; }
.suggestion-main h3 { margin: 10px 0 0; font-size: 15px; line-height: 1.45; }
.suggestion-main p { margin: 7px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.6; }
.suggestion-main small { display: block; margin-top: 9px; color: var(--text-muted); font-size: 11px; }
.profile-filter { display: inline-flex; gap: 3px; margin-top: 20px; padding: 3px; border-radius: 7px; background: var(--bg-tertiary); }
.profile-filter button { min-height: 32px; border: 0; border-radius: 5px; padding: 0 10px; color: var(--text-muted); background: transparent; cursor: pointer; font-size: 12px; }
.profile-filter button.active { color: var(--text-primary); background: var(--bg-secondary); box-shadow: var(--shadow-sm); font-weight: 700; }
.claim-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; padding: 20px 2px; border-bottom: 1px solid var(--border-color-light); }
.claim-main { min-width: 0; }
.claim-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.domain-label, .review-label, .context-label, .memory-type { display: inline-flex; align-items: center; min-height: 22px; padding: 0 7px; border-radius: 4px; font-size: 11px; font-weight: 700; }
.domain-label { color: var(--text-secondary); background: var(--bg-tertiary); }
.review-label { color: var(--color-warning); background: color-mix(in srgb, var(--color-warning) 10%, transparent); }
.review-label--confirmed, .review-label--corrected, .context-label { color: var(--color-success); background: color-mix(in srgb, var(--color-success) 9%, transparent); }
.review-label--rejected { color: var(--text-muted); background: var(--bg-tertiary); }
.claim-row h3 { margin: 10px 0 0; font-size: 15px; line-height: 1.45; }
.claim-value { margin: 6px 0 0; color: var(--text-primary); font-size: 14px; line-height: 1.6; overflow-wrap: anywhere; }
.claim-rationale { margin: 7px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.55; }
.claim-evidence { margin-top: 10px; color: var(--text-muted); font-size: 12px; }
.claim-evidence summary { width: fit-content; cursor: pointer; }
.claim-evidence > div { display: flex; align-items: center; gap: 8px; margin-top: 6px; }
.claim-evidence code { overflow: hidden; color: var(--text-secondary); font-family: var(--font-family-mono); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.claim-actions { display: flex; align-items: flex-start; flex-wrap: wrap; justify-content: flex-end; gap: 5px; max-width: 260px; }
.memory-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.memory-toolbar > span { color: var(--text-muted); font-size: 12px; }
.memory-row { display: grid; grid-template-columns: auto minmax(0, 1fr) auto 34px; align-items: start; gap: 13px; padding: 18px 2px; border-bottom: 1px solid var(--border-color-light); }
.memory-type { margin-top: 1px; color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 9%, transparent); }
.memory-copy { min-width: 0; }
.memory-copy strong { font-size: 14px; }
.memory-copy p { display: -webkit-box; overflow: hidden; margin: 5px 0; color: var(--text-secondary); font-size: 13px; line-height: 1.55; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.memory-copy small { color: var(--text-muted); font-size: 11px; }
.memory-use { display: grid; justify-items: end; gap: 4px; min-width: 70px; color: var(--text-muted); font-size: 11px; }
.context-sidebar { position: sticky; top: 22px; min-width: 0; }
.sidebar-section { padding: 28px 0; border-bottom: 1px solid var(--border-color); }
.sidebar-heading { align-items: center; }
.sidebar-heading h2 { font-size: 16px; }
.help-icon { color: var(--text-muted); cursor: help; }
.control-field { display: grid; gap: 8px; margin-top: 18px; }
.control-field > span { color: var(--text-secondary); font-size: 12px; font-weight: 700; }
.control-field :deep(.el-segmented) { width: 100%; min-height: 40px; padding: 3px; }
.control-field :deep(.el-segmented__item) { min-width: 0; }
.permission-list { margin-top: 13px; }
.permission-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; min-height: 56px; border-bottom: 1px solid var(--border-color-light); }
.permission-row > span { display: grid; gap: 2px; }
.permission-row strong { font-size: 13px; }
.permission-row small { color: var(--text-muted); font-size: 11px; line-height: 1.35; }
.audit-id { color: var(--text-muted); font-family: var(--font-family-mono); font-size: 11px; }
.context-note { display: flex; align-items: flex-start; gap: 7px; margin: 16px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.55; }
.source-list { margin-top: 12px; }
.source-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 50px; border-bottom: 1px solid var(--border-color-light); }
.source-row > span { display: grid; gap: 2px; }
.source-row strong { font-size: 13px; }
.source-row small { color: var(--text-muted); font-size: 11px; }
.source-row .el-icon { color: var(--color-success); }
.source-row--muted { opacity: .7; }
.source-row--muted .el-icon { color: var(--text-muted); }
.access-details { margin-top: 15px; }
.access-details summary { display: flex; align-items: center; justify-content: space-between; min-height: 42px; cursor: pointer; color: var(--text-secondary); font-size: 12px; font-weight: 700; }
.access-details summary > span { display: inline-flex; align-items: center; gap: 7px; }
.access-details[open] summary > .el-icon { transform: rotate(90deg); }
.access-list { border-top: 1px solid var(--border-color-light); }
.access-row { display: grid; gap: 2px; padding: 10px 0; border-bottom: 1px solid var(--border-color-light); font-size: 12px; }
.access-row small, .access-empty { color: var(--text-muted); font-size: 11px; }
.dialog-form { display: grid; gap: 18px; }
.dialog-form label { display: grid; gap: 8px; }
.dialog-form label > span, .original-value > span { color: var(--text-secondary); font-size: 13px; font-weight: 700; }
.dialog-form label small { color: var(--text-muted); font-weight: 400; }
.original-value { padding: 12px; border-left: 3px solid var(--color-warning); background: color-mix(in srgb, var(--color-warning) 7%, var(--bg-secondary)); }
.original-value p { margin: 5px 0 0; color: var(--text-primary); line-height: 1.55; }
.switch-field { grid-template-columns: minmax(0, 1fr) auto; align-items: center; }
.switch-field > span { display: grid; gap: 2px; }
.switch-field small { line-height: 1.4; }
@media (max-width: 1080px) { .workspace-grid { grid-template-columns: minmax(0, 1fr) 280px; gap: 28px; } .briefing { grid-template-columns: minmax(0, 1fr) minmax(320px, .85fr); gap: 28px; } }
@media (max-width: 860px) { .companion-page { padding-top: 22px; } .briefing { grid-template-columns: 1fr; gap: 22px; } .workspace-grid { grid-template-columns: 1fr; } .context-sidebar { position: static; } .sidebar-section { padding: 28px 2px; } }
@media (max-width: 640px) { .profile-suggestion { grid-template-columns: 1fr; gap: 14px; } .page-header { align-items: stretch; flex-direction: column; gap: 18px; } .header-state { justify-content: space-between; width: 100%; box-sizing: border-box; } .briefing { padding: 24px 2px; } .briefing h2 { font-size: 22px; } .section-heading { align-items: flex-start; flex-direction: column; gap: 14px; } .section-counts { width: 100%; } .focus-row { grid-template-columns: 32px minmax(0, 1fr) 18px; } .focus-status { display: none; } .claim-row { grid-template-columns: 1fr; gap: 14px; } .claim-actions { justify-content: flex-start; max-width: none; } .memory-row { grid-template-columns: auto minmax(0, 1fr) 34px; } .memory-use { grid-column: 2; grid-row: 2; justify-items: start; } .empty-inline { align-items: flex-start; flex-wrap: wrap; } .empty-inline .el-button { margin-left: 45px; } }
@media (prefers-reduced-motion: reduce) { .suggestion-button { transition: none; } }
/* The companion is a reflective workspace, with evidence kept visible but secondary. */
.companion-page { width: min(100%, 1180px); padding-top: 42px; }
.page-kicker, .section-kicker { color: var(--color-primary-dark); letter-spacing: .06em; text-transform: uppercase; }
.page-header h1 { font-size: clamp(30px, 3vw, 38px); letter-spacing: -.02em; }
.briefing { gap: 52px; padding-block: 38px; }
.briefing-label { border-radius: 999px; padding-inline: 10px; }
.suggestion-button { min-height: 62px; border-radius: 8px; }
.workspace-grid { gap: 52px; }
.profile-suggestion, .claim-row, .memory-row { padding-block: 22px; }
.context-sidebar { top: 28px; }
@media (max-width: 860px) { .companion-page { padding-top: 28px; } }
</style>
