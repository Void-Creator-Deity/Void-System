<template>
  <div class="document-manager fade-in">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="text-gradient">文档管理</h1>
      <p class="text-secondary">上传和管理您的知识库，开启深度 AI 问答体验</p>
    </div>

    <!-- 文件上传区域 -->
    <div class="upload-section">
      <div class="card upload-card card-glass">
        <div class="upload-area" @dragover="onDragOver" @drop="onDrop" @click="triggerFileSelect">
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.csv,.jpg,.jpeg,.png"
            style="display: none"
            @change="onFileSelect"
          />

          <div v-if="!uploading" class="upload-placeholder">
            <el-icon class="upload-icon-large"><Plus /></el-icon>
            <div class="upload-text">
              <p class="primary-text">拖拽文件到此处，或 <span class="text-primary">点击选择文件</span></p>
              <p class="secondary-text">
                支持 PDF、Word、Excel、图片、文本 (最大 50MB)
              </p>
            </div>
          </div>

          <!-- 上传进度 -->
          <div v-else class="upload-progress">
            <el-progress
              type="circle"
              :percentage="uploadProgress"
              :status="uploadStatus === 'success' ? 'success' : uploadStatus === 'error' ? 'exception' : undefined"
              :stroke-width="8"
              :width="120"
            />
            <p class="progress-text">{{ currentFileName }}</p>
            <p class="progress-message">{{ uploadMessage }}</p>
          </div>
        </div>

        <!-- 上传配置 -->
        <div class="upload-config">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-input
                v-model="uploadTitle"
                placeholder="文档标题 (可选)"
                clearable
              />
            </el-col>
            <el-col :span="12">
              <el-select
                v-model="uploadTags"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="添加标签 (可选)"
                style="width: 100%"
              />
            </el-col>
          </el-row>
        </div>
      </div>
    </div>

    <!-- 数据面板 -->
    <div class="stats-grid" v-if="stats">
      <div class="stat-card card">
        <div class="stat-value">{{ stats.total_documents }}</div>
        <div class="stat-label">总文档数</div>
      </div>
      <div class="stat-card card">
        <div class="stat-value">{{ stats.completed_documents }}</div>
        <div class="stat-label">已完成解析</div>
      </div>
      <div class="stat-card card">
        <div class="stat-value text-warning">{{ stats.status_stats.processing || 0 }}</div>
        <div class="stat-label">处理中</div>
      </div>
      <div class="stat-card card">
        <div class="stat-value">{{ formatFileSize(stats.total_size) }}</div>
        <div class="stat-label">存储容量</div>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="documents-section">
      <div class="section-header">
        <h2 class="section-title">我的知识库</h2>
        <div class="header-actions">
          <el-input
            v-model="vectorSearchQuery"
            placeholder="搜索文档内容..."
            clearable
            class="search-input"
            @keyup.enter="performVectorSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select v-model="filterStatus" placeholder="状态筛选" style="width: 120px" @change="loadDocuments">
            <el-option label="全部状态" value="" />
            <el-option label="解析中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="解析失败" value="failed" />
          </el-select>
          
          <el-button type="primary" link @click="loadDocuments" :loading="loading">
            <el-icon><RefreshRight /></el-icon>
          </el-button>
        </div>
      </div>
      
      <!-- 搜索结果预览 -->
      <div v-if="vectorSearchResults.length > 0" class="search-results-overlay card card-glass">
        <div class="overlay-header">
          <h3>内容命中 ({{ vectorSearchResults.length }})</h3>
          <el-button link @click="vectorSearchResults = []">关闭</el-button>
        </div>
        <div class="results-list">
          <div v-for="(result, i) in vectorSearchResults" :key="i" class="search-result-item">
            <div class="result-meta">命中率: {{ (result.score ? (1 - result.score) * 100 : 95).toFixed(1) }}%</div>
            <p class="result-text">{{ result.content }}</p>
          </div>
        </div>
      </div>

      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载文档中...</span>
      </div>

      <div v-else-if="documents.length === 0" class="empty-container card card-glass">
        <el-empty description="暂无文档记录" />
      </div>

      <div v-else class="document-grid">
        <div
          v-for="doc in documents"
          :key="doc.doc_id"
          class="document-card card"
          :class="getStatusClass(doc.parse_status)"
        >
          <div class="doc-header">
            <div class="doc-type-icon">
              <el-icon><component :is="getFileIcon(doc.file_type)" /></el-icon>
            </div>
            <div class="doc-main-info">
              <h3 class="doc-title">{{ doc.title }}</h3>
              <p class="doc-meta">{{ doc.original_name }} · {{ formatFileSize(doc.file_size) }}</p>
            </div>
            <el-tag :type="getStatusType(doc.parse_status)" size="small" effect="dark" class="status-tag">
              {{ getStatusText(doc.parse_status) }}
            </el-tag>
          </div>

          <div v-if="doc.parse_status === 'failed' && doc.error_message" class="doc-error-info">
            <el-icon><Warning /></el-icon> {{ doc.error_message }}
          </div>

          <div class="doc-body">
            <p class="doc-preview">{{ doc.content_preview || '尚无解析预览内容...' }}</p>
            <div class="doc-tags" v-if="doc.tags?.length">
              <el-tag v-for="tag in doc.tags" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
            </div>
          </div>

          <div class="doc-footer">
            <div class="doc-time">{{ formatDate(doc.created_at) }}</div>
            <div class="doc-actions">
              <el-button
                v-if="doc.parse_status === 'completed'"
                type="primary"
                size="small"
                @click="askWithDocument(doc)"
              >
                智能问答
              </el-button>
              
              <el-button size="small" circle @click="editDocument(doc)">
                <el-icon><Edit /></el-icon>
              </el-button>

              <el-dropdown @command="(c) => handleDocumentAction(c, doc)">
                <el-button size="small" circle>
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="preview">预览内容</el-dropdown-item>
                    <el-dropdown-item command="delete" class="text-error">删除记录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <!-- 解析进度条 -->
          <div v-if="doc.parse_status === 'processing' || doc.parse_status === 'parsed'" class="doc-status-line">
            <div class="progress-shimmer"></div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-container" v-if="totalCount > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalCount"
          layout="prev, pager, next"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 对话框部分 -->
    <el-dialog v-model="editDialogVisible" title="编辑文档" width="440px" class="cyber-dialog">
      <el-form :model="editingDoc" label-position="top">
        <el-form-item label="核心标题">
          <el-input v-model="editingDoc.title" placeholder="输入新标题" />
        </el-form-item>
        <el-form-item label="系统标签">
          <el-select v-model="editingDoc.tags" multiple filterable allow-create placeholder="添加分类卷标" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">丢弃更改</el-button>
        <el-button type="primary" @click="saveDocumentEdit" :loading="saving">确认同步</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewDialogVisible" title="内容预览" width="70%" class="cyber-dialog">
      <div class="preview-scroll">
        <pre class="code-block">{{ previewContent }}</pre>
      </div>
    </el-dialog>

    <el-dialog v-model="qaDialogVisible" :title="`文档分析: ${selectedDocForQA?.title}`" width="800px" class="cyber-dialog">
      <div class="qa-container">
        <div class="messages-area" ref="msgList">
          <div v-for="m in qaMessages" :key="m.id" class="qa-msg" :class="m.type">
            <div class="msg-content">{{ m.content }}</div>
            <div v-if="m.sources?.length" class="msg-sources">
              <span class="source-label">关联来源:</span>
              <el-tag v-for="(s, i) in m.sources" :key="i" size="small" class="source-tag">{{ s.title }}</el-tag>
            </div>
          </div>
        </div>
        <div class="qa-input-wrapper">
          <el-input
            v-model="qaQuestion"
            placeholder="询问关于此文档的问题..."
            @keyup.enter="sendQuestion"
            :disabled="asking"
          >
            <template #suffix>
              <el-button link @click="sendQuestion" :loading="asking">
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
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
}

/* 页面头部 */
.page-header {
  margin-bottom: 40px;
  text-align: center;
}

.page-header h1 {
  font-size: 32px;
  margin-bottom: 12px;
}

/* 上传卡片 */
.upload-card {
  padding: 2px;
  margin-bottom: 40px;
  border: 1px solid var(--color-border);
}

.upload-area {
  padding: 60px 20px;
  border: 2px dashed rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.02);
}

.upload-area:hover {
  border-color: var(--color-primary);
  background: rgba(var(--color-primary-rgb), 0.05);
}

.upload-icon-large {
  font-size: 48px;
  color: var(--color-primary);
  margin-bottom: 24px;
  opacity: 0.6;
}

.primary-text {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 8px;
}

.secondary-text {
  color: var(--color-text-dim);
  font-size: 14px;
}

.upload-progress {
  text-align: center;
}

.progress-message {
  margin-top: 16px;
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 14px;
}

.upload-config {
  margin-top: 24px;
  padding: 20px;
  border-top: 1px solid var(--color-border);
}

/* 统计面板 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.stat-card {
  padding: 24px;
  text-align: center;
  border: 1px solid var(--color-border);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--color-primary);
  margin-bottom: 8px;
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* 列表头部 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  border-left: 4px solid var(--color-primary);
  padding-left: 12px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.search-input :deep(.el-input__wrapper) {
  background: var(--color-bg-light);
  border-radius: var(--radius-full);
}

/* 文档网格 */
.document-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.document-card {
  display: flex;
  flex-direction: column;
  padding: 24px;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: all var(--transition-normal);
}

.document-card:hover {
  transform: translateY(-4px);
  border-color: var(--color-primary);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.doc-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.doc-type-icon {
  width: 48px;
  height: 48px;
  background: var(--color-bg-light);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--color-primary);
}

.doc-main-info {
  flex: 1;
}

.doc-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--color-text-bright);
}

.doc-meta {
  font-size: 12px;
  color: var(--color-text-dim);
}

.doc-body {
  flex: 1;
  margin-bottom: 24px;
}

.doc-preview {
  font-size: 14px;
  color: var(--color-text-dim);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 12px;
}

.doc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.doc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.doc-time {
  font-size: 12px;
  color: var(--color-text-dim);
}

.doc-actions {
  display: flex;
  gap: 8px;
}

/* 状态样式 */
.status-tag {
  border-radius: var(--radius-full);
}

.doc-error-info {
  margin: 0 16px 12px 16px;
  padding: 8px 12px;
  background: rgba(var(--color-danger-rgb), 0.1);
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-status-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: var(--color-primary);
  opacity: 0.5;
}

.progress-shimmer {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8), transparent);
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* 问答对话框 */
.qa-container {
  display: flex;
  flex-direction: column;
  height: 60vh;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-md);
  margin-bottom: 20px;
}

.qa-msg {
  max-width: 80%;
  padding: 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
}

.qa-msg.question {
  align-self: flex-end;
  background: var(--color-primary);
  color: white;
  border-bottom-right-radius: 2px;
}

.qa-msg.answer {
  align-self: flex-start;
  background: var(--color-bg-light);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 2px;
}

.qa-msg.typing {
  align-self: flex-start;
  color: var(--color-text-dim);
  font-style: italic;
  padding: 8px 16px;
}

.msg-sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.source-label {
  font-size: 12px;
  color: var(--color-text-dim);
}

/* 对话框覆盖层 */
.search-results-overlay {
  margin-bottom: 24px;
}

.overlay-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid var(--color-border);
}

.results-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
}

.search-result-item {
  padding: 16px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.result-meta {
  font-size: 11px;
  color: var(--color-primary);
  font-family: var(--font-mono);
  margin-bottom: 8px;
}

/* 响应式 */
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  .document-grid {
    grid-template-columns: 1fr;
  }
}

</style>

