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
            <span>共享知识维护</span>
          </RouterLink>
          <RouterLink to="/admin/ai" class="workspace-nav__item">
            <el-icon><Cpu /></el-icon>
            <span>AI 服务</span>
          </RouterLink>
        </template>
      </nav>

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
      <el-button text circle aria-label="打开导航" @click="mobileNavOpen = true"><el-icon><Menu /></el-icon></el-button>
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
          <span>共享知识维护</span>
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  Collection,
  Document,
  Files,
  House,
  List,
  MagicStick,
  Menu,
  MoreFilled,
  Setting,
  SwitchButton,
  TrendCharts,
  User
} from '@element-plus/icons-vue'
import { authState, logout as logoutApi } from '@/api/user'

const router = useRouter()
const route = useRoute()
const mobileNavOpen = ref(false)
const workspaceNavigation = [
  { to: '/', label: '工作台', icon: House },
  { to: '/tasks', label: '行动', icon: List },
  { to: '/documents', label: '资料库', icon: Document },
  { to: '/growth', label: '成长', icon: TrendCharts }
]

const assistantNavigation = [
  { to: '/ai', label: '对话', icon: ChatDotRound },
  { to: '/advisor', label: '行动规划', icon: MagicStick },
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

onMounted(() => {
  try {
    const saved = JSON.parse(localStorage.getItem('settings_cache') || '{}')
    document.documentElement.setAttribute('data-theme', saved?.preferences?.themeMode || 'light')
  } catch {
    document.documentElement.setAttribute('data-theme', 'light')
  }
})
</script>

<style scoped>
.app-shell { min-height: 100vh; background: var(--bg-primary); }
.app-shell--workspace { display: grid; grid-template-columns: 244px minmax(0, 1fr); }
.workspace-sidebar { position: sticky; top: 0; display: flex; flex-direction: column; width: 244px; height: 100vh; padding: 22px 14px 14px; border-right: 1px solid var(--border-color); background: var(--bg-secondary); }
.brand { display: inline-flex; align-items: center; gap: 10px; width: fit-content; border: 0; padding: 0 8px; color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.brand-mark { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 7px; color: #fff; background: var(--color-primary); font-size: 14px; font-weight: 800; box-shadow: 0 4px 12px color-mix(in srgb, var(--color-primary) 22%, transparent); }
.brand-copy { display: grid; gap: 1px; line-height: 1.15; }
.brand-copy strong { font-size: 15px; letter-spacing: 0; }
.brand-copy small { color: var(--text-muted); font-size: 11px; }
.workspace-nav { display: grid; align-content: start; gap: 3px; margin-top: 34px; }
.nav-label { margin: 0 10px 7px; color: var(--text-muted); font-size: 11px; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }
.nav-label--secondary { margin-top: 20px; }
.workspace-nav__item { display: flex; align-items: center; gap: 11px; min-height: 42px; padding: 0 10px; border: 1px solid transparent; border-radius: 7px; color: var(--text-secondary); font-size: 14px; text-decoration: none; transition: color .16s ease, background .16s ease, border-color .16s ease; }
.workspace-nav__item:hover { color: var(--text-primary); background: var(--bg-tertiary); }
.workspace-nav__item.router-link-exact-active { border-color: color-mix(in srgb, var(--color-primary) 22%, var(--border-color)); color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 9%, var(--bg-secondary)); font-weight: 700; }
.workspace-nav__item .el-icon { font-size: 17px; }
.sidebar-account { margin-top: auto; padding-top: 12px; border-top: 1px solid var(--border-color-light); }
.account-trigger, .mobile-account { display: flex; align-items: center; gap: 9px; width: 100%; border: 1px solid transparent; border-radius: 7px; padding: 7px; color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.account-trigger:hover, .mobile-account:hover { border-color: var(--border-color-light); background: var(--bg-tertiary); }
.account-avatar { display: grid; place-items: center; flex: 0 0 auto; width: 30px; height: 30px; border-radius: 50%; color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 15%, var(--bg-secondary)); font-size: 12px; font-weight: 800; }
.account-copy, .mobile-account > span:nth-child(2) { display: grid; gap: 1px; min-width: 0; }
.account-copy strong, .mobile-account strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.account-copy small, .mobile-account small { color: var(--text-muted); font-size: 11px; }
.account-caret { margin-left: auto; color: var(--text-muted); }
.main { min-width: 0; min-height: 100vh; }
.main--fullbleed { width: 100%; }
.main-inner--fullbleed { width: 100%; }
.mobile-header { display: none; }
.public-header { display: flex; align-items: center; justify-content: space-between; min-height: 62px; padding: 0 clamp(14px, 4vw, 28px); border-bottom: 1px solid var(--border-color-light); }
.public-header .brand { padding-left: 0; }
.public-header__actions { display: flex; align-items: center; gap: 4px; }
.mobile-navigation__header { display: flex; align-items: center; gap: 10px; padding: 4px 0 21px; border-bottom: 1px solid var(--border-color); }
.mobile-navigation__header > div { display: grid; gap: 1px; }
.mobile-navigation__header strong { font-size: 15px; }
.mobile-navigation__header small { color: var(--text-muted); font-size: 11px; }
.mobile-navigation__links { display: grid; gap: 4px; padding: 18px 0; }.mobile-navigation__label { margin: 14px 12px 4px; color: var(--text-muted); font-size: 11px; font-weight: 700; }
.mobile-navigation__links a { display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 0 12px; border-radius: 7px; color: var(--text-secondary); text-decoration: none; font-size: 14px; }
.mobile-navigation__links a.router-link-exact-active { color: var(--color-primary-dark); background: color-mix(in srgb, var(--color-primary) 10%, var(--bg-secondary)); font-weight: 700; }
.mobile-account { margin-top: auto; }
.mobile-account > .el-icon { margin-left: auto; color: var(--text-muted); }
@media (max-width: 900px) { .app-shell--workspace { display: block; } .workspace-sidebar { display: none; } .mobile-header { position: sticky; top: 0; z-index: 20; display: flex; align-items: center; justify-content: space-between; min-height: 60px; padding: 0 14px; border-bottom: 1px solid var(--border-color); background: color-mix(in srgb, var(--bg-primary) 94%, transparent); backdrop-filter: blur(14px); } .mobile-header .brand { padding-left: 0; } .main { min-height: calc(100vh - 60px); } }
@media (min-width: 901px) { .app-shell--workspace .main { grid-column: 2; } }

@media (max-width: 520px) { .brand-copy small { display: none; } .public-header__actions .el-button:first-child { display: none; } }
</style>
