<template>
  <div class="void-page-container document-manager">
    <div class="void-content">
      <!-- Page Header -->
      <header class="page-header">
        <h1 class="logo-text"><span class="void-text-gradient">文件</span> 归档</h1>
        <p class="subtitle">用于深度智能集成的神经仓库。</p>
      </header>
      
      <!-- 注入部分 -->
      <section class="upload-section animate-slide-up">
        <div class="void-card upload-card">
          <div 
            class="void-upload-area" 
            :class="{ 'uploading': uploading }"
            @dragover="onDragOver" 
            @drop="onDrop" 
            @click="triggerFileSelect"
          >
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.csv,.jpg,.jpeg,.png"
              style="display: none"
              @change="onFileSelect"
            />
            
            <div v-if="!uploading" class="upload-prompt">
              <el-icon class="prompt-icon"><Plus /></el-icon>
              <div class="prompt-text">
                <p class="main-text">通过拖拽或 <span class="highlight">点击此处</span> 部署新切片</p>
                <p class="sub-text">支持格式: PDF, Word, Excel, 图片, 文本 (最大 50MB)</p>
              </div>
            </div>
            
            <!-- 注入进度 -->
            <div v-else class="upload-status">
              <el-progress 
                type="circle" 
                :percentage="uploadProgress" 
                :status="uploadStatus === 'success' ? 'success' : uploadStatus === 'error' ? 'exception' : undefined"
                :stroke-width="6" 
                :width="100"
                class="void-progress"
              />
              <p class="filename">{{ currentFileName }}</p>
              <p class="status-msg">{{ uploadMessage }}</p>
            </div>
          </div>
          
          <div class="upload-meta">
            <div class="void-form-group">
              <label>切片标识符 (可选标题)</label>
              <el-input v-model="uploadTitle" placeholder="指定标题..." class="void-input" />
            </div>
            <div class="void-form-group">
              <label>索引分类器 (标签)</label>
              <el-select 
                v-model="uploadTags" 
                multiple 
                filterable 
                allow-create 
                default-first-option 
                placeholder="分配标签..." 
                class="void-select"
              />
            </div>
          </div>
        </div>
      </section>
      
      <!-- 统计概览 -->
      <section class="stats-overview" v-if="stats">
        <div class="void-stat-card animate-float">
          <div class="stat-icon"><DocumentIcon /></div>
          <div class="stat-info">
            <span class="stat-label">切片总数</span>
            <span class="stat-value">{{ stats.total_documents }}</span>
          </div>
        </div>
        <div class="void-stat-card animate-float" style="animation-delay: 0.1s">
          <div class="stat-icon"><component is="Check" /></div>
          <div class="stat-info">
            <span class="stat-label">已集成</span>
            <span class="stat-value">{{ stats.completed_documents }}</span>
          </div>
        </div>
        <div class="void-stat-card animate-float" style="animation-delay: 0.2s">
          <div class="stat-icon"><Loading class="is-loading" /></div>
          <div class="stat-info">
            <span class="stat-label">正在处理</span>
            <span class="stat-value alternate">{{ stats.status_stats.processing || 0 }}</span>
          </div>
        </div>
        <div class="void-stat-card animate-float" style="animation-delay: 0.3s">
          <div class="stat-icon"><Monitor /></div>
          <div class="stat-info">
            <span class="stat-label">内存负载</span>
            <span class="stat-value">{{ formatFileSize(stats.total_size) }}</span>
          </div>
        </div>
      </section>
      
      <!-- 文件列表部分 -->
      <section class="archive-section">
        <header class="section-header">
          <div class="title-group">
            <h2 class="section-title">知识内核</h2>
            <div class="void-badge primary">{{ totalCount }} 条目</div>
          </div>
          
          <div class="header-filters">
            <el-input 
              v-model="vectorSearchQuery" 
              placeholder="查询神经模式..." 
              clearable 
              class="void-input search-input"
              @keyup.enter="performVectorSearch"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            
            <el-select v-model="filterStatus" placeholder="状态过滤" class="void-select status-select" @change="loadDocuments">
              <el-option label="所有状态" value="" />
              <el-option label="正在处理" value="processing" />
              <el-option label="已完成" value="completed" />
              <el-option label="已失败" value="failed" />
            </el-select>
            
            <button class="void-icon-btn" @click="loadDocuments" :disabled="loading">
              <el-icon :class="{ 'is-loading': loading }"><RefreshRight /></el-icon>
            </button>
          </div>
        </header>

        <!-- 搜索结果覆盖层 -->
        <div v-if="vectorSearchResults.length > 0" class="search-overlay void-card animate-fade-in">
          <div class="overlay-header">
            <h3>神经模式匹配 ({{ vectorSearchResults.length }})</h3>
            <button class="void-btn text" @click="vectorSearchResults = []">关闭</button>
          </div>
          <div class="results-list">
            <div v-for="(result, i) in vectorSearchResults" :key="i" class="result-shard">
              <div class="shard-meta">置信度: {{ (result.score ? (1 - result.score) * 100 : 95).toFixed(1) }}%</div>
              <p class="shard-content">{{ result.content }}</p>
            </div>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="void-loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在同步归档...</span>
        </div>

        <!-- 空状态 -->
        <div v-else-if="documents.length === 0" class="void-empty-state">
          <el-empty description="系统归档库目前处于虚空状态。" />
        </div>

        <!-- Document Grid -->
        <div v-else class="void-grid document-grid">
          <div 
            v-for="doc in documents" 
            :key="doc.doc_id" 
            class="void-card document-card"
            :class="getStatusClass(doc.parse_status)"
          >
            <div class="card-glow"></div>
            
            <div class="doc-header">
              <div class="type-icon-wrapper">
                <el-icon><component :is="getFileIcon(doc.file_type)" /></el-icon>
              </div>
              <div class="doc-info">
                <h4 class="doc-title">{{ doc.title }}</h4>
                <div class="doc-specs">
                  <span>{{ doc.file_type.toUpperCase() }}</span>
                  <span class="divider"></span>
                  <span>{{ formatFileSize(doc.file_size) }}</span>
                </div>
              </div>
              <div class="doc-status">
                <div class="void-status-pill" :class="getStatusType(doc.parse_status)">
                  {{ getStatusText(doc.parse_status) }}
                </div>
              </div>
            </div>

            <div v-if="doc.parse_status === 'failed' && doc.error_message" class="error-strip">
              <el-icon><Warning /></el-icon>
              <span>{{ doc.error_message }}</span>
            </div>

            <div class="doc-preview-area">
              <p class="preview-text">{{ doc.content_preview || '正在解析内容片段...' }}</p>
              <div class="doc-tags" v-if="doc.tags?.length">
                <el-tag v-for="tag in doc.tags" :key="tag" size="small" class="void-tag sm">{{ tag }}</el-tag>
              </div>
            </div>

            <div class="doc-footer">
              <span class="timestamp">{{ formatDate(doc.created_at) }}</span>
              <div class="action-dock">
                <el-button 
                  v-if="doc.parse_status === 'completed'" 
                  type="primary" 
                  class="void-btn primary sm" 
                  @click="askWithDocument(doc)"
                >
                  DEEP_ANALYZE
                </el-button>
                
                <button class="void-icon-btn sm" @click="editDocument(doc)">
                  <el-icon><Edit /></el-icon>
                </button>

                <el-dropdown @command="(c) => handleDocumentAction(c, doc)">
                  <button class="void-icon-btn sm">
                    <el-icon><ArrowDown /></el-icon>
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu class="void-dropdown">
                      <el-dropdown-item command="preview">Preview Buffer</el-dropdown-item>
                      <el-dropdown-item command="delete" class="text-error">Wipe Data</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>

            <!-- Analysis Progress Line -->
            <div v-if="doc.parse_status === 'processing' || doc.parse_status === 'parsed'" class="analysis-line">
              <div class="line-shimmer"></div>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <footer class="archive-footer" v-if="totalCount > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="totalCount"
            layout="prev, pager, next"
            class="void-pagination"
            @current-change="handleCurrentChange"
          />
        </footer>
      </section>
    </div>

    <!-- Modals -->
    <el-dialog v-model="editDialogVisible" title="Neural Metadata Shift" width="500px" class="void-dialog">
      <div class="modal-body">
        <div class="void-form-group">
          <label>Redefine Shard Title</label>
          <el-input v-model="editingDoc.title" placeholder="New identifier..." class="void-input" />
        </div>
        <div class="void-form-group">
          <label>Update Classifiers</label>
          <el-select v-model="editingDoc.tags" multiple filterable allow-create class="void-select" placeholder="Add classification..." style="width: 100%" />
        </div>
      </div>
      <template #footer>
        <div class="modal-footer">
          <el-button class="void-btn text" @click="editDialogVisible = false">Cancel</el-button>
          <el-button type="primary" class="void-btn primary" @click="saveDocumentEdit" :loading="saving">Synchronize</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="previewDialogVisible" title="Buffer Preview" width="80%" class="void-dialog full-height">
      <div class="preview-scroll">
        <pre class="void-code-block">{{ previewContent }}</pre>
      </div>
    </el-dialog>

    <el-dialog v-model="qaDialogVisible" :title="`DEEP ANALYSIS: ${selectedDocForQA?.title}`" width="900px" class="void-dialog has-footer">
      <div class="qa-neural-link">
        <div class="chat-viewport" ref="msgList">
          <div v-for="m in qaMessages" :key="m.id" class="neural-message" :class="m.type">
            <div class="msg-bubble">{{ m.content }}</div>
            <div v-if="m.sources?.length" class="msg-knowledge">
              <div class="meta-label">SOURCE_SHARDS:</div>
              <div class="source-cloud">
                <el-tag v-for="(s, i) in m.sources" :key="i" size="small" class="void-tag sm">{{ s.title }}</el-tag>
              </div>
            </div>
          </div>
        </div>
        <div class="chat-input-area">
          <el-input 
            v-model="qaQuestion" 
            placeholder="Initialize query pattern..." 
            class="void-input" 
            @keyup.enter="sendQuestion" 
            :disabled="asking"
          >
            <template #append>
              <el-button class="void-btn primary" @click="sendQuestion" :loading="asking">
                <el-icon><Plus /></el-icon>
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import {
  Upload,
  Plus,
  RefreshRight,
  Loading,
  ChatLineRound,
  Edit,
  ArrowDown,
  View,
  Delete,
  Search,
  Document as DocumentIcon,
  Picture as PictureIcon
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { documentApi } from '@/api/document'

// 响应式数据
const fileInput = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadMessage = ref('')
const currentFileName = ref('')

const uploadTitle = ref('')
const uploadTags = ref([])

const loading = ref(false)
const documents = ref([])
const stats = ref(null)
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

const editDialogVisible = ref(false)
const editingDoc = ref({})
const saving = ref(false)

const previewDialogVisible = ref(false)
const previewContent = ref('')

const qaDialogVisible = ref(false)
const selectedDocForQA = ref(null)
const qaQuestion = ref('')
const qaMessages = ref([])
const asking = ref(false)

// 向量搜索相关
const vectorSearchQuery = ref('')
const vectorSearchResults = ref([])
const vectorSearchLoading = ref(false)

// 文件类型图标映射
const getFileIcon = (fileType) => {
  const iconMap = {
    'pdf': 'DocumentIcon',
    'doc': 'DocumentIcon',
    'docx': 'DocumentIcon',
    'xls': 'DocumentIcon',
    'xlsx': 'DocumentIcon',
    'csv': 'DocumentIcon',
    'txt': 'DocumentIcon',
    'md': 'DocumentIcon',
    'jpg': 'PictureIcon',
    'jpeg': 'PictureIcon',
    'png': 'PictureIcon',
    'gif': 'PictureIcon'
  }
  return iconMap[fileType] || 'DocumentIcon'
}

// 状态相关方法
const getStatusText = (status) => {
  const statusMap = {
    'pending': '等待中',
    'processing': '正在解析',
    'parsed': '正在向量化',
    'completed': '处理完成',
    'failed': '解析失败'
  }
  return statusMap[status] || status
}

const getStatusType = (status) => {
  const typeMap = {
    'pending': 'info',
    'processing': 'warning',
    'parsed': 'primary',
    'completed': 'success',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusClass = (status) => {
  return `status-${status}`
}

// 工具方法
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

// 上传相关方法
const triggerFileSelect = () => {
  fileInput.value?.click()
}

const onDragOver = (e) => {
  e.preventDefault()
}

const onDrop = (e) => {
  e.preventDefault()
  const files = Array.from(e.dataTransfer.files)
  handleFileUpload(files)
}

const onFileSelect = (e) => {
  const files = Array.from(e.target.files)
  handleFileUpload(files)
}

const handleFileUpload = async (files) => {
  if (files.length === 0) return

  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })

  if (uploadTitle.value.trim()) {
    formData.append('title', uploadTitle.value.trim())
  }

  if (uploadTags.value.length > 0) {
    formData.append('tags', JSON.stringify(uploadTags.value))
  }

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadMessage.value = '准备上传...'

  try {
    const response = await documentApi.upload(formData, (progressEvent) => {
      const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      uploadProgress.value = percentCompleted
      uploadMessage.value = `上传中... ${percentCompleted}%`
      
      if (percentCompleted === 100) {
        uploadMessage.value = '上传完成，后台处理中...'
      }
    })

    const data = response.data
    if (data.success) {
      uploadStatus.value = 'success'
      uploadMessage.value = `成功上传 ${data.data.successful_count}/${data.data.total_count} 个文件`
      
      // 清空表单
      uploadTitle.value = ''
      uploadTags.value = []
      
      // 刷新数据
      await Promise.all([loadDocuments(), loadStats()])
      ElMessage.success(data.message)
    } else {
      uploadStatus.value = 'error'
      uploadMessage.value = data.message || '上传异常'
    }
  } catch (error) {
    uploadStatus.value = 'error'
    uploadMessage.value = '上传失败'
    ElMessage.error('上传失败：' + (error.response?.data?.message || error.message))
  } finally {
    setTimeout(() => {
      uploading.value = false
    }, 3000)
  }
}

// 文档管理方法
const loadDocuments = async () => {
  loading.value = true
  try {
    const response = await documentApi.list({
      status: filterStatus.value || undefined,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value
    })

    if (response.data.success) {
      documents.value = response.data.data.documents || []
      totalCount.value = response.data.data.pagination?.total || documents.value.length
    }
  } catch (error) {
    console.error('加载文档失败:', error)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const response = await documentApi.getStats()
    if (response.data.success) {
      stats.value = response.data.data
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 编辑相关
const editDocument = (doc) => {
  editingDoc.value = { 
    doc_id: doc.doc_id,
    title: doc.title,
    tags: [...(doc.tags || [])]
  }
  editDialogVisible.value = true
}

const saveDocumentEdit = async () => {
  if (!editingDoc.value.title?.trim()) {
    ElMessage.warning('请输入标题')
    return
  }

  saving.value = true
  try {
    const response = await documentApi.update(editingDoc.value.doc_id, {
      title: editingDoc.value.title.trim(),
      tags: editingDoc.value.tags || []
    })

    if (response.data.success) {
      editDialogVisible.value = false
      await loadDocuments()
      ElMessage.success('更新成功')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 预览相关
const previewDocument = async (doc) => {
  try {
    const response = await documentApi.get(doc.doc_id)
    if (response.data.success) {
      previewContent.value = response.data.data.content_preview || '暂无内容'
      previewDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error('无法预览')
  }
}

const closePreview = () => {
  previewDialogVisible.value = false
  previewContent.value = ''
}

// 问答相关
const askWithDocument = (doc) => {
  selectedDocForQA.value = doc
  qaMessages.value = []
  qaQuestion.value = ''
  qaDialogVisible.value = true
}

const sendQuestion = async () => {
  if (!qaQuestion.value.trim()) return

  const question = qaQuestion.value.trim()
  qaQuestion.value = ''
  
  qaMessages.value.push({ id: Date.now(), type: 'question', content: question })
  
  const answerId = Date.now() + 1
  qaMessages.value.push({ id: answerId, type: 'typing', content: '分析中...' })
  
  asking.value = true
  try {
    const response = await documentApi.ask(question, [selectedDocForQA.value.doc_id])
    const answerIndex = qaMessages.value.findIndex(m => m.id === answerId)
    
    if (response.data.success && answerIndex !== -1) {
      qaMessages.value[answerIndex] = {
        id: answerId,
        type: 'answer',
        content: response.data.data.answer,
        sources: response.data.data.sources
      }
    }
  } catch (error) {
    const answerIndex = qaMessages.value.findIndex(m => m.id === answerId)
    if (answerIndex !== -1) {
      qaMessages.value[answerIndex].content = '问答系统暂时不可用'
    }
  } finally {
    asking.value = false
  }
}

const closeQA = () => {
  qaDialogVisible.value = false
  selectedDocForQA.value = null
}

// 操作分发 (修复 Bug)
const handleDocumentAction = async (command, doc) => {
  switch (command) {
    case 'preview':
      await previewDocument(doc)
      break
    case 'delete':
      await deleteDoc(doc)
      break
  }
}

const deleteDoc = async (doc) => {
  try {
    await ElMessageBox.confirm(`确定要彻底删除 "${doc.title}" 吗？`, '警告', {
      type: 'warning',
      confirmButtonText: '极其确定',
      cancelButtonText: '手滑了'
    })
    
    const response = await documentApi.delete(doc.doc_id)
    if (response.data.success) {
      ElMessage.success('文档已删除')
      await Promise.all([loadDocuments(), loadStats()])
    }
  } catch(e) { /* Cancel */ }
}

// 向量搜索
const performVectorSearch = async () => {
  if (!vectorSearchQuery.value.trim()) return
  
  vectorSearchLoading.value = true
  try {
    const response = await documentApi.search(vectorSearchQuery.value.trim())
    if (response.data.success) {
      vectorSearchResults.value = response.data.data.results || []
    }
  } catch (error) {
    ElMessage.error('搜索异常')
  } finally {
    vectorSearchLoading.value = false
  }
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  loadDocuments()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadDocuments()
}

// 初始化
onMounted(() => {
  loadDocuments()
  loadStats()
})
</script>

<style scoped>
.document-manager {
  min-height: 100vh;
}

.void-content {
  padding: var(--spacing-xxl) 0;
  max-width: 1400px;
  margin: 0 auto;
}

/* Page Header */
.page-header {
  margin-bottom: var(--spacing-xxxl);
  text-align: center;
}

/* Upload Section */
.upload-section {
  margin-bottom: var(--spacing-xxxl);
}

.upload-card {
  padding: var(--spacing-xl);
}

.void-upload-area {
  padding: var(--spacing-xxxl) var(--spacing-xl);
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary-transparent);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.void-upload-area:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-transparent);
}

.void-upload-area.uploading {
  cursor: wait;
}

.prompt-icon {
  font-size: 3rem;
  color: var(--color-primary);
  margin-bottom: var(--spacing-lg);
  opacity: 0.6;
}

.main-text {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: var(--spacing-xs);
}

.highlight {
  color: var(--color-primary-light);
  text-decoration: underline;
}

.sub-text {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.upload-status {
  text-align: center;
}

.filename {
  margin-top: var(--spacing-md);
  font-weight: 600;
}

.status-msg {
  color: var(--color-primary);
  font-family: var(--font-family-mono);
  font-size: 0.85rem;
  margin-top: var(--spacing-sm);
}

.upload-meta {
  margin-top: var(--spacing-xl);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
  padding-top: var(--spacing-xl);
  border-top: 1px solid var(--border-color-light);
}

/* Stats Overview */
.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-xxxl);
}

.void-stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
  backdrop-filter: blur(10px);
}

.stat-icon {
  width: 50px;
  height: 50px;
  background: var(--color-primary-transparent);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: var(--color-primary);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 800;
  font-family: var(--font-family-mono);
  color: var(--color-primary-light);
}

.stat-value.alternate {
  color: var(--color-warning);
}

/* Archive Section */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  gap: var(--spacing-xl);
  flex-wrap: wrap;
}

.title-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.section-title {
  font-size: 1.5rem;
  margin: 0;
}

.header-filters {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

.search-input {
  width: 300px;
}

.status-select {
  width: 160px;
}

/* Document Grid */
.document-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: var(--spacing-xl);
}

.document-card {
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.doc-header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.type-icon-wrapper {
  width: 44px;
  height: 44px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: var(--color-primary);
  border: 1px solid var(--border-color-light);
}

.doc-info {
  flex: 1;
}

.doc-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.doc-specs {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.divider {
  width: 3px;
  height: 3px;
  background: var(--text-muted);
  border-radius: 50%;
}

.doc-preview-area {
  flex: 1;
  margin-bottom: var(--spacing-xl);
}

.preview-text {
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: var(--spacing-md);
}

.doc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.doc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color-light);
}

.timestamp {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-family-mono);
}

.action-dock {
  display: flex;
  gap: var(--spacing-xs);
}

.error-strip {
  background: var(--color-danger-transparent);
  border-left: 3px solid var(--color-danger);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  color: var(--color-danger-light);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: var(--spacing-md);
}

.analysis-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: var(--color-primary-transparent);
}

.line-shimmer {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
  animation: shimmer 2s infinite linear;
}

/* Modals & Overlays */
.search-overlay {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
}

.result-shard {
  padding: var(--spacing-md);
  background: var(--bg-secondary-transparent);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
}

.shard-meta {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 4px;
}

.preview-scroll {
  max-height: 60vh;
  overflow-y: auto;
}

.qa-neural-link {
  height: 600px;
  display: flex;
  flex-direction: column;
}

.chat-viewport {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.neural-message {
  max-width: 80%;
  display: flex;
  flex-direction: column;
}

.neural-message.question {
  align-self: flex-end;
}

.neural-message.answer {
  align-self: flex-start;
}

.msg-bubble {
  padding: var(--spacing-lg);
  border-radius: var(--radius-lg);
  line-height: 1.6;
}

.question .msg-bubble {
  background: var(--void-gradient);
  color: white;
  border-bottom-right-radius: 4px;
}

.answer .msg-bubble {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 4px;
}

.msg-knowledge {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color-light);
}

.meta-label {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--text-muted);
  margin-bottom: var(--spacing-xs);
}

.source-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.chat-input-area {
  padding: var(--spacing-xl);
  border-top: 1px solid var(--border-color-light);
}

@keyframes shimmer {
  from { transform: translateX(-100%); }
  to { transform: translateX(100%); }
}

@media (max-width: 768px) {
  .header-filters {
    width: 100%;
  }
  .search-input {
    flex: 1;
  }
  .upload-meta {
    grid-template-columns: 1fr;
  }
}
</style>

