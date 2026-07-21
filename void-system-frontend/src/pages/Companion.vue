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

        <section class="workspace-section profile-workspace" aria-labelledby="profile-title">
          <div class="section-heading profile-workspace-heading">
            <div>
              <p class="section-kicker">协作偏好与工作记录</p>
              <h2 id="profile-title">系统如何更好地配合你</h2>
              <p>先看你已确认的偏好与近期记录。任何新建议都由你决定是否保留，不会把一次任务变成人格结论。</p>
            </div>
            <div class="profile-heading-side">
              <div class="profile-totals" aria-label="协作偏好与工作记录统计">
                <span><strong>{{ profileSummary.established || 0 }}</strong> 已确认</span>
                <span><strong>{{ profileSummary.reviewing || 0 }}</strong> 待确认</span>
                <span><strong>{{ profileSummary.signals || 0 }}</strong> 条参考记录</span>
              </div>
              <el-button type="primary" :icon="Compass" :loading="loading.inference" :disabled="!settings.permissions.profile || !profileEvidence.ready_for_inference" @click="inferProfileUnderstanding">整理协作建议</el-button>
            </div>
          </div>

          <div class="profile-intent" :class="{ 'profile-intent--off': !settings.permissions.profile }">
            <span class="profile-intent-mark"><el-icon><User /></el-icon></span>
            <div>
              <strong>{{ settings.permissions.profile ? '只根据你允许的记录逐步学习' : '帮助系统理解我目前已关闭' }}</strong>
              <p>{{ settings.permissions.profile ? '目前只参考任务汇总、复盘结果、你的确认或修正，以及明确授权的长期记忆；不会读取任务标题、聊天内容或资料正文。' : '开启右侧“帮助系统理解我”后，系统才会整理可审阅的协作建议。' }}</p>
            </div>
          </div>

          <div v-if="profileFacets.length" class="profile-layer">
            <div class="profile-layer-heading"><div><span class="layer-eyebrow">已确认</span><h3>已确认的协作偏好</h3></div><p>这些是你确认或修正后允许系统在后续协助中参考的内容。</p></div>
            <div class="facet-grid">
              <article v-for="facet in profileFacets" :key="facet.facet_id" class="profile-facet">
                <span>{{ facet.label }}</span><strong>{{ facet.title }}</strong><p>{{ facet.value }}</p><small>{{ facet.source }} · {{ formatDate(facet.updated_at) }}</small>
              </article>
            </div>
          </div>

          <div v-if="profilePatterns.length" class="profile-layer">
            <div class="profile-layer-heading"><div><span class="layer-eyebrow">近期记录</span><h3>近期工作记录</h3></div><p>这里只显示已授权记录的汇总，不对你做性格判断。</p></div>
            <div class="pattern-list">
              <article v-for="pattern in profilePatterns" :key="pattern.pattern_id" class="pattern-row">
                <span class="pattern-mark"><el-icon><CircleCheck /></el-icon></span><div><strong>{{ pattern.title }}</strong><p>{{ pattern.summary }}</p></div><span class="freshness-label">{{ pattern.freshness }}</span>
              </article>
            </div>
          </div>

          <div class="profile-layer profile-layer--review">
            <div class="profile-layer-heading"><div><span class="layer-eyebrow">等待确认</span><h3>需要你确认的协作建议</h3></div><p>只有明确、可修改的建议会出现在这里。确认前不会用于对话或规划。</p></div>
            <div v-if="profileHypotheses.length" class="hypothesis-list">
              <article v-for="hypothesis in profileHypotheses" :key="hypothesis.hypothesis_id" class="hypothesis-row">
                <div class="hypothesis-copy">
                  <span>{{ hypothesis.label }}</span><h4>{{ hypothesis.title }}</h4><p>{{ hypothesis.detail }}</p>
                  <div v-if="hypothesis.evidence.length" class="hypothesis-evidence"><strong>参考记录</strong><span v-for="evidence in hypothesis.evidence" :key="evidence.label + ':' + evidence.observed_at">{{ evidence.label }}：{{ evidence.detail }}</span></div>
                </div>
                <div class="hypothesis-actions"><el-button type="success" plain :icon="Check" :loading="loading.review" @click="reviewHypothesis(hypothesis, 'confirmed')">确认</el-button><el-button :icon="EditPen" :loading="loading.review" @click="openHypothesisCorrection(hypothesis)">修正</el-button><el-button text :icon="Close" :loading="loading.review" @click="reviewHypothesis(hypothesis, 'rejected')">不采用</el-button></div>
              </article>
            </div>
            <div v-else class="profile-empty-state"><span class="empty-icon"><el-icon><Compass /></el-icon></span><div><strong>还没有需要你确认的协作建议</strong><p>{{ profileEvidence.ready_for_inference ? '可以根据当前记录整理少量具体、可修正的协作建议。' : '继续使用目标、执行和复盘后，系统会先积累足够的记录基础。' }}</p></div></div>
          </div>

          <details class="profile-sources" open>
            <summary><span><el-icon><View /></el-icon>本次整理参考了哪些记录</span><small>{{ profileSources.length }} 类来源</small></summary>
            <div v-if="profileSources.length" class="profile-source-list"><div v-for="source in profileSources" :key="source.source_id" class="profile-source-row"><div><strong>{{ source.label }}</strong><p>{{ source.detail }}</p></div><span>{{ source.count }} 条</span></div></div>
            <p v-else class="access-empty">还没有形成可用记录。</p>
          </details>
        </section>

        <section class="workspace-section" aria-labelledby="memory-title">
          <div class="section-heading">
            <div>
              <p class="section-kicker">长期记忆</p>
              <h2 id="memory-title">值得保留的信息</h2>
              <p>手动保存的内容可立即使用；系统整理出的候选需先确认。你可暂停使用、归档或彻底忘记。</p>
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
          <div class="persona-fields">
            <div class="persona-heading">
              <span>精灵人设</span>
              <small>只影响表达与协作方式</small>
            </div>
            <label class="control-field control-field--compact">
              <span>怎么称呼它</span>
              <el-input v-model="settings.persona.name" maxlength="48" show-word-limit :disabled="loading.settings" />
            </label>
            <label class="control-field control-field--compact">
              <span>它是什么角色</span>
              <el-input v-model="settings.persona.role" maxlength="80" show-word-limit :disabled="loading.settings" />
            </label>
            <label class="control-field control-field--compact">
              <span>怎么介绍它</span>
              <el-input v-model="settings.persona.brief" type="textarea" :rows="3" maxlength="500" show-word-limit :disabled="loading.settings" />
            </label>
            <el-button class="persona-save" plain :loading="loading.settings" @click="savePersona">保存人设</el-button>
          </div>
        </section>

        <section class="sidebar-section">
          <div class="sidebar-heading">
            <div><p class="section-kicker">数据权限</p><h2>可以参考什么</h2></div>
            <el-tooltip content="权限决定系统精灵能否读取相应数据；个人资料馆仅按当前问题检索你的资料馆，不会扫描未加入的共享资料。" placement="top">
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
const loading = reactive({ page: true, settings: false, briefing: false, inference: false, review: false, memory: false, access: false })
const settings = reactive({
  enabled: true,
  tone: 'calm',
  initiative: 'balanced',
  persona: { name: '系统精灵', role: '协作伙伴', brief: '' },
  permissions: {}
})
const briefing = ref({})
const profile = ref({ summary: {}, facets: [], patterns: [], hypotheses: [], sources: [], evidence: {} })
const profileSuggestions = ref([])
const memories = ref([])
const accessRecords = ref([])
const claimFilter = ref('all')
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
  { key: 'knowledge', label: '个人资料馆', description: '开启后，对话会按当前问题检索你上传或已加入资料馆的内容' },
  { key: 'rewards', label: '奖励与资源', description: '余额和已获得资源；只在确有必要时提供摘要' }
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
const profileEvidenceSourceMeta = {
  task_history: { label: '任务与执行汇总', detail: '只统计目标、执行和步骤等工作流汇总，不读取标题、描述或产出正文。' },
  task_reviews: { label: '任务复盘', detail: '只使用已完成复盘的结构化记录，不读取其他聊天内容。' },
  profile_feedback: { label: '你的确认与修正', detail: '你对协作建议的确认、修正或不采用会成为可追溯的反馈依据。' },
  manual_evidence: { label: '明确保存的依据', detail: '仅使用你主动录入或明确导入的可审阅信息。' },
  explicit_memories: { label: '授权的长期记忆', detail: '只有勾选“帮助系统理解我”的记忆会直接加入画像，不会自动读取全部记忆。' }
}
const permissionLabels = Object.fromEntries(permissionOptions.map((item) => [item.key, item.label]))

const correctionDialog = reactive({ open: false, claim: null, value: '', reason: '' })
const emptyMemory = () => ({ memory_type: 'fact', title: '', content: '', use_in_context: true, contribute_to_profile: false })
const memoryDialog = reactive({ open: false, memoryId: null, form: emptyMemory() })

const profileSummary = computed(() => profile.value?.summary || {})
const profileFacets = computed(() => profile.value?.facets || [])
const profilePatterns = computed(() => profile.value?.patterns || [])
const profileHypotheses = computed(() => profile.value?.hypotheses || [])
const profileSources = computed(() => profile.value?.sources || [])
const profileEvidence = computed(() => profile.value?.evidence || {
  eligible_signal_count: 0,
  minimum_signal_count: 3,
  permission_enabled: false,
  ready_for_inference: false,
  sources: []
})
const visibleMemories = computed(() => memories.value.filter((memory) => memory.status === memoryFilter.value))
const focusItems = computed(() => briefing.value?.focus_items || [])
const suggestions = computed(() => briefing.value?.suggestions || [])
const contextSources = computed(() => briefing.value?.context?.sources || [])
const profileInferenceNote = computed(() => {
  if (!settings.permissions.profile) return '先在右侧打开“帮助系统理解我”，再整理协作建议。'
  if (profileEvidence.value.ready_for_inference) return '只会将当前展示的记录整理成待确认建议，不会自动当作事实使用。'
  return '会先刷新任务记录汇总；不足三条合格记录时不会让模型猜测。'
})
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
  settings.persona = {
    name: value.persona?.name || '系统精灵',
    role: value.persona?.role || '协作伙伴',
    brief: value.persona?.brief || ''
  }
  settings.permissions = Object.fromEntries(permissionOptions.map((item) => [item.key, value.permissions?.[item.key] ?? false]))
}

async function loadPage() {
  loading.page = true
  try {
    const [settingsResult, profileResult, memoryResult] = await Promise.allSettled([
      companionApi.getSettings(), companionApi.getProfile(), companionApi.listMemories({ limit: 200 })
    ])
    if (settingsResult.status === 'fulfilled') normalizeSettings(settingsResult.value)
    else throw settingsResult.reason
    if (profileResult.status === 'fulfilled') profile.value = profileResult.value
    if (memoryResult.status === 'fulfilled') memories.value = memoryResult.value
    await refreshBriefing(false)
    await loadAccessLog(false)
    const partialFailures = [profileResult, memoryResult].filter((item) => item.status === 'rejected').length
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

function savePersona() {
  return saveSettings({ persona: { ...settings.persona } })
}

async function refreshProfileUnderstanding() {
  profile.value = await companionApi.getProfile()
}

async function inferProfileUnderstanding() {
  loading.inference = true
  try {
    const result = await companionApi.inferProfile({ max_signals: 24, max_hypotheses: 4 })
    await refreshProfileUnderstanding()
    const count = result?.hypotheses?.length || 0
    ElMessage[count ? 'success' : 'info'](
      count ? `已整理 ${count} 条待判断理解` : '暂时没有足够的新线索形成理解'
    )
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '暂时无法整理个人理解'))
  } finally {
    loading.inference = false
  }
}

async function reviewHypothesis(hypothesis, decision) {
  loading.review = true
  try {
    await companionApi.reviewHypothesis(hypothesis.hypothesis_id, decision)
    await refreshProfileUnderstanding()
    ElMessage.success(decision === 'confirmed' ? '这项理解已确认' : '这项理解不会再参与后续协助')
    await refreshBriefing(false)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '这项理解没有保存成功'))
  } finally {
    loading.review = false
  }
}

function openHypothesisCorrection(hypothesis) {
  correctionDialog.claim = { hypothesis_id: hypothesis.hypothesis_id, value: hypothesis.title }
  correctionDialog.value = hypothesis.title
  correctionDialog.reason = ''
  correctionDialog.open = true
}

async function submitCorrection() {
  if (!correctionDialog.value.trim()) return ElMessage.warning('请填写更准确的说法')
  loading.review = true
  try {
    await companionApi.reviewHypothesis(
      correctionDialog.claim.hypothesis_id,
      'corrected',
      correctionDialog.value.trim(),
      correctionDialog.reason.trim()
    )
    await refreshProfileUnderstanding()
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
/* A personal understanding file: factual first, interpretive only where review is needed. */
.companion-page { width: min(100%, 1180px); margin: 0 auto; padding: 42px 0 72px; color: var(--text-primary); }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 28px; padding: 4px 2px 34px; border-bottom: 1px solid var(--border-color-light); }
.page-kicker, .section-kicker { margin: 0 0 7px; color: var(--color-primary-dark); font-size: 11px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.page-header h1 { margin: 0; font-size: 36px; line-height: 1.16; letter-spacing: 0; }
.page-header h1 + p { max-width: 620px; margin: 10px 0 0; color: var(--text-secondary); font-size: 14px; line-height: 1.7; }
.header-state { display: inline-flex; align-items: center; gap: 9px; flex: none; min-height: 38px; padding: 0 5px 0 12px; color: var(--text-secondary); border: 1px solid var(--border-color); background: var(--bg-secondary); border-radius: 7px; font-size: 12px; font-weight: 700; }
.state-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-success); box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-success) 15%, transparent); }
.header-state--paused .state-dot { background: var(--text-muted); box-shadow: none; }

.briefing { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(300px, .76fr); gap: 52px; padding: 38px 2px; border-bottom: 1px solid var(--border-color-light); }
.briefing-label { display: inline-flex; margin-bottom: 11px; padding: 2px 10px; color: var(--color-primary-dark); border: 1px solid color-mix(in srgb, var(--color-primary) 28%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 7%, var(--bg-secondary)); border-radius: 999px; font-size: 11px; font-weight: 800; line-height: 20px; }
.briefing h2 { max-width: 720px; margin: 0; font-size: 25px; line-height: 1.38; }
.briefing-copy > p { max-width: 700px; margin: 10px 0 0; color: var(--text-secondary); font-size: 14px; line-height: 1.68; }
.briefing-actions { display: grid; align-content: center; gap: 8px; }
.suggestion-button { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 18px; width: 100%; min-height: 62px; padding: 13px 15px; color: inherit; text-align: left; cursor: pointer; border: 1px solid var(--border-color-light); border-radius: 7px; background: var(--bg-secondary); transition: border-color .18s ease, background .18s ease, transform .18s ease; }
.suggestion-button:hover { border-color: color-mix(in srgb, var(--color-primary) 52%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 4%, var(--bg-secondary)); transform: translateX(2px); }
.suggestion-button span { display: grid; gap: 4px; min-width: 0; }
.suggestion-button strong { color: var(--text-primary); font-size: 13px; }
.suggestion-button small { overflow: hidden; color: var(--text-muted); font-size: 11px; line-height: 1.45; text-overflow: ellipsis; white-space: nowrap; }
.suggestion-button .el-icon { color: var(--color-primary); }

.workspace-grid { display: grid; grid-template-columns: minmax(0, 1fr) 264px; gap: 52px; align-items: start; }
.workspace-main { min-width: 0; }
.workspace-section { padding: 36px 2px; border-bottom: 1px solid var(--border-color-light); }
.section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.section-heading h2, .sidebar-heading h2 { margin: 0; font-size: 20px; line-height: 1.35; }
.section-heading > div > p:last-child { max-width: 650px; margin: 7px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.65; }
.focus-list { margin-top: 18px; border-top: 1px solid var(--border-color-light); }
.focus-row { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto 18px; gap: 12px; align-items: center; width: 100%; min-height: 64px; padding: 10px 4px; color: inherit; text-align: left; cursor: pointer; border: 0; border-bottom: 1px solid var(--border-color-light); background: transparent; }
.focus-row:hover .focus-copy strong { color: var(--color-primary); }
.focus-icon, .empty-icon { display: grid; place-items: center; width: 32px; height: 32px; color: var(--color-primary); border: 1px solid color-mix(in srgb, var(--color-primary) 24%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 6%, var(--bg-secondary)); border-radius: 50%; }
.focus-copy { display: grid; gap: 4px; min-width: 0; }
.focus-copy strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; transition: color .18s ease; }
.focus-copy small { overflow: hidden; color: var(--text-muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.focus-status { color: var(--text-secondary); font-size: 12px; }
.row-arrow { color: var(--text-muted); }
.empty-inline, .profile-empty-state { display: flex; align-items: flex-start; gap: 13px; margin-top: 18px; padding: 16px 0; }
.empty-inline > div, .profile-empty-state > div { min-width: 0; }
.empty-inline strong, .profile-empty-state strong { font-size: 13px; }
.empty-inline p, .profile-empty-state p { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.55; }
.empty-inline .el-button { margin-left: auto; }

.profile-workspace { padding-top: 38px; }
.profile-workspace-heading { align-items: flex-start; }
.profile-heading-side { display: grid; justify-items: end; gap: 12px; flex: none; }
.profile-totals { display: inline-flex; align-items: center; gap: 13px; color: var(--text-muted); font-size: 11px; }
.profile-totals span { padding-left: 13px; border-left: 1px solid var(--border-color-light); white-space: nowrap; }
.profile-totals span:first-child { padding-left: 0; border-left: 0; }
.profile-totals strong { color: var(--text-primary); font-size: 17px; font-variant-numeric: tabular-nums; }
.profile-intent { display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 12px; margin-top: 24px; padding: 15px 16px; border: 1px solid color-mix(in srgb, var(--color-primary) 20%, var(--border-color)); border-left: 3px solid var(--color-primary); border-radius: 6px; background: color-mix(in srgb, var(--color-primary) 5%, var(--bg-secondary)); }
.profile-intent-mark { display: grid; place-items: center; width: 28px; height: 28px; color: var(--color-primary); background: color-mix(in srgb, var(--color-primary) 11%, var(--bg-secondary)); border-radius: 50%; }
.profile-intent strong { font-size: 13px; }
.profile-intent p { margin: 4px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.62; }
.profile-intent--off { border-color: var(--border-color); border-left-color: var(--text-muted); background: var(--bg-tertiary); }
.profile-intent--off .profile-intent-mark { color: var(--text-muted); background: color-mix(in srgb, var(--text-muted) 10%, var(--bg-secondary)); }
.profile-layer { margin-top: 32px; }
.profile-layer-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 14px; }
.profile-layer-heading h3 { margin: 3px 0 0; font-size: 17px; line-height: 1.35; }
.profile-layer-heading p { max-width: 325px; margin: 0; color: var(--text-muted); font-size: 11px; line-height: 1.52; text-align: right; }
.layer-eyebrow { color: var(--color-primary); font-size: 10px; font-weight: 800; letter-spacing: .07em; text-transform: uppercase; }
.facet-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.profile-facet { display: flex; flex-direction: column; min-height: 144px; padding: 16px; border: 1px solid var(--border-color-light); border-top: 2px solid color-mix(in srgb, var(--color-primary) 55%, var(--border-color)); border-radius: 6px; background: var(--bg-secondary); }
.profile-facet > span { color: var(--color-primary-dark); font-size: 11px; font-weight: 800; }
.profile-facet strong { margin-top: 8px; font-size: 14px; line-height: 1.42; }
.profile-facet p { margin: 6px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.55; }
.profile-facet small { margin-top: auto; padding-top: 13px; color: var(--text-muted); font-size: 10px; }
.pattern-list, .hypothesis-list, .memory-list { border-top: 1px solid var(--border-color-light); }
.pattern-row { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--border-color-light); }
.pattern-mark { display: grid; place-items: center; width: 26px; height: 26px; color: var(--color-primary); border-radius: 50%; background: color-mix(in srgb, var(--color-primary) 9%, var(--bg-secondary)); }
.pattern-row strong { font-size: 13px; }
.pattern-row p { margin: 4px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.5; }
.freshness-label { color: var(--text-muted); font-size: 11px; white-space: nowrap; }
.profile-layer--review { padding: 20px; border: 1px solid color-mix(in srgb, var(--color-accent) 39%, var(--border-color)); border-radius: 7px; background: color-mix(in srgb, var(--color-accent) 5%, var(--bg-secondary)); }
.profile-layer--review .profile-layer-heading { margin-bottom: 3px; }
.profile-layer--review .layer-eyebrow, .hypothesis-copy > span { color: var(--color-accent); }
.hypothesis-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; align-items: center; padding: 18px 0; border-bottom: 1px solid color-mix(in srgb, var(--color-accent) 26%, var(--border-color)); }
.hypothesis-row:last-child { border-bottom: 0; }
.hypothesis-copy > span { font-size: 11px; font-weight: 800; }
.hypothesis-copy h4 { margin: 5px 0 0; font-size: 15px; line-height: 1.45; }
.hypothesis-copy > p { margin: 6px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.6; }
.hypothesis-evidence { display: grid; gap: 4px; margin-top: 12px; padding: 8px 10px; border-left: 2px solid color-mix(in srgb, var(--color-accent) 58%, transparent); background: color-mix(in srgb, var(--color-accent) 5%, transparent); color: var(--text-muted); font-size: 11px; line-height: 1.48; }
.hypothesis-evidence strong { color: var(--text-secondary); font-size: 11px; }
.hypothesis-actions { display: flex; align-items: center; justify-content: flex-end; gap: 6px; flex-wrap: wrap; }
.profile-empty-state { padding: 20px 0 4px; }
.profile-sources { margin-top: 28px; border-top: 1px solid var(--border-color-light); border-bottom: 1px solid var(--border-color-light); }
.profile-sources summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 52px; color: var(--text-secondary); cursor: pointer; font-size: 12px; font-weight: 700; list-style: none; }
.profile-sources summary::-webkit-details-marker { display: none; }
.profile-sources summary > span { display: inline-flex; align-items: center; gap: 7px; }
.profile-sources summary small { color: var(--text-muted); font-size: 11px; font-weight: 400; }
.profile-source-list { padding-bottom: 10px; }
.profile-source-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; padding: 10px 0; border-top: 1px solid var(--border-color-light); }
.profile-source-row strong { font-size: 12px; }
.profile-source-row p { margin: 3px 0 0; color: var(--text-muted); font-size: 11px; line-height: 1.45; }
.profile-source-row > span { color: var(--text-secondary); font-size: 11px; font-variant-numeric: tabular-nums; white-space: nowrap; }

.memory-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 20px; color: var(--text-muted); font-size: 12px; }
.profile-filter { display: inline-flex; padding: 3px; border: 1px solid var(--border-color); background: var(--bg-tertiary); border-radius: 6px; }
.profile-filter button { padding: 5px 9px; color: var(--text-muted); cursor: pointer; border: 0; background: transparent; border-radius: 4px; font: inherit; font-size: 11px; font-weight: 700; }
.profile-filter button.active { color: var(--text-primary); background: var(--bg-secondary); box-shadow: 0 1px 2px color-mix(in srgb, var(--text-primary) 12%, transparent); }
.memory-row { display: grid; grid-template-columns: auto minmax(0, 1fr) auto 34px; gap: 14px; align-items: start; padding: 18px 0; border-bottom: 1px solid var(--border-color-light); }
.memory-type { display: inline-flex; align-items: center; min-height: 24px; padding: 0 7px; color: var(--color-primary-dark); border: 1px solid color-mix(in srgb, var(--color-primary) 24%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 7%, var(--bg-secondary)); border-radius: 999px; font-size: 10px; font-weight: 800; white-space: nowrap; }
.memory-copy strong { font-size: 13px; }
.memory-copy p { margin: 4px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.55; white-space: pre-line; }
.memory-copy small { display: block; margin-top: 7px; color: var(--text-muted); font-size: 10px; }
.memory-use { display: grid; justify-items: end; gap: 4px; padding-top: 2px; color: var(--text-muted); font-size: 10px; white-space: nowrap; }
.empty-inline--quiet { border-top: 1px solid var(--border-color-light); }

.context-sidebar { position: sticky; top: 28px; border-left: 1px solid var(--border-color-light); }
.sidebar-section { padding: 30px 0 30px 24px; border-bottom: 1px solid var(--border-color-light); }
.sidebar-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.sidebar-heading h2 { font-size: 16px; }
.help-icon { margin-top: 3px; color: var(--text-muted); cursor: help; }
.control-field { display: grid; gap: 8px; margin-top: 18px; }
.control-field > span { color: var(--text-secondary); font-size: 12px; font-weight: 700; }
.control-field :deep(.el-segmented) { width: 100%; }
.persona-fields { display: grid; gap: 0; margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border-color-light); }
.persona-heading { display: grid; gap: 3px; }
.persona-heading > span { color: var(--text-primary); font-size: 13px; font-weight: 800; }
.persona-heading > small { color: var(--text-muted); font-size: 11px; line-height: 1.45; }
.control-field--compact { margin-top: 14px; }
.control-field--compact :deep(.el-input__wrapper), .control-field--compact :deep(.el-textarea__inner) { background: var(--bg-secondary); box-shadow: 0 0 0 1px var(--border-color) inset; }
.persona-save { justify-self: start; margin-top: 16px; }
.permission-list { margin-top: 12px; }
.permission-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; min-height: 58px; border-bottom: 1px solid var(--border-color-light); }
.permission-row > span { display: grid; gap: 3px; }
.permission-row strong { font-size: 12px; }
.permission-row small { color: var(--text-muted); font-size: 11px; line-height: 1.36; }
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
.original-value p { margin: 5px 0 0; line-height: 1.55; }
.switch-field { grid-template-columns: minmax(0, 1fr) auto; align-items: center; }
.switch-field > span { display: grid; gap: 2px; }
.switch-field small { line-height: 1.4; }

@media (max-width: 1080px) { .workspace-grid { grid-template-columns: minmax(0, 1fr) 280px; gap: 30px; } .briefing { grid-template-columns: minmax(0, 1fr) minmax(290px, .8fr); gap: 30px; } }
@media (max-width: 860px) { .companion-page { padding-top: 28px; } .briefing { grid-template-columns: 1fr; gap: 22px; } .workspace-grid { grid-template-columns: 1fr; } .context-sidebar { position: static; border-left: 0; } .sidebar-section { padding: 28px 2px; } }
@media (max-width: 760px) { .profile-workspace-heading, .profile-layer-heading { align-items: flex-start; flex-direction: column; gap: 14px; } .profile-layer-heading p { max-width: none; text-align: left; } .profile-heading-side { justify-items: start; width: 100%; } .profile-totals { width: 100%; justify-content: space-between; } .facet-grid { grid-template-columns: 1fr; } .hypothesis-row { grid-template-columns: 1fr; gap: 14px; } .hypothesis-actions { justify-content: flex-start; } }
@media (max-width: 640px) { .page-header { align-items: stretch; flex-direction: column; gap: 18px; } .header-state { justify-content: space-between; width: 100%; box-sizing: border-box; } .briefing { padding: 26px 2px; } .briefing h2 { font-size: 22px; } .section-heading { align-items: flex-start; flex-direction: column; gap: 14px; } .focus-row { grid-template-columns: 32px minmax(0, 1fr) 18px; } .focus-status { display: none; } .memory-row { grid-template-columns: auto minmax(0, 1fr) 34px; } .memory-use { grid-column: 2; grid-row: 2; justify-items: start; } .empty-inline { align-items: flex-start; flex-wrap: wrap; } .empty-inline .el-button { margin-left: 45px; } .profile-layer--review { margin-inline: -2px; padding: 16px; } .profile-source-row { gap: 8px; } }
@media (prefers-reduced-motion: reduce) { .suggestion-button { transition: none; } }
</style>
