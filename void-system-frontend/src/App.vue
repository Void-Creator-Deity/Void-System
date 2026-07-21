<template>
  <div id="app" class="app-shell" :class="{ 'app-shell--workspace': isWorkspaceRoute }">
    <aside v-if="isWorkspaceRoute" class="workspace-sidebar">
      <button class="brand" type="button" aria-label="前往工作台" @click="router.push('/')">
        <span class="brand-mark" aria-hidden="true">V</span>
        <span class="brand-copy"><strong>虚空系统</strong><small>个人工作区</small></span>
      </button>

      <nav class="workspace-nav" aria-label="主要导航">
        <p class="nav-label">工作</p>
        <RouterLink v-for="item in workspaceNavigation" :key="item.to" :to="item.to" class="workspace-nav__item">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>

        <p class="nav-label nav-label--secondary">智能协作</p>
        <RouterLink v-for="item in assistantNavigation" :key="item.to" :to="item.to" class="workspace-nav__item">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>

        <template v-if="isAdmin">
          <p class="nav-label nav-label--secondary">管理</p>
          <RouterLink to="/admin/rag" class="workspace-nav__item">
            <el-icon><Files /></el-icon>
            <span>共享馆藏管理</span>
          </RouterLink>
          <RouterLink to="/admin/ai" class="workspace-nav__item">
            <el-icon><Cpu /></el-icon>
            <span>AI 服务</span>
          </RouterLink>
        </template>
      </nav>

      <button
        v-if="isAuthenticated"
        class="background-progress-trigger"
        type="button"
        aria-label="打开后台进度"
        @click="backgroundProgressOpen = true"
      >
        <el-icon><Clock /></el-icon>
        <span>后台进度</span>
        <span v-if="backgroundProgress.activeCount" class="background-progress-trigger__count">{{ backgroundProgress.activeCount }}</span>
      </button>

      <div class="sidebar-account">
        <el-dropdown v-if="isAuthenticated" trigger="click" placement="top-start" @command="handleAccountCommand">
          <button class="account-trigger" type="button" aria-label="打开账号菜单">
            <span class="account-avatar">{{ userAvatar }}</span>
            <span class="account-copy"><strong>{{ userName }}</strong><small>账号与偏好</small></span>
            <el-icon class="account-caret"><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu class="account-menu">
              <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人资料</el-dropdown-item>
              <el-dropdown-item command="settings"><el-icon><Setting /></el-icon>偏好设置</el-dropdown-item>
              <el-dropdown-item divided command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <header v-if="isWorkspaceRoute" class="mobile-header">
      <button class="brand" type="button" aria-label="前往工作台" @click="router.push('/')">
        <span class="brand-mark" aria-hidden="true">V</span>
        <span class="brand-copy"><strong>虚空系统</strong><small>{{ route.meta.title || '工作区' }}</small></span>
      </button>
      <div class="mobile-header__actions">
        <el-button v-if="isAuthenticated" text circle aria-label="打开后台进度" @click="backgroundProgressOpen = true">
          <el-badge :value="backgroundProgress.activeCount" :hidden="!backgroundProgress.activeCount" :max="9">
            <el-icon><Clock /></el-icon>
          </el-badge>
        </el-button>
        <el-button text circle aria-label="打开导航" @click="mobileNavOpen = true"><el-icon><Menu /></el-icon></el-button>
      </div>
    </header>

    <header v-else class="public-header">
      <button class="brand" type="button" aria-label="前往首页" @click="router.push('/login')">
        <span class="brand-mark" aria-hidden="true">V</span>
        <span class="brand-copy"><strong>虚空系统</strong><small>成长工作台</small></span>
      </button>
      <div class="public-header__actions">
        <el-button text @click="router.push('/login')">登录</el-button>
        <el-button type="primary" @click="router.push('/register')">创建账号</el-button>
      </div>
    </header>

    <el-drawer v-model="mobileNavOpen" direction="ltr" size="min(84vw, 340px)" :with-header="false" class="mobile-navigation">
      <div class="mobile-navigation__header">
        <span class="brand-mark" aria-hidden="true">V</span>
        <div><strong>虚空系统</strong><small>个人工作区</small></div>
      </div>
      <nav class="mobile-navigation__links" aria-label="移动端导航">
        <RouterLink v-for="item in workspaceNavigation" :key="item.to" :to="item.to" @click="mobileNavOpen = false">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
        <p class="mobile-navigation__label">智能协作</p>
        <RouterLink v-for="item in assistantNavigation" :key="item.to" :to="item.to" @click="mobileNavOpen = false">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/rag" @click="mobileNavOpen = false">
          <el-icon><Files /></el-icon>
          <span>共享馆藏管理</span>
        </RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/ai" @click="mobileNavOpen = false">
          <el-icon><Cpu /></el-icon>
          <span>AI 服务</span>
        </RouterLink>
      </nav>
      <button v-if="isAuthenticated" class="mobile-account" type="button" @click="openSettings">
        <span class="account-avatar">{{ userAvatar }}</span>
        <span><strong>{{ userName }}</strong><small>账号与偏好</small></span>
        <el-icon><ArrowRight /></el-icon>
      </button>
    </el-drawer>

    <main class="main" :class="{ 'main--fullbleed': route.meta.fullBleed, 'main--public': !isWorkspaceRoute }">
      <div :class="route.meta.fullBleed ? 'main-inner--fullbleed' : 'container'">
        <RouterView />
      </div>
    </main>
    <BackgroundProgressDrawer v-if="isAuthenticated" v-model="backgroundProgressOpen" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  Clock,
  Collection,
  Compass,
  Document,
  Files,
  House,
  List,
  Menu,
  MoreFilled,
  Setting,
  SwitchButton,
  TrendCharts,
  User
} from '@element-plus/icons-vue'
import { authState, logout as logoutApi } from '@/api/user'
import BackgroundProgressDrawer from '@/components/BackgroundProgressDrawer.vue'
import { useBackgroundProgressStore } from '@/stores/backgroundProgress'

const router = useRouter()
const route = useRoute()
const mobileNavOpen = ref(false)
const backgroundProgressOpen = ref(false)
const backgroundProgress = useBackgroundProgressStore()
const workspaceNavigation = [
  { to: '/', label: '工作台', icon: House },
  { to: '/tasks', label: '行动', icon: List },
  { to: '/documents', label: '资料馆', icon: Document },
  { to: '/growth', label: '成长', icon: TrendCharts }
]

const assistantNavigation = [
  { to: '/companion', label: '系统精灵', icon: Compass },
  { to: '/ai', label: '对话', icon: ChatDotRound },
  { to: '/qa', label: '知识问答', icon: Collection }
]
const isWorkspaceRoute = computed(() => route.meta.requiresAuth !== false)
const isAuthenticated = computed(() => authState.isLoggedIn)
const userName = computed(() => {
  const info = authState.userInfo
  return info?.username || info?.user?.username || info?.userName || '用户'
})
const userAvatar = computed(() => userName.value.trim().charAt(0).toUpperCase() || 'V')
const isAdmin = computed(() => {
  const info = authState.userInfo
  return info?.user?.role === 'admin' || info?.role === 'admin'
})

async function handleAccountCommand(command) {
  if (command === 'profile') return router.push('/profile')
  if (command === 'settings') return router.push('/settings')
  if (command === 'logout') {
    try { await logoutApi() } catch { /* The API client clears local state as a fallback. */ }
    router.push('/login')
  }
}

function openSettings() {
  mobileNavOpen.value = false
  router.push('/settings')
}

/**
 * Tie global background recovery to the authenticated application lifecycle.
 * Input: Reactive authentication state maintained by the shared API client.
 * Output: Starts one owner-scoped recovery/polling loop after login and stops it after logout.
 * Called by: This root application shell for initial load and subsequent auth changes.
 * Side effects: Reads recent durable work and clears transient state when the user session ends.
 * Failure: Initial recovery stays non-blocking because individual pages remain usable while the progress center retries.
 * Invariant: Polling is never kept alive for a logged-out user or restored from another user's browser state.
 */
watch(isAuthenticated, (authenticated) => {
  if (authenticated) backgroundProgress.start().catch(() => {})
  else {
    backgroundProgressOpen.value = false
    backgroundProgress.stop()
  }
}, { immediate: true })

onMounted(() => {
  try {
    const saved = JSON.parse(localStorage.getItem('settings_cache') || '{}')
    document.documentElement.setAttribute('data-theme', saved?.preferences?.themeMode || 'light')
  } catch {
    document.documentElement.setAttribute('data-theme', 'light')
  }
})

onUnmounted(() => {
  backgroundProgress.stop()
})
</script>

<style scoped>
.app-shell { min-height: 100vh; background: var(--bg-primary); }
.app-shell--workspace { display: grid; grid-template-columns: 256px minmax(0, 1fr); }
.workspace-sidebar { position: sticky; top: 0; display: flex; flex-direction: column; width: 256px; height: 100vh; padding: 26px 16px 16px; border-right: 1px solid var(--border-color-light); background: color-mix(in srgb, var(--bg-secondary) 92%, var(--bg-primary)); }
.brand { display: inline-flex; align-items: center; gap: 11px; width: fit-content; border: 0; padding: 0 8px; color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.brand-mark { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid color-mix(in srgb, var(--color-primary) 30%, transparent); border-radius: 9px; color: #fff; background: var(--color-primary); font-size: 14px; font-weight: 800; box-shadow: 0 8px 18px color-mix(in srgb, var(--color-primary) 18%, transparent); }
.brand-copy { display: grid; gap: 2px; line-height: 1.15; }
.brand-copy strong { font-size: 15px; letter-spacing: .01em; }
.brand-copy small { color: var(--text-muted); font-size: 11px; }
.workspace-nav { display: grid; align-content: start; gap: 4px; margin-top: 38px; }
.nav-label { margin: 0 12px 8px; color: var(--text-muted); font-size: 10px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.nav-label--secondary { margin-top: 24px; }
.workspace-nav__item { display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 0 12px; border: 1px solid transparent; border-radius: 8px; color: var(--text-secondary); font-size: 14px; text-decoration: none; transition: color .16s ease, background .16s ease, border-color .16s ease, transform .16s ease; }
.workspace-nav__item:hover { color: var(--text-primary); background: var(--bg-tertiary); transform: translateX(2px); }
.workspace-nav__item.router-link-exact-active { border-color: color-mix(in srgb, var(--color-primary) 22%, var(--border-color)); color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 9%, var(--bg-secondary)); font-weight: 750; }
.workspace-nav__item .el-icon { width: 18px; color: currentColor; font-size: 17px; }
.background-progress-trigger { display: flex; align-items: center; gap: 10px; width: 100%; min-height: 42px; margin-top: auto; border: 1px solid transparent; border-radius: 8px; padding: 0 12px; color: var(--text-secondary); background: transparent; cursor: pointer; font-size: 13px; font-weight: 700; text-align: left; }
.background-progress-trigger:hover { border-color: var(--border-color-light); color: var(--text-primary); background: var(--bg-tertiary); }
.background-progress-trigger .el-icon { font-size: 17px; }
.background-progress-trigger__count { display: grid; min-width: 19px; height: 19px; place-items: center; margin-left: auto; border-radius: 999px; color: #fff; background: var(--color-primary); font-size: 10px; font-weight: 800; }
.sidebar-account { padding-top: 14px; border-top: 1px solid var(--border-color-light); }
.account-trigger, .mobile-account { display: flex; align-items: center; gap: 10px; width: 100%; border: 1px solid transparent; border-radius: 8px; padding: 8px; color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.account-trigger:hover, .mobile-account:hover { border-color: var(--border-color-light); background: var(--bg-tertiary); }
.account-avatar { display: grid; place-items: center; flex: 0 0 auto; width: 32px; height: 32px; border: 1px solid color-mix(in srgb, var(--color-primary) 22%, var(--border-color)); border-radius: 50%; color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 12%, var(--bg-secondary)); font-size: 12px; font-weight: 800; }
.account-copy, .mobile-account > span:nth-child(2) { display: grid; gap: 2px; min-width: 0; }
.account-copy strong, .mobile-account strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.account-copy small, .mobile-account small { color: var(--text-muted); font-size: 11px; }
.account-caret { margin-left: auto; color: var(--text-muted); }
.main { min-width: 0; min-height: 100vh; background: linear-gradient(180deg, color-mix(in srgb, var(--bg-secondary) 34%, transparent), transparent 220px); }
.main--fullbleed { width: 100%; }
.main-inner--fullbleed { width: 100%; }
.mobile-header { display: none; }
.mobile-header__actions { display: flex; align-items: center; gap: 2px; }
.public-header { display: flex; align-items: center; justify-content: space-between; min-height: 68px; padding: 0 clamp(16px, 4vw, 38px); border-bottom: 1px solid var(--border-color-light); background: var(--bg-secondary); }
.public-header .brand { padding-left: 0; }
.public-header__actions { display: flex; align-items: center; gap: 6px; }
.mobile-navigation__header { display: flex; align-items: center; gap: 10px; padding: 4px 0 21px; border-bottom: 1px solid var(--border-color); }
.mobile-navigation__header > div { display: grid; gap: 2px; }
.mobile-navigation__header strong { font-size: 15px; }
.mobile-navigation__header small { color: var(--text-muted); font-size: 11px; }
.mobile-navigation__links { display: grid; gap: 4px; padding: 18px 0; }
.mobile-navigation__label { margin: 14px 12px 4px; color: var(--text-muted); font-size: 10px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.mobile-navigation__links a { display: flex; align-items: center; gap: 12px; min-height: 46px; padding: 0 12px; border-radius: 8px; color: var(--text-secondary); text-decoration: none; font-size: 14px; }
.mobile-navigation__links a.router-link-exact-active { color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 10%, var(--bg-secondary)); font-weight: 750; }
.mobile-account { margin-top: auto; }
.mobile-account > .el-icon { margin-left: auto; color: var(--text-muted); }
@media (max-width: 900px) { .app-shell--workspace { display: block; } .workspace-sidebar { display: none; } .mobile-header { position: sticky; top: 0; z-index: 20; display: flex; align-items: center; justify-content: space-between; min-height: 62px; padding: 0 16px; border-bottom: 1px solid var(--border-color); background: color-mix(in srgb, var(--bg-primary) 94%, transparent); backdrop-filter: blur(14px); } .mobile-header .brand { padding-left: 0; } .main { min-height: calc(100vh - 62px); } }
@media (min-width: 901px) { .app-shell--workspace .main { grid-column: 2; } }
@media (max-width: 520px) { .brand-copy small { display: none; } .public-header__actions .el-button:first-child { display: none; } }
</style>
