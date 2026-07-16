<template>
  <section class="settings-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">个人工作区</p>
        <h1>设置</h1>
        <p>只保留会影响日常使用的偏好和设备操作。</p>
      </div>
      <div class="connection-status" :class="systemInfo.status">
        <span></span>{{ connectionLabel }}
        <el-button text circle :icon="Refresh" :loading="loading.health" title="重新检查服务状态" aria-label="重新检查服务状态" @click="loadHealth" />
      </div>
    </header>

    <nav class="settings-index" aria-label="设置分区">
      <a href="#appearance-title">显示</a>
      <a href="#account-title">账户</a>
      <a href="#device-title">设备与数据</a>
    </nav>

    <section class="settings-section" aria-labelledby="appearance-title">
      <div class="section-heading">
        <span class="section-icon"><el-icon><Brush /></el-icon></span>
        <div>
          <h2 id="appearance-title">显示</h2>
          <p>主题会立即应用，并保存在这台设备上。</p>
        </div>
      </div>

      <div class="theme-options" role="radiogroup" aria-label="界面主题">
        <button
          type="button"
          class="theme-option theme-option--light"
          :class="{ selected: preferences.themeMode === 'light' }"
          role="radio"
          :aria-checked="preferences.themeMode === 'light'"
          @click="setThemeMode('light')"
        >
          <span class="theme-preview"><i></i><i></i></span>
          <span><strong>浅色</strong><small>明亮、清晰，适合白天使用</small></span>
          <el-icon v-if="preferences.themeMode === 'light'"><CircleCheck /></el-icon>
        </button>
        <button
          type="button"
          class="theme-option theme-option--dark"
          :class="{ selected: preferences.themeMode === 'dark' }"
          role="radio"
          :aria-checked="preferences.themeMode === 'dark'"
          @click="setThemeMode('dark')"
        >
          <span class="theme-preview"><i></i><i></i></span>
          <span><strong>深色</strong><small>降低夜间使用时的视觉负担</small></span>
          <el-icon v-if="preferences.themeMode === 'dark'"><CircleCheck /></el-icon>
        </button>
      </div>
    </section>

    <section class="settings-section" aria-labelledby="account-title">
      <div class="section-heading">
        <span class="section-icon section-icon--blue"><el-icon><User /></el-icon></span>
        <div>
          <h2 id="account-title">账户</h2>
          <p>管理称呼、学习方向和当前目标；这些内容会用于规划上下文。</p>
        </div>
      </div>
      <div class="action-row">
        <div><strong>个人资料</strong><span>更新个人信息与工作方向</span></div>
        <el-button plain @click="router.push('/profile')">打开资料</el-button>
      </div>
    </section>

    <section class="settings-section" aria-labelledby="device-title">
      <div class="section-heading">
        <span class="section-icon section-icon--muted"><el-icon><Monitor /></el-icon></span>
        <div>
          <h2 id="device-title">设备与数据</h2>
          <p>这些操作仅影响当前浏览器，不会删除服务器中的目标、行动和资料。</p>
        </div>
      </div>

      <dl class="device-details">
        <div><dt>服务状态</dt><dd :class="systemInfo.status === 'online' ? 'is-success' : 'is-warning'">{{ connectionDetail }}</dd></div>
        <div><dt>系统版本</dt><dd>{{ systemInfo.version }}</dd></div>
      </dl>

      <div class="action-row">
        <div><strong>清除本地偏好</strong><span>移除主题和临时界面状态，不影响已登录账号。</span></div>
        <el-button plain :loading="loading.cache" @click="clearCache"><el-icon><Delete /></el-icon>清除</el-button>
      </div>
      <div class="action-row action-row--danger">
        <div><strong>退出当前设备</strong><span>撤销此设备上的会话并返回登录页。</span></div>
        <el-button type="danger" plain @click="confirmLogout"><el-icon><SwitchButton /></el-icon>退出登录</el-button>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Brush, CircleCheck, Delete, Monitor, Refresh, SwitchButton, User } from '@element-plus/icons-vue'
import { systemApi } from '../api/administration.js'
import { logout as logoutApi } from '../api/user.js'

const router = useRouter()
const loading = reactive({ cache: false, health: false })
const preferences = reactive({
  themeMode: document.documentElement.getAttribute('data-theme') || 'light'
})
const systemInfo = reactive({ status: 'checking', version: '--' })

const connectionLabel = computed(() => {
  if (systemInfo.status === 'online') return '服务已连接'
  if (systemInfo.status === 'offline') return '服务暂不可用'
  return '正在检查连接'
})

const connectionDetail = computed(() => systemInfo.status === 'online' ? '正常' : systemInfo.status === 'offline' ? '暂时不可用' : '检查中')

const applyTheme = (mode) => {
  const themeMode = mode === 'dark' ? 'dark' : 'light'
  preferences.themeMode = themeMode
  document.documentElement.setAttribute('data-theme', themeMode)
}

const loadPreferences = () => {
  try {
    const saved = JSON.parse(localStorage.getItem('settings_cache') || '{}')
    applyTheme(saved?.preferences?.themeMode || 'light')
  } catch {
    localStorage.removeItem('settings_cache')
    applyTheme('light')
  }
}

const setThemeMode = (mode) => {
  applyTheme(mode)
  localStorage.setItem('settings_cache', JSON.stringify({
    preferences: { themeMode: preferences.themeMode }
  }))
}

const loadHealth = async () => {
  loading.health = true
  try {
    const data = await systemApi.health()
    systemInfo.status = data.status === 'healthy' ? 'online' : 'offline'
    systemInfo.version = data.version || '--'
  } catch {
    systemInfo.status = 'offline'
  } finally {
    loading.health = false
  }
}

const clearCache = async () => {
  try {
    await ElMessageBox.confirm(
      '清除这台设备中的主题和临时界面状态？服务器中的目标、行动、资料和账号不会受影响。',
      '清除本地偏好',
      { confirmButtonText: '清除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  loading.cache = true
  try {
    localStorage.removeItem('settings_cache')
    sessionStorage.clear()
    applyTheme('light')
    ElMessage.success('本地偏好已清除')
  } finally {
    loading.cache = false
  }
}

const confirmLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '确定退出当前设备吗？',
      '退出登录',
      { confirmButtonText: '退出', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await logoutApi()
  } catch {
    // Local cleanup still protects this device when the service is unavailable.
  }
  await router.push('/login')
}

onMounted(() => {
  loadPreferences()
  loadHealth()
})
</script>

<style scoped>
.settings-page { width: min(100%, 960px); margin: 0 auto; padding: 42px 0 76px; color: var(--text-primary); }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; padding: 0 2px 28px; border-bottom: 1px solid var(--border-color); }
.page-kicker { margin: 0 0 8px; color: var(--color-primary-dark); font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.page-header h1 { margin: 0; font-size: clamp(28px, 4vw, 38px); line-height: 1.15; letter-spacing: -.02em; }
.page-header p:not(.page-kicker) { max-width: 590px; margin: 10px 0 0; color: var(--text-secondary); font-size: 15px; line-height: 1.65; }
.connection-status { display: inline-flex; align-items: center; flex: 0 0 auto; gap: 7px; color: var(--text-muted); font-size: 13px; white-space: nowrap; }
.connection-status > span { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); box-shadow: 0 0 0 4px color-mix(in srgb, var(--text-muted) 10%, transparent); }
.connection-status.online { color: var(--color-success); }.connection-status.online > span { background: var(--color-success); box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-success) 13%, transparent); }.connection-status.offline { color: var(--color-warning); }.connection-status.offline > span { background: var(--color-warning); box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-warning) 13%, transparent); }
.settings-index { position: sticky; top: 0; z-index: 3; display: flex; gap: 20px; padding: 12px 2px; border-bottom: 1px solid var(--border-color-light); background: color-mix(in srgb, var(--bg-primary) 92%, transparent); backdrop-filter: blur(12px); }
.settings-index a { color: var(--text-muted); font-size: 12px; font-weight: 700; text-decoration: none; }.settings-index a:hover { color: var(--color-primary-dark); }
.settings-section { padding: 34px 2px; border-bottom: 1px solid var(--border-color-light); scroll-margin-top: 56px; }
.section-heading { display: flex; align-items: flex-start; gap: 13px; }.section-heading h2 { margin: 0; font-size: 17px; line-height: 1.4; }.section-heading p { margin: 5px 0 0; color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
.section-icon { display: grid; place-items: center; flex: 0 0 auto; width: 36px; height: 36px; border: 1px solid color-mix(in srgb, var(--color-primary) 20%, var(--border-color)); border-radius: 8px; color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 8%, var(--bg-secondary)); }
.section-icon--blue { color: #276f92; border-color: color-mix(in srgb, #3b9cc6 24%, var(--border-color)); background: color-mix(in srgb, #3b9cc6 10%, var(--bg-secondary)); }.section-icon--muted { color: var(--text-secondary); border-color: var(--border-color); background: var(--bg-tertiary); }
.theme-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 22px 0 0 49px; }
.theme-option { display: grid; grid-template-columns: 58px minmax(0, 1fr) 18px; align-items: center; min-height: 84px; gap: 13px; padding: 13px; border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary); background: var(--bg-secondary); cursor: pointer; text-align: left; transition: border-color .16s ease, background .16s ease, transform .16s ease; }.theme-option:hover { border-color: color-mix(in srgb, var(--color-primary) 45%, var(--border-color)); transform: translateY(-1px); }.theme-option.selected { border-color: var(--color-primary); background: color-mix(in srgb, var(--color-primary) 7%, var(--bg-secondary)); box-shadow: 0 6px 16px color-mix(in srgb, var(--color-primary) 8%, transparent); }.theme-option strong,.theme-option small { display: block; }.theme-option small { margin-top: 4px; color: var(--text-muted); font-size: 12px; line-height: 1.4; }.theme-option > .el-icon { color: var(--color-primary); font-size: 18px; }
.theme-preview { display: grid; grid-template-rows: 9px 1fr; height: 52px; overflow: hidden; border: 1px solid var(--border-color); border-radius: 6px; background: #f5f8f6; }.theme-preview i:first-child { background: #8dbca6; }.theme-preview i:last-child { margin: 8px; background: #dce8e1; }.theme-option--dark .theme-preview { border-color: #31413a; background: #16211e; }.theme-option--dark .theme-preview i:first-child { background: #356d5a; }.theme-option--dark .theme-preview i:last-child { background: #2b3934; }
.device-details { display: grid; margin: 22px 0 0 49px; }.device-details div,.action-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 15px 0; border-bottom: 1px solid var(--border-color-light); }.device-details dt { color: var(--text-secondary); font-size: 14px; }.device-details dd { margin: 0; color: var(--text-primary); font-size: 14px; }.device-details .is-success { color: var(--color-success); font-weight: 700; }.device-details .is-warning { color: var(--color-warning); font-weight: 700; }
.action-row { margin-left: 49px; }.action-row:first-of-type { margin-top: 20px; }.action-row:last-child { border-bottom: 0; }.action-row > div { display: grid; gap: 4px; }.action-row strong { font-size: 14px; }.action-row span { color: var(--text-muted); font-size: 13px; line-height: 1.5; }.action-row--danger strong { color: var(--color-danger); }
@media (max-width: 720px) { .settings-page { padding: 26px 0 52px; }.page-header { align-items: flex-start; flex-direction: column; gap: 13px; }.settings-index { overflow-x: auto; gap: 18px; white-space: nowrap; }.theme-options { grid-template-columns: 1fr; margin-left: 0; }.device-details,.action-row { margin-left: 0; }.action-row { align-items: flex-start; flex-direction: column; }.action-row .el-button { align-self: flex-end; } }
</style>
