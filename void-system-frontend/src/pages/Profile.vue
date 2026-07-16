<template>
  <div class="profile-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">账号</p>
        <h1>个人资料</h1>
        <p>告诉工作台你正在关注什么，建议和规划会更贴近你的节奏。</p>
      </div>
    </header>

    <div v-if="loadState === 'loading'" class="profile-state" aria-live="polite">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在加载个人资料...</span>
    </div>

    <div v-else-if="loadState === 'error'" class="profile-state profile-state--error" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <div>
        <strong>个人资料暂时无法加载</strong>
        <p>{{ loadError }}</p>
      </div>
      <el-button :icon="Refresh" :loading="loading.profile" @click="loadUserInfo">重新加载</el-button>
    </div>

    <template v-else>
    <section class="identity-row" aria-label="当前账号">
      <span class="identity-avatar" aria-hidden="true">{{ userInitial }}</span>
      <div class="identity-copy">
        <strong>{{ userInfo.username || '正在加载…' }}</strong>
        <span>{{ userInfo.email || '未绑定邮箱' }}</span>
      </div>
      <span class="focus-tag">{{ selectedMajorLabel }}</span>
    </section>

    <section class="profile-editor" aria-labelledby="profile-editor-title">
      <div class="section-heading">
        <div>
          <h2 id="profile-editor-title">你的当前方向</h2>
          <p>这几项会用于行动规划和对话时的上下文参考。</p>
        </div>
      </div>

      <div class="form-grid">
        <label class="form-field">
          <span>称呼</span>
          <el-input v-model="userInfo.username" placeholder="例如：小林" maxlength="50" show-word-limit />
          <small v-if="errors.username" class="form-error">{{ errors.username }}</small>
        </label>

        <label class="form-field">
          <span>关注方向</span>
          <el-input v-model="userInfo.major" maxlength="100" show-word-limit placeholder="例如：项目管理、考研、英语或健康" />
          <small>用你自己的话描述即可，规划和对话会把它作为上下文参考。</small>
        </label>

        <label class="form-field form-field--wide">
          <span>当前目标</span>
          <el-input v-model="userInfo.learningGoal" type="textarea" :rows="4" maxlength="300" show-word-limit placeholder="例如：本月完成线性代数第一轮复习" />
          <small>写一句眼下最想稳定推进的事情即可。</small>
        </label>
      </div>

      <footer class="editor-footer">
        <p v-if="saveState === 'saved'" class="save-feedback">资料已保存</p>
        <p v-else>保存后会同步到工作台和后续建议。</p>
        <el-button type="primary" :loading="loading.profile" @click="saveUserInfo"><el-icon><Check /></el-icon>保存资料</el-button>
      </footer>
    </section>

    <details class="account-details">
      <summary>账户信息 <el-icon><InfoFilled /></el-icon></summary>
      <dl>
        <div><dt>邮箱</dt><dd>{{ userInfo.email || '未绑定' }}</dd></div>
        <div><dt>账户编号</dt><dd>{{ userInfo.uid || '--' }}</dd></div>
      </dl>
    </details>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, InfoFilled, Loading, Refresh, WarningFilled } from '@element-plus/icons-vue'
import { getCurrentUser, updateUserProfile } from '../api/user.js'

const loading = reactive({ profile: false })
const errors = reactive({ username: '' })
const saveState = ref('idle')
const loadState = ref('loading')
const loadError = ref('')
const userInfo = reactive({ username: '', email: '', learningGoal: '', major: '', uid: '' })
const selectedMajorLabel = computed(() => userInfo.major || '尚未设置方向')
const userInitial = computed(() => String(userInfo.username || '用').trim().charAt(0).toUpperCase() || '用')

const validateForm = () => {
  errors.username = userInfo.username?.trim() ? '' : '请填写称呼'
  return !errors.username
}

const saveUserInfo = async () => {
  saveState.value = 'idle'
  if (!validateForm()) return
  loading.profile = true
  try {
    await updateUserProfile(userInfo)
    userInfo.username = userInfo.username.trim()
    saveState.value = 'saved'
    ElMessage.success('资料已保存')
  } catch (error) {
    ElMessage.error(error?.message || '保存失败，请稍后重试')
  } finally {
    loading.profile = false
  }
}

const loadUserInfo = async () => {
  loadState.value = 'loading'
  loadError.value = ''
  try {
    const userData = await getCurrentUser()
    Object.assign(userInfo, {
      username: userData.username || '',
      email: userData.email || '',
      uid: userData.user_id || '',
      learningGoal: userData.learning_goal || '',
      major: userData.specialization || ''
    })
    loadState.value = 'ready'
  } catch (error) {
    loadState.value = 'error'
    loadError.value = error?.message || '请检查服务连接后重试。已经保存的资料不会丢失。'
    ElMessage.error('个人资料暂时无法加载')
  }
}

onMounted(loadUserInfo)
</script>

<style scoped>
.profile-page { width:min(100%, 860px); margin:0 auto; padding:32px 0 64px; color:var(--text-primary); }.page-header { padding:0 2px 24px; border-bottom:1px solid var(--border-color); }.page-kicker { margin:0 0 6px; color:var(--color-primary); font-size:12px; font-weight:700; }.page-header h1 { margin:0; font-size:28px; line-height:1.2; }.page-header p:not(.page-kicker) { max-width:620px; margin:9px 0 0; color:var(--text-secondary); line-height:1.6; }.profile-state { display:flex; align-items:center; justify-content:center; gap:10px; min-height:250px; color:var(--text-muted); }.profile-state--error { justify-content:flex-start; min-height:0; margin-top:24px; padding:18px; border:1px solid color-mix(in srgb,var(--color-danger) 24%,var(--border-color)); border-radius:7px; color:var(--text-secondary); background:color-mix(in srgb,var(--color-danger) 5%,var(--bg-secondary)); }.profile-state--error > .el-icon { flex:0 0 auto; color:var(--color-danger); font-size:22px; }.profile-state--error > div { flex:1; min-width:0; }.profile-state--error strong { color:var(--text-primary); font-size:14px; }.profile-state--error p { margin:4px 0 0; font-size:13px; line-height:1.5; }.identity-row { display:flex; align-items:center; gap:12px; min-height:82px; padding:20px 2px; border-bottom:1px solid var(--border-color-light); }.identity-avatar { display:grid; place-items:center; width:42px; height:42px; border-radius:50%; color:var(--color-primary-dark); background:color-mix(in srgb, var(--color-primary) 15%, var(--bg-secondary)); font-size:16px; font-weight:800; }.identity-copy { display:grid; min-width:0; gap:3px; }.identity-copy strong { font-size:16px; }.identity-copy span { overflow:hidden; color:var(--text-muted); font-size:13px; text-overflow:ellipsis; white-space:nowrap; }.focus-tag { margin-left:auto; max-width:42%; overflow:hidden; padding:5px 9px; border:1px solid color-mix(in srgb, var(--color-primary) 22%, var(--border-color)); border-radius:6px; color:var(--color-primary-dark); background:color-mix(in srgb, var(--color-primary) 8%, var(--bg-secondary)); font-size:12px; font-weight:700; text-overflow:ellipsis; white-space:nowrap; }.profile-editor { padding:30px 2px 0; }.section-heading { display:flex; justify-content:space-between; gap:18px; }.section-heading h2 { margin:0; font-size:18px; }.section-heading p { margin:6px 0 0; color:var(--text-secondary); font-size:14px; line-height:1.55; }.form-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; margin-top:24px; }.form-field { display:grid; gap:8px; }.form-field > span { color:var(--text-secondary); font-size:14px; font-weight:700; }.form-field > small { color:var(--text-muted); font-size:12px; line-height:1.45; }.form-field--wide { grid-column:1/-1; }.form-error { color:var(--color-danger) !important; }.form-field :deep(.el-input__wrapper),.form-field :deep(.el-select__wrapper),.form-field :deep(.el-textarea__inner) { border:1px solid var(--border-color); border-radius:7px; background:var(--bg-secondary); box-shadow:none; }.form-field :deep(.el-input__wrapper),.form-field :deep(.el-select__wrapper) { min-height:44px; }.form-field :deep(.el-input__wrapper.is-focus),.form-field :deep(.el-select__wrapper.is-focused),.form-field :deep(.el-textarea__inner:focus) { border-color:var(--color-primary); box-shadow:0 0 0 3px color-mix(in srgb, var(--color-primary) 13%, transparent); }.editor-footer { display:flex; align-items:center; justify-content:space-between; gap:18px; margin-top:24px; padding-top:20px; border-top:1px solid var(--border-color-light); }.editor-footer p { margin:0; color:var(--text-muted); font-size:13px; }.editor-footer .save-feedback { color:var(--color-success); font-weight:700; }.account-details { margin-top:32px; padding-top:18px; border-top:1px solid var(--border-color-light); color:var(--text-secondary); }.account-details summary { display:flex; align-items:center; width:fit-content; gap:7px; cursor:pointer; font-size:13px; }.account-details summary::-webkit-details-marker { display:none; }.account-details dl { display:grid; gap:0; margin:14px 0 0; }.account-details dl div { display:flex; justify-content:space-between; gap:18px; padding:11px 0; border-bottom:1px solid var(--border-color-light); }.account-details dt { color:var(--text-muted); font-size:13px; }.account-details dd { max-width:65%; margin:0; color:var(--text-primary); font-size:13px; overflow-wrap:anywhere; text-align:right; }@media (max-width:720px) { .profile-page { padding:22px 0 48px; }.profile-state--error { align-items:flex-start; flex-wrap:wrap; }.profile-state--error .el-button { width:100%; }.form-grid { grid-template-columns:1fr; }.editor-footer { align-items:flex-start; flex-direction:column; }.editor-footer .el-button { align-self:flex-end; }.focus-tag { max-width:48%; } }
</style>
