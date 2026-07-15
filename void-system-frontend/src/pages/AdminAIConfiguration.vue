<template>
  <div class="admin-ai-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">管理员</p>
        <h1>AI 服务</h1>
        <p>维护工作台使用的模型连接。这里的更改会影响新发起的请求。</p>
      </div>
      <span class="admin-badge">仅管理员</span>
    </header>

    <section class="config-section">
      <div class="section-heading">
        <div>
          <h2>对话服务</h2>
          <p>选择实际提供回答的模型服务。</p>
        </div>
      </div>

      <div class="provider-list" role="radiogroup" aria-label="选择模型服务">
        <button v-for="provider in providerOptions" :key="provider.value" type="button" class="provider-option" :class="{ selected: normalizedProvider === provider.value }" role="radio" :aria-checked="normalizedProvider === provider.value" @click="selectProvider(provider.value)">
          <el-icon><component :is="provider.icon" /></el-icon>
          <span><strong>{{ provider.title }}</strong><small>{{ provider.description }}</small></span>
          <el-icon v-if="normalizedProvider === provider.value" class="provider-check"><CircleCheck /></el-icon>
        </button>
      </div>

      <div class="connection-form">
        <label v-if="normalizedProvider === 'ollama'" class="form-field">
          <span>本地服务地址</span>
          <el-input v-model="aiConfig.ollama_base_url" placeholder="http://localhost:11434" />
          <small>模型运行在本机或局域网服务中。</small>
        </label>
        <label v-if="usesOpenAIProtocol" class="form-field">
          <span>{{ normalizedProvider === 'openai_compat' ? '服务地址' : '自定义服务地址（可选）' }}</span>
          <el-input v-model="aiConfig.openai_base_url" :placeholder="providerBasePlaceholder" />
          <small>{{ normalizedProvider === 'openai_compat' ? '需要填写完整的 OpenAI 兼容 API 地址。' : '留空时将使用官方默认地址。' }}</small>
        </label>
        <label v-if="usesOpenAIProtocol" class="form-field">
          <span>访问密钥</span>
          <el-input v-model="aiConfig.openai_api_key" type="password" show-password :placeholder="aiConfig.openai_api_key_set ? '已保存，留空表示不修改' : '输入 API Key'" autocomplete="new-password" />
          <small>{{ aiConfig.openai_api_key_set ? '已有密钥已安全保存。' : '密钥不会在页面中回显。' }}</small>
        </label>
        <label v-if="normalizedProvider === 'gemini'" class="form-field">
          <span>Gemini 访问密钥</span>
          <el-input v-model="aiConfig.google_api_key" type="password" show-password :placeholder="aiConfig.google_api_key_set ? '已保存，留空表示不修改' : '输入 API Key'" autocomplete="new-password" />
          <small>{{ aiConfig.google_api_key_set ? '已有密钥已安全保存。' : '密钥不会在页面中回显。' }}</small>
        </label>
        <label class="form-field">
          <span>对话模型</span>
          <el-select v-model="aiConfig.chat_model" filterable allow-create default-first-option placeholder="选择或输入模型名称">
            <el-option v-for="model in chatModelOptions" :key="model" :label="model" :value="model" />
          </el-select>
          <small>保存后，新发起的对话将使用这个模型。</small>
        </label>
      </div>

      <div class="action-row">
        <p>先测试连接，再保存并启用。</p>
        <div>
          <el-button :loading="loading.testing" @click="testAiConfig"><el-icon><Connection /></el-icon>测试连接</el-button>
          <el-button type="primary" :loading="loading.saving" @click="saveAiConfig"><el-icon><Check /></el-icon>保存并启用</el-button>
        </div>
      </div>
    </section>

    <section class="config-section">
      <div class="section-heading">
        <div>
          <h2>资料检索</h2>
          <p>选择用于整理和检索资料的模型，不会改变对话模型。</p>
        </div>
      </div>
      <div class="connection-form connection-form--two">
        <label class="form-field">
          <span>检索服务</span>
          <el-select v-model="aiConfig.embedding_provider">
            <el-option label="本地 Ollama" value="ollama" />
            <el-option label="OpenAI 兼容接口" value="openai" />
          </el-select>
        </label>
        <label class="form-field">
          <span>检索模型</span>
          <el-select v-model="aiConfig.embedding_model" filterable allow-create default-first-option placeholder="选择或输入模型名称">
            <el-option v-for="model in embeddingModelOptions" :key="model" :label="model" :value="model" />
          </el-select>
        </label>
      </div>
      <div class="save-secondary"><el-button :loading="loading.saving" @click="saveAiConfig"><el-icon><Check /></el-icon>保存检索设置</el-button></div>
    </section>

    <details class="runtime-details">
      <summary>运行方式 <el-icon><InfoFilled /></el-icon></summary>
      <p>用于控制这些修改何时生效。日常维护通常保持默认即可。</p>
      <div class="runtime-options">
        <label><span><strong>立即用于新请求</strong><small>保存后立即切换到新配置</small></span><el-switch v-model="aiConfig.apply_runtime" /></label>
        <label><span><strong>重启后保留</strong><small>将配置保存在本机服务环境中</small></span><el-switch v-model="aiConfig.persist_to_env" /></label>
      </div>
    </details>
  </div>
</template>

<script setup>
import { computed, markRaw, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, CircleCheck, Connection, Cpu, InfoFilled, Link, MagicStick, MoonNight } from '@element-plus/icons-vue'
import { getApiErrorMessage } from '../api/index'
import { aiConnectionApi } from '../api/administration.js'

const loading = reactive({ read: false, testing: false, saving: false })
const aiConfig = reactive({
  llm_provider: 'ollama', embedding_provider: 'ollama', ollama_base_url: 'http://localhost:11434', chat_model: '', embedding_model: '', openai_base_url: '', openai_api_key: '', google_api_key: '', openai_api_key_set: false, google_api_key_set: false, persist_to_env: true, apply_runtime: true
})
const chatModelOptions = ref([])
const embeddingModelOptions = ref([])
const providerOptions = [
  { value: 'ollama', title: '本地 Ollama', description: '当前设备或局域网模型服务', icon: markRaw(Cpu) },
  { value: 'deepseek', title: 'DeepSeek', description: '适合中文任务与推理', icon: markRaw(MagicStick) },
  { value: 'openai', title: 'OpenAI', description: '通用云端模型服务', icon: markRaw(Connection) },
  { value: 'gemini', title: 'Gemini', description: '长上下文与多模态服务', icon: markRaw(MoonNight) },
  { value: 'openai_compat', title: '兼容服务', description: '其他 OpenAI 协议服务', icon: markRaw(Link) }
]
const normalizedProvider = computed(() => String(aiConfig.llm_provider || 'ollama').toLowerCase())
const usesOpenAIProtocol = computed(() => ['openai', 'deepseek', 'openai_compat'].includes(normalizedProvider.value))
const providerBasePlaceholder = computed(() => {
  if (normalizedProvider.value === 'deepseek') return 'https://api.deepseek.com/v1（留空使用默认地址）'
  if (normalizedProvider.value === 'openai') return 'https://api.openai.com/v1（留空使用默认地址）'
  return 'https://example.com/v1'
})

const selectProvider = provider => {
  aiConfig.llm_provider = provider
  if (provider === 'ollama' && !aiConfig.ollama_base_url) aiConfig.ollama_base_url = 'http://localhost:11434'
}

const applyReadConfig = data => {
  Object.assign(aiConfig, {
    llm_provider: data.llm_provider || 'ollama', embedding_provider: data.embedding_provider || 'ollama', ollama_base_url: data.ollama_base_url || 'http://localhost:11434', chat_model: data.chat_model || '', embedding_model: data.embedding_model || '', openai_base_url: data.openai_base_url || '', openai_api_key: '', google_api_key: '', openai_api_key_set: Boolean(data.openai_api_key_set), google_api_key_set: Boolean(data.google_api_key_set)
  })
  const models = Array.isArray(data.model_options) ? data.model_options : []
  chatModelOptions.value = [...new Set([aiConfig.chat_model, ...models].filter(Boolean))]
  embeddingModelOptions.value = [...new Set([aiConfig.embedding_model, ...models].filter(Boolean))]
}

const loadAiConfig = async () => {
  loading.read = true
  try {
    applyReadConfig(await aiConnectionApi.read())
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'AI 服务配置读取失败'))
  } finally {
    loading.read = false
  }
}

const validateConnectionForm = () => {
  if (normalizedProvider.value === 'openai_compat' && !aiConfig.openai_base_url.trim()) return '兼容服务需要填写服务地址'
  if (usesOpenAIProtocol.value && !aiConfig.openai_api_key_set && !aiConfig.openai_api_key.trim()) return '请填写访问密钥'
  if (normalizedProvider.value === 'gemini' && !aiConfig.google_api_key_set && !aiConfig.google_api_key.trim()) return '请填写 Gemini 访问密钥'
  if (!aiConfig.chat_model.trim()) return '请选择或输入对话模型'
  if (!aiConfig.embedding_model.trim()) return '请选择或输入检索模型'
  return ''
}

const connectionPayload = includeRuntime => {
  const payload = { llm_provider: normalizedProvider.value, ollama_base_url: aiConfig.ollama_base_url, chat_model: aiConfig.chat_model, openai_base_url: aiConfig.openai_base_url }
  if (aiConfig.openai_api_key.trim()) payload.openai_api_key = aiConfig.openai_api_key.trim()
  if (aiConfig.google_api_key.trim()) payload.google_api_key = aiConfig.google_api_key.trim()
  if (includeRuntime) Object.assign(payload, { embedding_provider: aiConfig.embedding_provider, embedding_model: aiConfig.embedding_model, persist_to_env: Boolean(aiConfig.persist_to_env), apply_runtime: Boolean(aiConfig.apply_runtime) })
  return payload
}

const testAiConfig = async () => {
  const validation = validateConnectionForm()
  if (validation) return ElMessage.warning(validation)
  loading.testing = true
  try {
    const data = await aiConnectionApi.test(connectionPayload(false))
    ElMessage.success(data?.latency_ms ? `连接正常，响应约 ${data.latency_ms} ms` : '连接测试通过')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '连接测试失败'))
  } finally {
    loading.testing = false
  }
}

const saveAiConfig = async () => {
  const validation = validateConnectionForm()
  if (validation) return ElMessage.warning(validation)
  loading.saving = true
  try {
    await aiConnectionApi.update(connectionPayload(true))
    ElMessage.success('AI 服务设置已保存')
    await loadAiConfig()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'AI 服务设置保存失败'))
  } finally {
    loading.saving = false
  }
}

onMounted(loadAiConfig)
</script>

<style scoped>
.admin-ai-page { width:min(100%, 980px); margin:0 auto; padding:32px 0 64px; color:var(--text-primary); }.page-header { display:flex; align-items:flex-end; justify-content:space-between; gap:24px; padding:0 2px 25px; border-bottom:1px solid var(--border-color); }.page-kicker { margin:0 0 6px; color:var(--color-primary); font-size:12px; font-weight:700; }.page-header h1 { margin:0; font-size:28px; line-height:1.2; }.page-header p:not(.page-kicker) { margin:9px 0 0; color:var(--text-secondary); }.admin-badge { flex:0 0 auto; padding:5px 9px; border:1px solid color-mix(in srgb, var(--color-primary) 26%, var(--border-color)); border-radius:6px; color:var(--color-primary-dark); background:color-mix(in srgb, var(--color-primary) 8%, var(--bg-secondary)); font-size:12px; font-weight:700; }.config-section { padding:30px 2px; border-bottom:1px solid var(--border-color-light); }.section-heading h2 { margin:0; font-size:18px; }.section-heading p { margin:6px 0 0; color:var(--text-secondary); font-size:14px; line-height:1.55; }.provider-list { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin-top:22px; }.provider-option { position:relative; display:grid; align-content:start; gap:9px; min-height:122px; padding:13px; border:1px solid var(--border-color); border-radius:7px; color:var(--text-primary); background:var(--bg-secondary); text-align:left; cursor:pointer; transition:background .16s ease,border-color .16s ease; }.provider-option:hover { border-color:color-mix(in srgb, var(--color-primary) 42%, var(--border-color)); }.provider-option.selected { border-color:var(--color-primary); background:color-mix(in srgb, var(--color-primary) 7%, var(--bg-secondary)); }.provider-option > .el-icon:first-child { width:28px; height:28px; border-radius:6px; color:var(--color-primary-dark); background:color-mix(in srgb, var(--color-primary) 11%, var(--bg-primary)); }.provider-option span { display:grid; gap:4px; }.provider-option strong { font-size:13px; line-height:1.3; }.provider-option small { color:var(--text-muted); font-size:11px; line-height:1.4; }.provider-check { position:absolute; top:10px; right:9px; color:var(--color-primary); font-size:17px; }.connection-form { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; margin-top:24px; }.connection-form--two { margin-top:22px; }.form-field { display:grid; gap:8px; }.form-field > span { color:var(--text-secondary); font-size:14px; font-weight:700; }.form-field > small { color:var(--text-muted); font-size:12px; line-height:1.45; }.form-field :deep(.el-input__wrapper),.form-field :deep(.el-select__wrapper) { min-height:44px; border:1px solid var(--border-color); border-radius:7px; background:var(--bg-secondary); box-shadow:none; }.form-field :deep(.el-input__wrapper.is-focus),.form-field :deep(.el-select__wrapper.is-focused) { border-color:var(--color-primary); box-shadow:0 0 0 3px color-mix(in srgb, var(--color-primary) 13%, transparent); }.action-row { display:flex; align-items:center; justify-content:space-between; gap:18px; margin-top:26px; padding-top:20px; border-top:1px solid var(--border-color-light); }.action-row p { margin:0; color:var(--text-muted); font-size:13px; }.action-row > div { display:flex; flex-wrap:wrap; gap:8px; }.save-secondary { display:flex; justify-content:flex-end; margin-top:20px; }.runtime-details { margin:24px 2px 0; padding:18px 0 0; border-top:1px solid var(--border-color-light); }.runtime-details summary { display:flex; align-items:center; width:fit-content; gap:7px; cursor:pointer; color:var(--text-secondary); font-size:13px; }.runtime-details summary::-webkit-details-marker { display:none; }.runtime-details > p { margin:12px 0 0; color:var(--text-muted); font-size:13px; line-height:1.5; }.runtime-options { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:16px; }.runtime-options label { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:14px; border:1px solid var(--border-color-light); border-radius:7px; background:var(--bg-secondary); }.runtime-options span { display:grid; gap:3px; }.runtime-options strong { font-size:13px; }.runtime-options small { color:var(--text-muted); font-size:12px; line-height:1.4; }@media (max-width:900px) { .provider-list { grid-template-columns:repeat(3,minmax(0,1fr)); } }@media (max-width:680px) { .admin-ai-page { padding:22px 0 48px; }.page-header { align-items:flex-start; flex-direction:column; gap:12px; }.provider-list { grid-template-columns:repeat(2,minmax(0,1fr)); }.connection-form,.runtime-options { grid-template-columns:1fr; }.action-row { align-items:flex-start; flex-direction:column; }.action-row > div { align-self:flex-end; } }@media (max-width:380px) { .provider-list { grid-template-columns:1fr; }.provider-option { min-height:78px; grid-template-columns:28px minmax(0,1fr); align-items:start; }.provider-option > .el-icon:first-child { grid-row:1/3; }.provider-option span { gap:2px; } }
</style>
