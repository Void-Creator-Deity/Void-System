<template>
  <div class="settings-container">
    <!-- 页面标题 -->
    <div class="settings-header">
      <h2><span class="glitch">系统</span> <span class="system-text">设置</span></h2>
      <p class="subtitle">配置您的虚空学习系统参数</p>
    </div>
    
    <!-- 设置标签页导航 -->
    <el-tabs v-model="activeTab" class="settings-tabs">

      
      <el-tab-pane label="系统配置" name="config">
        <!-- 系统配置卡片 -->
        <div class="settings-card system-config">
          <div class="config-content">
            <div class="config-group">
              <div class="config-header">
                <h4>AI 助手设置</h4>
                <el-switch v-model="systemConfig.aiAssistantEnabled" />
              </div>
              
              <div class="config-details" v-if="systemConfig.aiAssistantEnabled">
                <p class="settings-tip">这些参数会影响 AI 任务建议生成（提示词上下文）。</p>
                <div class="detail-group">
                  <label>回复风格</label>
                  <el-radio-group v-model="systemConfig.responseStyle">
                    <el-radio-button label="专业">专业</el-radio-button>
                    <el-radio-button label="友好">友好</el-radio-button>
                    <el-radio-button label="详细">详细</el-radio-button>
                  </el-radio-group>
                </div>
                
                <div class="detail-group">
                  <label>温度系数（任务建议）</label>
                  <el-slider
                    v-model="systemConfig.aiTemperature"
                    :min="0"
                    :max="100"
                    :marks="{ 0: '稳定', 35: '均衡', 70: '发散', 100: '创意' }"
                  />
                </div>
              </div>
            </div>
            
            <div class="config-group">
              <div class="config-header">
                <h4><el-icon><Monitor /></el-icon> 界面主题</h4>
              </div>
              
              <div class="config-details">
                <div class="detail-group">
                  <label>主题预设</label>
                  <div class="theme-choices">
                    <div 
                      class="theme-card dark" 
                      :class="{ active: systemConfig.themeMode === 'dark' }"
                      @click="systemConfig.themeMode = 'dark'"
                    >
                      <div class="preview-box">
                        <div class="line"></div>
                        <div class="line short"></div>
                      </div>
                      <span>骇客深邃 (Dark)</span>
                    </div>
                    
                    <div 
                      class="theme-card light" 
                      :class="{ active: systemConfig.themeMode === 'light' }"
                      @click="systemConfig.themeMode = 'light'"
                    >
                      <div class="preview-box">
                        <div class="line"></div>
                        <div class="line short"></div>
                      </div>
                      <span>双子光辉 (Light)</span>
                    </div>
                  </div>
                </div>
                
              </div>
            </div>

            <div class="config-group">
              <div class="config-header">
                <h4>AI 连接配置（管理员）</h4>
              </div>
              <div class="config-details">
                <p class="settings-tip">保存后将通过 API 写入后端运行配置，并可同步到 .env。</p>
                <div class="detail-group detail-group--section">
                  <label>LLM 模型配置</label>
                </div>
                <div class="detail-group">
                  <label>LLM 提供商</label>
                  <el-select v-model="aiRuntimeConfig.llm_provider" placeholder="选择或输入提供商" filterable allow-create default-first-option>
                    <el-option v-for="p in providerOptions" :key="p" :label="p" :value="p" />
                  </el-select>
                </div>
                <div class="detail-group">
                  <label>聊天模型</label>
                  <el-select v-model="aiRuntimeConfig.chat_model" placeholder="选择或输入模型名" filterable allow-create default-first-option>
                    <el-option v-for="m in chatModelOptions" :key="m" :label="m" :value="m" />
                  </el-select>
                </div>
                <div class="detail-group">
                  <label>Ollama Base URL</label>
                  <el-input v-model="aiRuntimeConfig.ollama_base_url" placeholder="http://localhost:11434" />
                </div>
                <div class="detail-group detail-group--section">
                  <label>Embedding 模型配置</label>
                </div>
                <div class="detail-group">
                  <label>Embedding 提供商</label>
                  <el-select v-model="aiRuntimeConfig.embedding_provider" placeholder="选择或输入嵌入提供商" filterable allow-create default-first-option>
                    <el-option v-for="p in providerOptions" :key="`emb-${p}`" :label="p" :value="p" />
                  </el-select>
                </div>
                <div class="detail-group">
                  <label>Embedding 模型</label>
                  <el-select v-model="aiRuntimeConfig.embedding_model" placeholder="选择或输入 Embedding 模型名" filterable allow-create default-first-option>
                    <el-option v-for="m in embeddingModelOptions" :key="`emb-${m}`" :label="m" :value="m" />
                  </el-select>
                </div>
                <div v-if="showEmbeddingOpenAICompatFields" class="detail-group">
                  <label>Embedding OpenAI Base URL（必填）</label>
                  <el-input v-model="aiRuntimeConfig.openai_base_url" placeholder="https://api.openai.com/v1" />
                </div>
                <div v-if="showEmbeddingOpenAICompatFields" class="detail-group">
                  <label>Embedding API Key（必填）</label>
                  <el-input v-model="aiRuntimeConfig.openai_api_key" type="password" show-password placeholder="请输入 API Key（与上方可共用）" />
                </div>
                <div v-if="showOpenAICompatFields" class="detail-group">
                  <label>OpenAI Base URL（必填）</label>
                  <el-input v-model="aiRuntimeConfig.openai_base_url" placeholder="https://api.openai.com/v1" />
                </div>
                <div v-if="showOpenAICompatFields" class="detail-group">
                  <label>OpenAI / DeepSeek API Key（必填）</label>
                  <el-input v-model="aiRuntimeConfig.openai_api_key" type="password" show-password placeholder="请输入 API Key（或先在后端已配置）" />
                </div>
                <div v-if="showGeminiFields" class="detail-group">
                  <label>Gemini API Key（必填）</label>
                  <el-input v-model="aiRuntimeConfig.google_api_key" type="password" show-password placeholder="请输入 Gemini API Key（或先在后端已配置）" />
                </div>
                <div class="detail-group">
                  <el-checkbox v-model="aiRuntimeConfig.persist_to_env">写入 .env（重启后仍生效）</el-checkbox>
                  <el-checkbox v-model="aiRuntimeConfig.apply_runtime">立即应用到当前进程</el-checkbox>
                </div>
                <div class="detail-group">
                  <label>额外环境变量（可扩展新厂商）</label>
                  <div class="extra-env-list">
                    <div v-for="(row, idx) in extraEnvRows" :key="`extra-${idx}`" class="extra-env-row">
                      <el-input v-model="row.key" placeholder="KEY（大写下划线）" />
                      <el-input v-model="row.value" placeholder="VALUE" />
                      <el-button @click="removeExtraEnvRow(idx)">删除</el-button>
                    </div>
                    <el-button @click="addExtraEnvRow">新增变量</el-button>
                  </div>
                </div>
                <div class="detail-group">
                  <label>当前 .env（已存在项）</label>
                  <div class="env-table">
                    <div class="env-row env-row--head"><span>键</span><span>值</span></div>
                    <div v-for="row in aiEnvEntries" :key="row.key" class="env-row">
                      <span>{{ row.key }}</span>
                      <span>{{ row.value }}</span>
                    </div>
                    <div v-if="!aiEnvEntries.length" class="env-row">
                      <span>暂无配置</span>
                      <span>-</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="card-actions">
                <el-button @click="loadAiRuntimeConfig" :loading="loading.aiConfig">刷新配置</el-button>
                <el-button @click="testAiRuntimeConfig" :loading="loading.aiConfig">测试连接</el-button>
                <el-button type="primary" @click="saveAiRuntimeConfig" :loading="loading.aiConfig">保存AI配置</el-button>
              </div>
            </div>
          </div>
          
          <div class="card-actions">
            <el-button type="primary" @click="saveSystemConfig" :loading="loading.config">应用设置</el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="系统信息" name="info">
        <!-- 系统信息卡片 -->
        <div class="settings-card system-info">
          <div class="info-content">
            <div class="info-item">
              <span class="info-label">系统版本</span>
              <span class="info-value">{{ systemInfo.version }}</span>
            </div>
            
            <div class="info-item">
              <span class="info-label">AI 模型</span>
              <span class="info-value">{{ systemInfo.aiModel }}</span>
            </div>
            
            <div class="info-item">
              <span class="info-label">向量存储</span>
              <span class="info-value">{{ systemInfo.vectorStore }}</span>
            </div>
            
            <div class="info-item">
              <span class="info-label">运行时间</span>
              <span class="info-value">{{ systemInfo.uptime }}</span>
            </div>
            
            <div class="info-item">
              <span class="info-label">后端状态</span>
              <span class="info-value" :class="{ 'status-online': systemInfo.status === 'online', 'status-offline': systemInfo.status === 'offline' }">
                {{ systemInfo.status === 'online' ? '在线' : '离线' }}
              </span>
            </div>
          </div>
          
          <div class="card-actions">
            <el-button @click="checkForUpdates" :loading="loading.update">检查更新</el-button>
            <el-button type="warning" plain @click="clearCache" :loading="loading.clearCache">清除缓存</el-button>
            <el-button type="danger" plain @click="confirmLogout">退出登录</el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
    
  </div>
</template>

<script setup>
/**
 * Settings Component
 * ------------------
 * 系统设置页面，包含用户信息、系统配置、学习偏好等设置选项
 */

import { ref, reactive, onMounted, onBeforeUnmount, watch, computed } from "vue"
import { useRouter, useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from 'element-plus'
import { logout as logoutApi } from '../api/user.js'
import api from '../api/index'

const router = useRouter()
const route = useRoute()

// ==================== 响应式状态 ====================
const activeTab = ref(route.query.tab || 'config')

// 监听路由变化，如果在页面内直接切换路由参数则自动跳标签
watch(() => route.query.tab, (newTab) => {
  if (newTab) {
    activeTab.value = newTab
  }
})
const loading = reactive({
  profile: false,
  config: false,
  aiConfig: false,
  update: false,
  clearCache: false
})
// ==================== 数据模型 ====================

// 系统配置
const systemConfig = reactive({
  aiAssistantEnabled: true,
  responseStyle: "专业",
  aiTemperature: 35,
  themeMode: "dark"
})

const aiRuntimeConfig = reactive({
  llm_provider: "ollama",
  embedding_provider: "ollama",
  ollama_base_url: "http://localhost:11434",
  chat_model: "",
  embedding_model: "",
  openai_base_url: "",
  openai_api_key: "",
  google_api_key: "",
  persist_to_env: true,
  apply_runtime: true
})
const providerOptions = ref(['ollama', 'openai', 'deepseek', 'gemini', 'openai_compat'])
const chatModelOptions = ref([])
const embeddingModelOptions = ref([])
const aiEnvEntries = ref([])
const extraEnvRows = ref([])
const showOpenAICompatFields = computed(() => ['openai', 'openai_compat', 'deepseek'].includes(String(aiRuntimeConfig.llm_provider || '').toLowerCase()))
const showGeminiFields = computed(() => String(aiRuntimeConfig.llm_provider || '').toLowerCase() === 'gemini')
const showEmbeddingOpenAICompatFields = computed(() => ['openai', 'openai_compat', 'deepseek'].includes(String(aiRuntimeConfig.embedding_provider || '').toLowerCase()))

// 系统信息
const systemInfo = reactive({
  version: "1.0.0",
  aiModel: "Ollama LLM",
  vectorStore: "Chroma DB",
  uptime: "00:00:00",
  status: 'online'
})

// 确认对话框状态
const confirmLogoutVisible = ref(false)

// 已移除冗余的颜色选项

// ==================== 工具函数 ====================

// 系统运行时间相关
let startTime = new Date()
let uptimeInterval = null

/**
 * 更新系统运行时间
 */
const updateUptime = () => {
  const currentTime = new Date()
  const diff = Math.floor((currentTime - startTime) / 1000)
  
  const hours = Math.floor(diff / 3600).toString().padStart(2, '0')
  const minutes = Math.floor((diff % 3600) / 60).toString().padStart(2, '0')
  const seconds = (diff % 60).toString().padStart(2, '0')
  
  systemInfo.uptime = `${hours}:${minutes}:${seconds}`
}

// ==================== 业务逻辑 ====================

/**
 * 保存系统配置
 */
const saveSystemConfig = async () => {
  loading.config = true
  try {
    // TODO: 调用实际的 API
    // await api.updateSystemConfig(systemConfig)
    
    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用全局主题
    document.documentElement.setAttribute('data-theme', systemConfig.themeMode)
    
    // 保存到本地存储
    localStorage.setItem('settings_cache', JSON.stringify({
      systemConfig
    }))
    
    ElMessage.success('系统配置应用成功')
  } catch (error) {
    console.error('保存系统配置失败:', error)
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    loading.config = false
  }
}

const loadAiRuntimeConfig = async () => {
  loading.aiConfig = true
  try {
    const res = await api.get('/api/admin/system/ai-config')
    const data = res?.data?.data || {}
    aiRuntimeConfig.llm_provider = data.llm_provider || aiRuntimeConfig.llm_provider
    aiRuntimeConfig.embedding_provider = data.embedding_provider || aiRuntimeConfig.embedding_provider
    aiRuntimeConfig.ollama_base_url = data.ollama_base_url || aiRuntimeConfig.ollama_base_url
    aiRuntimeConfig.chat_model = data.chat_model || ''
    aiRuntimeConfig.embedding_model = data.embedding_model || ''
    aiRuntimeConfig.openai_base_url = data.openai_base_url || ''
    aiRuntimeConfig.openai_api_key = ''
    aiRuntimeConfig.google_api_key = ''
    aiEnvEntries.value = Array.isArray(data.env_entries) ? data.env_entries : []
    const modelOptions = Array.isArray(data.model_options) ? data.model_options : []
    chatModelOptions.value = Array.from(new Set([...(aiRuntimeConfig.chat_model ? [aiRuntimeConfig.chat_model] : []), ...modelOptions]))
    embeddingModelOptions.value = Array.from(new Set([...(aiRuntimeConfig.embedding_model ? [aiRuntimeConfig.embedding_model] : []), ...modelOptions]))
    if (aiRuntimeConfig.llm_provider && !providerOptions.value.includes(aiRuntimeConfig.llm_provider)) {
      providerOptions.value.push(aiRuntimeConfig.llm_provider)
    }
    if (aiRuntimeConfig.embedding_provider && !providerOptions.value.includes(aiRuntimeConfig.embedding_provider)) {
      providerOptions.value.push(aiRuntimeConfig.embedding_provider)
    }
    if (data.model_options_error) {
      ElMessage.warning(`模型列表读取失败：${data.model_options_error}`)
    }
  } catch (error) {
    if (error?.response?.status === 403) {
      ElMessage.warning('需要管理员权限才能读取 AI 连接配置')
    } else {
      ElMessage.error('读取 AI 配置失败')
    }
  } finally {
    loading.aiConfig = false
  }
}

const normalizeExtraEnv = () => {
  const out = {}
  for (const row of extraEnvRows.value) {
    const key = String(row?.key || '').trim().toUpperCase()
    const value = String(row?.value || '').trim()
    if (!key) continue
    if (!/^[A-Z_][A-Z0-9_]*$/.test(key)) continue
    out[key] = value
  }
  return out
}

const addExtraEnvRow = () => {
  extraEnvRows.value.push({ key: '', value: '' })
}

const removeExtraEnvRow = (idx) => {
  extraEnvRows.value.splice(idx, 1)
}

const saveAiRuntimeConfig = async () => {
  loading.aiConfig = true
  try {
    const provider = String(aiRuntimeConfig.llm_provider || '').toLowerCase()
    if (showOpenAICompatFields.value) {
      if (!String(aiRuntimeConfig.openai_base_url || '').trim()) {
        ElMessage.warning('当前厂商需要填写 OpenAI Base URL')
        return
      }
      if (!String(aiRuntimeConfig.openai_api_key || '').trim()) {
        ElMessage.warning('当前厂商需要填写 OpenAI / DeepSeek API Key')
        return
      }
    }
    if (showGeminiFields.value && !String(aiRuntimeConfig.google_api_key || '').trim()) {
      ElMessage.warning('当前厂商需要填写 Gemini API Key')
      return
    }
    if (showEmbeddingOpenAICompatFields.value) {
      if (!String(aiRuntimeConfig.openai_base_url || '').trim()) {
        ElMessage.warning('Embedding 提供商需要填写 OpenAI Base URL')
        return
      }
      if (!String(aiRuntimeConfig.openai_api_key || '').trim()) {
        ElMessage.warning('Embedding 提供商需要填写 API Key')
        return
      }
    }

    const payload = {
      llm_provider: provider || aiRuntimeConfig.llm_provider,
      embedding_provider: aiRuntimeConfig.embedding_provider,
      ollama_base_url: aiRuntimeConfig.ollama_base_url,
      chat_model: aiRuntimeConfig.chat_model,
      embedding_model: aiRuntimeConfig.embedding_model,
      openai_base_url: aiRuntimeConfig.openai_base_url,
      extra_env: normalizeExtraEnv(),
      persist_to_env: Boolean(aiRuntimeConfig.persist_to_env),
      apply_runtime: Boolean(aiRuntimeConfig.apply_runtime)
    }
    if (aiRuntimeConfig.openai_api_key?.trim()) payload.openai_api_key = aiRuntimeConfig.openai_api_key.trim()
    if (aiRuntimeConfig.google_api_key?.trim()) payload.google_api_key = aiRuntimeConfig.google_api_key.trim()
    await api.put('/api/admin/system/ai-config', payload)
    aiRuntimeConfig.openai_api_key = ''
    aiRuntimeConfig.google_api_key = ''
    ElMessage.success('AI 连接配置已更新')
    await loadAiRuntimeConfig()
  } catch (error) {
    if (error?.response?.status === 403) {
      ElMessage.warning('需要管理员权限才能修改 AI 连接配置')
    } else {
      ElMessage.error('保存 AI 配置失败')
    }
  } finally {
    loading.aiConfig = false
  }
}

const testAiRuntimeConfig = async () => {
  loading.aiConfig = true
  try {
    const payload = {
      llm_provider: aiRuntimeConfig.llm_provider,
      ollama_base_url: aiRuntimeConfig.ollama_base_url,
      chat_model: aiRuntimeConfig.chat_model,
      openai_base_url: aiRuntimeConfig.openai_base_url
    }
    if (aiRuntimeConfig.openai_api_key?.trim()) payload.openai_api_key = aiRuntimeConfig.openai_api_key.trim()
    if (aiRuntimeConfig.google_api_key?.trim()) payload.google_api_key = aiRuntimeConfig.google_api_key.trim()
    const res = await api.post('/api/admin/system/ai-config/test', payload)
    ElMessage.success(res?.data?.message || '连接测试通过')
  } catch (error) {
    const msg = error?.response?.data?.message || error?.response?.data?.detail || error?.message || '连接测试失败'
    ElMessage.error(msg)
  } finally {
    loading.aiConfig = false
  }
}

/**
 * 检查系统更新
 */
const checkForUpdates = async () => {
  loading.update = true
  try {
    // TODO: 调用实际的 API
    // const response = await api.checkUpdates()
    
    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('已是最新版本')
  } catch (error) {
    console.error('检查更新失败:', error)
    ElMessage.error('检查更新失败，请稍后重试')
  } finally {
    loading.update = false
  }
}

/**
 * 清除缓存
 */
const clearCache = async () => {
  loading.clearCache = true
  try {
    // 清除本地缓存
    localStorage.removeItem('settings_cache')
    sessionStorage.clear()
    
    // TODO: 调用实际的 API（如果需要）
    // await api.clearServerCache()
    
    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('缓存清除成功')
  } catch (error) {
    console.error('清除缓存失败:', error)
    ElMessage.error('清除缓存失败，请稍后重试')
  } finally {
    loading.clearCache = false
  }
}

/**
 * 确认退出登录（显示确认对话框）
 */
const confirmLogout = () => {
  ElMessageBox.confirm(
    '确定要退出当前登录吗？',
    '确认退出登录',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    logout()
  }).catch(() => {
    // 用户取消，不做任何操作
  })
}

/**
 * 退出登录
 */
const logout = async () => {
  try {
    // 调用后端 logout API
    await logoutApi()
    
    // 清除本地存储
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    localStorage.removeItem('persona_session_id')
    
    // 跳转到登录页
    router.push('/login')
    
    ElMessage.success('已成功退出登录')
  } catch (error) {
    console.error('退出登录失败:', error)
    // 即使 API 调用失败，仍然清除本地信息并跳转
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    localStorage.removeItem('persona_session_id')
    router.push('/login')
  }
}

/**
 * 加载系统设置
 */
const loadSettings = () => {
  const savedSettings = localStorage.getItem('settings_cache')
  if (savedSettings) {
    try {
      const parsedSettings = JSON.parse(savedSettings)
      if (parsedSettings.systemConfig) {
        Object.assign(systemConfig, parsedSettings.systemConfig)
      }
      systemConfig.aiTemperature = Number.isFinite(Number(systemConfig.aiTemperature)) ? Math.min(100, Math.max(0, Number(systemConfig.aiTemperature))) : 35
    } catch (e) {
      console.error('解析保存的设置失败:', e)
    }
  }
}

/**
 * 清理资源（清除定时器）
 */
const cleanup = () => {
  if (uptimeInterval) {
    clearInterval(uptimeInterval)
    uptimeInterval = null
  }
}

// ==================== 生命周期 ====================

// 组件挂载时
onMounted(() => {
  // 加载系统设置
  loadSettings()
  loadAiRuntimeConfig()
  
  // 启动运行时间更新定时器
  updateUptime()
  uptimeInterval = setInterval(updateUptime, 1000)
  
  // 初始化主题（从配置同步）
  document.documentElement.setAttribute('data-theme', systemConfig.themeMode)
})

// 组件卸载前清理资源
onBeforeUnmount(() => {
  cleanup()
})
</script>

<style scoped>
.settings-container {
  max-width: 1080px;
  margin: 0 auto;
  padding: 24px;
  color: var(--text-primary);
}

.settings-header {
  margin-bottom: 20px;
  padding: 20px 24px;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-glass);
  box-shadow: var(--shadow-sm);
}

.settings-header h2 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.2;
}

.glitch {
  color: var(--color-primary);
}

.system-text {
  color: var(--text-primary);
}

.subtitle {
  margin: 0;
  color: var(--text-secondary);
}

.settings-tabs {
  border-radius: 16px;
}

.settings-tabs :deep(.el-tabs__header) {
  margin: 0 0 16px;
}

.settings-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.settings-tabs :deep(.el-tabs__nav) {
  padding: 6px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-secondary);
}

.settings-tabs :deep(.el-tabs__item) {
  height: 38px;
  color: var(--text-secondary);
  font-weight: 600;
}

.settings-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
}

.settings-tabs :deep(.el-tabs__active-bar) {
  background: var(--color-primary);
  height: 2px;
}

.settings-card {
  padding: 20px;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: var(--bg-glass);
  box-shadow: var(--shadow-sm);
}

.config-group {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid var(--border-color-light);
  border-radius: 12px;
  background: var(--bg-secondary);
}

.config-group:last-child {
  margin-bottom: 0;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.config-header h4 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 700;
}

.config-details {
  padding-left: 12px;
  border-left: 2px solid var(--border-color-light);
}

.detail-group {
  margin-bottom: 14px;
}

.detail-group:last-child {
  margin-bottom: 0;
}

.detail-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.settings-tip {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.detail-group--section {
  margin-top: 8px;
}

.detail-group--section label {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
}

.extra-env-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.extra-env-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
}

.env-table {
  border: 1px solid var(--border-color-light);
  border-radius: 8px;
  overflow: hidden;
}

.env-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 8px;
  padding: 8px 10px;
  border-top: 1px solid var(--border-color-light);
  font-size: 12px;
}

.env-row:first-child {
  border-top: none;
}

.env-row--head {
  font-weight: 700;
  background: var(--bg-secondary);
}

.theme-choices {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.theme-card {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-tertiary);
  cursor: pointer;
  transition: border-color .2s ease, transform .2s ease, box-shadow .2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.theme-card:hover {
  transform: translateY(-1px);
  border-color: var(--color-primary);
}

.theme-card.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 25%, transparent);
}

.theme-card .preview-box {
  width: 100%;
  height: 56px;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.theme-card.dark .preview-box {
  background: #1f2430;
}

.theme-card.light .preview-box {
  background: #ffffff;
  border: 1px solid #d9dde8;
}

.preview-box .line {
  height: 6px;
  border-radius: 6px;
  background: rgba(120, 126, 140, 0.35);
}

.preview-box .line.short {
  width: 62%;
}

.theme-card span {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.info-content {
  display: grid;
  gap: 10px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-color-light);
  border-radius: 10px;
  background: var(--bg-secondary);
}

.info-label {
  color: var(--text-secondary);
  font-size: 14px;
}

.info-value {
  color: var(--text-primary);
  font-weight: 600;
}

.status-online {
  color: var(--color-success);
}

.status-offline {
  color: var(--color-error);
}

.card-actions {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border-color-light);
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.card-actions :deep(.el-button) {
  min-width: 108px;
}

:deep(.el-switch) {
  --el-switch-on-color: var(--color-primary);
  --el-switch-off-color: var(--border-color);
}

:deep(.el-radio-button__inner) {
  border-color: var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

:deep(.el-checkbox__label),
:deep(.el-radio__label) {
  color: var(--text-secondary);
}

:deep(.el-slider__runway) {
  background: var(--border-color-light);
}

:deep(.el-slider__bar) {
  background: var(--color-primary);
}

:deep(.el-slider__button) {
  border-color: var(--color-primary);
}

@media (max-width: 900px) {
  .settings-container {
    padding: 16px;
  }

  .settings-header {
    padding: 16px;
  }

  .settings-header h2 {
    font-size: 24px;
  }

  .settings-card {
    padding: 14px;
  }

  .config-group {
    padding: 12px;
  }

  .theme-choices {
    grid-template-columns: 1fr;
  }

  .card-actions {
    justify-content: stretch;
  }

  .card-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }

  .info-item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
