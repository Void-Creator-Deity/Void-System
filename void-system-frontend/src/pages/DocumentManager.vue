<template>
  <div class="document-manager">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>文档管理</h1>
      <p class="page-description">上传和管理您的文档，开启个性化AI问答体验</p>
    </div>

    <!-- 文件上传区域 -->
    <div class="upload-section">
      <el-card class="upload-card">
        <template #header>
          <div class="upload-header">
            <el-icon class="upload-icon"><Upload /></el-icon>
            <span>上传文档</span>
          </div>
        </template>

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
              <p class="primary-text">拖拽文件到此处，或 <el-button type="primary" size="small">点击选择文件</el-button></p>
              <p class="secondary-text">
                支持格式：PDF、Word、Excel、图片、文本文件<br>
                单个文件最大 50MB，支持批量上传
              </p>
            </div>
          </div>

          <!-- 上传进度 -->
          <div v-else class="upload-progress">
            <el-progress
              type="circle"
              :percentage="uploadProgress"
              :status="uploadStatus === 'success' ? 'success' : uploadStatus === 'error' ? 'exception' : undefined"
            />
            <p class="progress-text">{{ currentFileName }}</p>
            <p class="progress-status">{{ uploadMessage }}</p>
          </div>
        </div>

        <!-- 上传配置 -->
        <div class="upload-config">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="文档标题（可选）">
                <el-input
                  v-model="uploadTitle"
                  placeholder="为文档设置一个易记的标题"
                  clearable
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="标签（可选）">
                <el-select
                  v-model="uploadTags"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="为文档添加标签"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-card>
    </div>

    <!-- 文档列表 -->
    <div class="documents-section">
      <el-card class="documents-card">
        <template #header>
          <div class="documents-header">
            <span>我的文档</span>
            <div class="header-actions">
              <el-select v-model="filterStatus" placeholder="筛选状态" style="width: 120px" @change="loadDocuments">
                <el-option label="全部" value="" />
                <el-option label="处理中" value="processing" />
                <el-option label="已完成" value="completed" />
                <el-option label="失败" value="failed" />
              </el-select>
              <el-button type="primary" @click="loadDocuments" :loading="loading">
                <el-icon><RefreshRight /></el-icon>
                刷新
              </el-button>
            </div>
          </div>
        </template>

        <!-- 统计信息 -->
        <div class="stats-bar" v-if="stats">
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ stats.total_documents }}</div>
                <div class="stat-label">总文档数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ stats.completed_documents }}</div>
                <div class="stat-label">已完成</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ stats.status_stats.processing || 0 }}</div>
                <div class="stat-label">处理中</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ formatFileSize(stats.total_size) }}</div>
                <div class="stat-label">总大小</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 文档列表 -->
        <div class="documents-list">
          <div v-if="loading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>加载文档中...</p>
          </div>

          <div v-else-if="documents.length === 0" class="empty-state">
            <el-empty description="还没有上传任何文档">
              <el-button type="primary" @click="triggerFileSelect">上传第一个文档</el-button>
            </el-empty>
          </div>

          <div v-else class="document-grid">
            <el-card
              v-for="doc in documents"
              :key="doc.doc_id"
              class="document-card"
              :class="getStatusClass(doc.parse_status)"
            >
              <div class="document-header">
                <div class="document-icon">
                  <el-icon :size="24">
                    <component :is="getFileIcon(doc.file_type)" />
                  </el-icon>
                </div>
                <div class="document-info">
                  <h3 class="document-title">{{ doc.title }}</h3>
                  <p class="document-meta">
                    {{ doc.original_name }} · {{ formatFileSize(doc.file_size) }} · {{ formatDate(doc.created_at) }}
                  </p>
                </div>
                <div class="document-status">
                  <el-tag :type="getStatusType(doc.parse_status)" size="small">
                    {{ getStatusText(doc.parse_status) }}
                  </el-tag>
                </div>
              </div>

              <div class="document-content">
                <p class="document-preview" v-if="doc.content_preview">
                  {{ doc.content_preview }}
                </p>
                <div v-else class="no-preview">
                  <el-text type="info">暂无预览内容</el-text>
                </div>

                <div class="document-tags" v-if="doc.tags && doc.tags.length > 0">
                  <el-tag
                    v-for="tag in doc.tags"
                    :key="tag"
                    size="small"
                    class="tag-item"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
              </div>

              <div class="document-actions">
                <el-button
                  v-if="doc.parse_status === 'completed'"
                  type="primary"
                  size="small"
                  @click="askWithDocument(doc)"
                >
                  <el-icon><ChatLineRound /></el-icon>
                  问答
                </el-button>

                <el-button
                  size="small"
                  @click="editDocument(doc)"
                  :disabled="doc.parse_status === 'processing'"
                >
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-button>

                <el-dropdown @command="handleDocumentAction" :disabled="doc.parse_status === 'processing'">
                  <el-button size="small">
                    更多操作 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="preview" :disabled="!doc.content_preview">
                        <el-icon><View /></el-icon>
                        预览内容
                      </el-dropdown-item>
                      <el-dropdown-item command="delete" divided>
                        <el-icon><Delete /></el-icon>
                        删除文档
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>

              <!-- 处理进度条 -->
              <div v-if="doc.parse_status === 'processing'" class="processing-bar">
                <el-progress :percentage="50" :show-text="false" />
                <span class="processing-text">正在解析文档内容...</span>
              </div>
            </el-card>
          </div>

          <!-- 分页 -->
          <div class="pagination-wrapper" v-if="documents.length > 0">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="totalCount"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
      </el-card>
    </div>

    <!-- 编辑文档对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑文档" width="500px">
      <el-form :model="editingDoc" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editingDoc.title" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="editingDoc.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="添加标签"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveDocumentEdit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog v-model="previewDialogVisible" title="文档预览" width="800px" :before-close="closePreview">
      <div class="preview-content">
        <pre>{{ previewContent }}</pre>
      </div>
    </el-dialog>

    <!-- 问答对话框 -->
    <el-dialog v-model="qaDialogVisible" title="文档问答" width="800px" :before-close="closeQA">
      <div class="qa-content">
        <div class="selected-doc-info">
          <el-tag>基于文档：{{ selectedDocForQA.title }}</el-tag>
        </div>

        <div class="qa-messages">
          <div v-for="message in qaMessages" :key="message.id" class="message" :class="message.type">
            <div class="message-content">
              <p v-if="message.type === 'question'">{{ message.content }}</p>
              <div v-else-if="message.type === 'answer'">
                <p>{{ message.content }}</p>
                <div class="answer-sources" v-if="message.sources && message.sources.length > 0">
                  <p><strong>参考来源：</strong></p>
                  <el-tag v-for="source in message.sources" :key="source.doc_id" size="small">
                    {{ source.title }}
                  </el-tag>
                </div>
              </div>
              <div v-else class="typing">
                <el-icon class="is-loading"><Loading /></el-icon>
                {{ message.content }}
              </div>
            </div>
          </div>
        </div>

        <div class="qa-input">
          <el-input
            v-model="qaQuestion"
            placeholder="请输入您的问题..."
            @keyup.enter="sendQuestion"
            :disabled="asking"
          >
            <template #suffix>
              <el-button
                type="primary"
                :icon="ChatLineRound"
                @click="sendQuestion"
                :loading="asking"
                :disabled="!qaQuestion.trim()"
              >
                发送
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
  Delete
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from '@/api/index.js'

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

// 文件类型图标映射
const getFileIcon = (fileType) => {
  const iconMap = {
    'pdf': 'Document',
    'doc': 'Document',
    'docx': 'Document',
    'xls': 'Document',
    'xlsx': 'Document',
    'csv': 'Document',
    'txt': 'Document',
    'md': 'Document',
    'jpg': 'Picture',
    'jpeg': 'Picture',
    'png': 'Picture',
    'gif': 'Picture'
  }
  return iconMap[fileType] || 'Document'
}

// 状态相关方法
const getStatusText = (status) => {
  const statusMap = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '处理失败'
  }
  return statusMap[status] || status
}

const getStatusType = (status) => {
  const typeMap = {
    'pending': '',
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return typeMap[status] || ''
}

const getStatusClass = (status) => {
  return `status-${status}`
}

// 工具方法
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const formatDate = (dateString) => {
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
    const response = await axios.post('/api/user/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress.value = percentCompleted
        uploadMessage.value = `上传中... ${percentCompleted}%`

        // 模拟处理进度
        if (percentCompleted === 100) {
          uploadMessage.value = '上传完成，正在处理文档...'
        }
      }
    })

    const data = response.data
    if (data.success) {
      uploadStatus.value = 'success'
      uploadMessage.value = `成功上传 ${data.data.successful_count}/${data.data.total_count} 个文件`

      // 清空表单
      uploadTitle.value = ''
      uploadTags.value = []

      // 刷新文档列表
      await loadDocuments()

      ElMessage.success(data.message)
    } else {
      uploadStatus.value = 'error'
      uploadMessage.value = data.message || '上传失败'
      ElMessage.error(data.message || '上传失败')
    }
  } catch (error) {
    uploadStatus.value = 'error'
    uploadMessage.value = '上传失败'
    ElMessage.error('上传失败：' + (error.response?.data?.message || error.message))
  } finally {
    setTimeout(() => {
      uploading.value = false
    }, 2000)
  }
}

// 文档管理方法
const loadDocuments = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/user/documents', {
      params: {
        status: filterStatus.value || undefined,
        limit: pageSize.value,
        offset: (currentPage.value - 1) * pageSize.value
      }
    })

    if (response.data.success) {
      documents.value = response.data.data.documents || []
      totalCount.value = response.data.data.pagination?.total || documents.value.length
    }
  } catch (error) {
    ElMessage.error('加载文档失败：' + (error.response?.data?.message || error.message))
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const response = await axios.get('/api/user/documents/stats')
    if (response.data.success) {
      stats.value = response.data.data
    }
  } catch (error) {
    console.error('加载统计信息失败：', error)
  }
}

// 编辑相关方法
const editDocument = (doc) => {
  editingDoc.value = { ...doc }
  editDialogVisible.value = true
}

const saveDocumentEdit = async () => {
  if (!editingDoc.value.title?.trim()) {
    ElMessage.warning('请输入文档标题')
    return
  }

  saving.value = true
  try {
    const response = await axios.put(`/api/user/documents/${editingDoc.value.doc_id}`, {
      title: editingDoc.value.title.trim(),
      tags: editingDoc.value.tags || []
    })

    if (response.data.success) {
      editDialogVisible.value = false
      await loadDocuments()
      ElMessage.success('文档信息更新成功')
    } else {
      ElMessage.error(response.data.message || '更新失败')
    }
  } catch (error) {
    ElMessage.error('更新失败：' + (error.response?.data?.message || error.message))
  } finally {
    saving.value = false
  }
}

// 预览相关方法
const previewDocument = async (doc) => {
  try {
    const response = await axios.get(`/api/user/documents/${doc.doc_id}`)
    if (response.data.success) {
      previewContent.value = response.data.data.content_preview || '暂无预览内容'
      previewDialogVisible.value = true
    }
  } catch (error) {
    ElMessage.error('预览失败：' + (error.response?.data?.message || error.message))
  }
}

const closePreview = () => {
  previewDialogVisible.value = false
  previewContent.value = ''
}

// 问答相关方法
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

  // 添加用户问题到消息列表
  qaMessages.value.push({
    id: Date.now(),
    type: 'question',
    content: question
  })

  // 添加AI回答中状态
  const answerId = Date.now() + 1
  qaMessages.value.push({
    id: answerId,
    type: 'typing',
    content: '正在分析文档...'
  })

  asking.value = true

  try {
    const response = await axios.post('/api/user/qa/ask', {
      question: question,
      document_ids: [selectedDocForQA.value.doc_id]
    })

    if (response.data.success) {
      // 替换打字状态为实际回答
      const answerIndex = qaMessages.value.findIndex(msg => msg.id === answerId)
      if (answerIndex !== -1) {
        qaMessages.value[answerIndex] = {
          id: answerId,
          type: 'answer',
          content: response.data.data.answer,
          sources: response.data.data.sources,
          confidence: response.data.data.confidence
        }
      }
    } else {
      // 替换为错误消息
      const answerIndex = qaMessages.value.findIndex(msg => msg.id === answerId)
      if (answerIndex !== -1) {
        qaMessages.value[answerIndex] = {
          id: answerId,
          type: 'answer',
          content: response.data.data.answer || '回答生成失败',
          sources: [],
          confidence: 0
        }
      }
    }
  } catch (error) {
    // 替换为错误消息
    const answerIndex = qaMessages.value.findIndex(msg => msg.id === answerId)
    if (answerIndex !== -1) {
      qaMessages.value[answerIndex] = {
        id: answerId,
        type: 'answer',
        content: '抱歉，处理您的问题时出现了错误，请稍后重试。',
        sources: [],
        confidence: 0
      }
    }
    ElMessage.error('问答失败：' + (error.response?.data?.message || error.message))
  } finally {
    asking.value = false
  }
}

const closeQA = () => {
  qaDialogVisible.value = false
  selectedDocForQA.value = null
  qaMessages.value = []
  qaQuestion.value = ''
}

// 操作处理方法
const handleDocumentAction = async (command) => {
  const doc = arguments[1] // 从dropdown传递的文档对象

  switch (command) {
    case 'preview':
      await previewDocument(doc)
      break
    case 'delete':
      await deleteDocument(doc)
      break
  }
}

const deleteDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档 "${doc.title}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await axios.delete(`/api/user/documents/${doc.doc_id}`)
    if (response.data.success) {
      await loadDocuments()
      await loadStats()
      ElMessage.success('文档删除成功')
    } else {
      ElMessage.error(response.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败：' + (error.response?.data?.message || error.message))
    }
  }
}

// 分页处理
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
  loadDocuments()
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
  loadDocuments()
}

// 生命周期
onMounted(async () => {
  await Promise.all([loadDocuments(), loadStats()])
})
</script>

<style scoped>
.document-manager {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
  text-align: center;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.page-description {
  color: #6b7280;
  font-size: 16px;
}

/* 上传区域样式 */
.upload-section {
  margin-bottom: 40px;
}

.upload-card {
  border: 2px dashed #d1d5db;
  transition: all 0.3s ease;
}

.upload-card:hover {
  border-color: #3b82f6;
}

.upload-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  color: #3b82f6;
  font-size: 20px;
}

.upload-area {
  padding: 40px;
  text-align: center;
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.3s ease;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-area:hover {
  background-color: #f8fafc;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon-large {
  font-size: 48px;
  color: #9ca3af;
}

.upload-text {
  text-align: center;
}

.primary-text {
  font-size: 16px;
  color: #1f2937;
  margin-bottom: 4px;
}

.secondary-text {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.progress-text {
  font-weight: 500;
  color: #1f2937;
}

.progress-status {
  font-size: 14px;
  color: #6b7280;
}

.upload-config {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

/* 文档列表样式 */
.documents-section {
  margin-top: 40px;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stats-bar {
  margin-bottom: 24px;
  padding: 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-radius: 8px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.documents-list {
  min-height: 200px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #6b7280;
}

.document-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.document-card {
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
}

.document-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.document-card.status-processing {
  border-color: #fbbf24;
  background: linear-gradient(135deg, #fefce8 0%, #fffbeb 100%);
}

.document-card.status-completed {
  border-color: #10b981;
  background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
}

.document-card.status-failed {
  border-color: #ef4444;
  background: linear-gradient(135deg, #fef2f2 0%, #fef2f2 100%);
}

.document-header {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.document-icon {
  flex-shrink: 0;
  padding: 8px;
  background: #f3f4f6;
  border-radius: 6px;
}

.document-info {
  flex: 1;
  min-width: 0;
}

.document-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-meta {
  font-size: 12px;
  color: #6b7280;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-status {
  flex-shrink: 0;
}

.document-content {
  margin-bottom: 16px;
}

.document-preview {
  font-size: 14px;
  color: #4b5563;
  line-height: 1.5;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.no-preview {
  font-style: italic;
  color: #9ca3af;
}

.document-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-item {
  margin: 0;
}

.document-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.processing-bar {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid #e5e7eb;
}

.processing-text {
  font-size: 12px;
  color: #6b7280;
}

.pagination-wrapper {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

/* 对话框样式 */
.preview-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  max-height: 400px;
  overflow-y: auto;
  background: #f8fafc;
  padding: 16px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.qa-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selected-doc-info {
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 6px;
  border-left: 4px solid #3b82f6;
}

.qa-messages {
  max-height: 300px;
  overflow-y: auto;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fafafa;
}

.message {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 8px;
}

.message.question {
  background: #3b82f6;
  color: white;
  margin-left: 20px;
}

.message.answer {
  background: white;
  border: 1px solid #e5e7eb;
  margin-right: 20px;
}

.message.typing {
  background: #f3f4f6;
  color: #6b7280;
  font-style: italic;
}

.message-content {
  line-height: 1.5;
}

.answer-sources {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}

.qa-input {
  margin-top: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .document-manager {
    padding: 16px;
  }

  .documents-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .header-actions {
    justify-content: space-between;
  }

  .document-grid {
    grid-template-columns: 1fr;
  }

  .stat-item {
    margin-bottom: 16px;
  }

  .upload-area {
    padding: 20px;
  }

  .upload-icon-large {
    font-size: 32px;
  }
}
</style>

