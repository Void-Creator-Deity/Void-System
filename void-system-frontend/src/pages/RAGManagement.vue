<!--
 * Void System Frontend - RAG Management Page
 * ------------------------------------------
 * 管理员专用RAG文档管理页面
-->

<template>
  <div class="rag-management fade-in">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="text-gradient">RAG系统管理</h1>
      <p class="text-secondary">管理员专用：管理系统级知识库文档，为 RAG 提供核心数据支持</p>
    </div>

    <!-- 操作与过滤栏 -->
    <div class="action-section">
      <div class="card action-card card-glass">
        <div class="action-top">
          <div class="primary-actions">
            <el-button type="primary" class="btn-cyber" @click="showUploadDialog = true">
              <el-icon><Upload /></el-icon> 上传文档
            </el-button>
            <el-button class="btn-cyber-outline" @click="syncDatabase">
              <el-icon><Refresh /></el-icon> 同步向量库
            </el-button>
          </div>
          <div class="search-box">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索文档标题..."
              prefix-icon="Search"
              clearable
              class="cyber-input"
            />
          </div>
        </div>

        <div class="filter-bottom">
          <div class="filter-label">标签过滤:</div>
          <div class="filter-tags">
            <el-check-tag
              :checked="!filterTags.length"
              @change="clearTagFilter"
              class="cyber-check-tag"
            >
              全部
            </el-check-tag>
            <el-check-tag
              v-for="tag in allTags"
              :key="tag"
              :checked="filterTags.includes(tag)"
              @change="(val) => handleTagFilterToggle(tag, val)"
              class="cyber-check-tag"
            >
              {{ tag }}
            </el-check-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 文档卡片网格 -->
    <div class="documents-grid" v-loading="loading">
      <div v-if="filteredDocuments.length === 0" class="empty-state card card-glass">
        <el-empty description="未找到匹配的文档" />
      </div>
      
      <div
        v-for="doc in paginatedDocuments"
        :key="doc.id"
        class="doc-card card card-glass"
        :class="{ 'inactive': !doc.is_active }"
      >
        <div class="doc-header">
          <div class="doc-title-area">
            <h3 class="doc-title">{{ doc.title }}</h3>
            <span class="doc-id">ID: {{ doc.id.substring(0, 8) }}...</span>
          </div>
          <div class="doc-status">
            <el-tag :type="doc.is_active ? 'success' : 'info'" size="small" effect="dark" class="status-tag">
              {{ doc.is_active ? '活跃' : '离线' }}
            </el-tag>
          </div>
        </div>

        <div class="doc-meta">
          <div class="meta-item">
            <span class="meta-label">文件名:</span>
            <span class="meta-value">{{ doc.file_name }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">文件类型:</span>
            <span class="meta-value text-primary">{{ doc.file_type.toUpperCase() }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">文件大小:</span>
            <span class="meta-value">{{ formatFileSize(doc.file_size) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">上传时间:</span>
            <span class="meta-value">{{ formatDate(doc.upload_time) }}</span>
          </div>
        </div>

        <div class="doc-description" v-if="doc.description">
          <p>{{ doc.description }}</p>
        </div>

        <div class="doc-tags">
          <el-tag
            v-for="tag in doc.tags"
            :key="tag"
            size="small"
            class="cyber-tag"
          >
            {{ tag }}
          </el-tag>
        </div>

        <div class="doc-actions">
          <el-button-group>
            <el-button size="small" class="btn-cyber-mini" @click="handleEdit(doc)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button
              v-if="doc.is_active"
              size="small"
              type="danger"
              class="btn-cyber-mini danger"
              @click="handleDelete(doc)"
            >
              <el-icon><Delete /></el-icon> 禁用
            </el-button>
            <el-button
              v-else
              size="small"
              type="primary"
              class="btn-cyber-mini success"
              @click="handleActivate(doc)"
            >
              <el-icon><Check /></el-icon> 激活
            </el-button>
          </el-button-group>
        </div>
      </div>
    </div>

    <!-- 分页器 -->
    <div class="pagination-area" v-if="filteredDocuments.length > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        layout="prev, pager, next, total"
        :total="filteredDocuments.length"
        background
        class="cyber-pagination"
      />
    </div>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="同步至系统核心知识库"
      width="600px"
      append-to-body
      class="cyber-dialog"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-position="top">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="uploadForm.title" placeholder="如：虚空系统权限协议" />
        </el-form-item>
        
        <el-form-item label="核心文件" prop="file">
          <el-upload
            class="cyber-upload"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleUploadFileChange"
            :file-list="uploadFileList"
            :limit="1"
            :accept="acceptedFileTypes.map(t => '.' + t).join(',')"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              托拽文档至此，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持: {{ acceptedFileTypesDisplay }}
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item label="系统标签">
          <el-select
            v-model="uploadForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或创建标签"
            style="width: 100%"
          >
            <el-option
              v-for="item in allTags"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="文档描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            rows="3"
            placeholder="对该文档在系统中的作用进行简要描述..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showUploadDialog = false" class="btn-cyber-outline">取消</el-button>
          <el-button type="primary" @click="handleUploadSubmit" :loading="isUploading" class="btn-cyber">
            开始注入
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="修正文档元属性"
      width="600px"
      append-to-body
      class="cyber-dialog"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="editForm.title" />
        </el-form-item>
        
        <el-form-item label="原始文件名">
          <el-input v-model="editForm.file_name" disabled />
        </el-form-item>
        
        <el-form-item label="系统标签">
          <el-select
            v-model="editForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或创建标签"
            style="width: 100%"
          >
            <el-option
              v-for="item in allTags"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="文档描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            rows="3"
          />
        </el-form-item>
        
        <el-form-item label="激活状态">
          <el-switch
            v-model="editForm.is_active"
            active-text="活跃"
            inactive-text="禁用"
            active-color="var(--color-success)"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showEditDialog = false" class="btn-cyber-outline">取消</el-button>
          <el-button type="primary" @click="handleEditSubmit" :loading="isEditing" class="btn-cyber">
            保存修正
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Upload, Refresh, Search, UploadFilled, Edit, Delete, Check } from '@element-plus/icons-vue';
import { ragApi } from '@/api/rag';

// ==================== 响应式状态 ====================

const documents = ref([]);
const allTags = ref([]);
const loading = ref(false);
const searchKeyword = ref('');
const filterTags = ref([]);

// 分页
const currentPage = ref(1);
const pageSize = ref(8);

// 对话框
const showUploadDialog = ref(false);
const showEditDialog = ref(false);
const isUploading = ref(false);
const isEditing = ref(false);

const uploadForm = ref({
  title: '',
  tags: [],
  description: ''
});

const editForm = ref({
  id: '',
  title: '',
  file_name: '',
  tags: [],
  description: '',
  is_active: true
});

const uploadFileList = ref([]);
const acceptedFileTypes = ref(['txt', 'md', 'json', 'csv', 'py', 'js', 'html', 'css', 'xml']);

const uploadFormRef = ref(null);
const editFormRef = ref(null);

// ==================== 计算属性 ====================

const acceptedFileTypesDisplay = computed(() => acceptedFileTypes.value.join(', '));

const filteredDocuments = computed(() => {
  let result = documents.value;
  
  // 标题检索
  if (searchKeyword.value) {
    result = result.filter(doc => 
      doc.title.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
      doc.file_name.toLowerCase().includes(searchKeyword.value.toLowerCase())
    );
  }
  
  // 标签过滤
  if (filterTags.value.length > 0) {
    result = result.filter(doc => 
      filterTags.value.every(t => doc.tags && doc.tags.includes(t))
    );
  }
  
  return result;
});

const paginatedDocuments = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredDocuments.value.slice(start, start + pageSize.value);
});

// ==================== 表单验证规则 ====================
const uploadRules = {
  title: [
    { required: true, message: '请输入文档标题', trigger: 'blur' },
    { min: 2, max: 255, message: '标题长度在 2 到 255 个字符', trigger: 'blur' }
  ]
};

const editRules = {
  title: [
    { required: true, message: '请输入文档标题', trigger: 'blur' },
    { min: 2, max: 255, message: '标题长度在 2 到 255 个字符', trigger: 'blur' }
  ]
};

// ==================== 方法 ====================

const loadTags = async () => {
  try {
    const response = await ragApi.getTags();
    if (response.data.success) {
      allTags.value = response.data.data.tags;
    }
  } catch (error) {
    console.error('加载系统标签失败:', error);
  }
};

const loadDocuments = async () => {
  loading.value = true;
  try {
    const response = await ragApi.listDocuments();
    if (response.data.success) {
      documents.value = response.data.data.documents;
    } else {
      ElMessage.error('数据链同步失败：' + response.data.message);
    }
  } catch (error) {
    ElMessage.error('访问核心库失败：' + (error.response?.data?.message || error.message));
  } finally {
    loading.value = false;
  }
};

const clearTagFilter = () => {
  filterTags.value = [];
};

const handleTagFilterToggle = (tag, active) => {
  if (active) {
    if (!filterTags.value.includes(tag)) filterTags.value.push(tag);
  } else {
    filterTags.value = filterTags.value.filter(t => t !== tag);
  }
  currentPage.value = 1;
};

const handleUploadFileChange = (file, fileList) => {
  uploadFileList.value = fileList;
  if (!uploadForm.value.title && fileList.length > 0) {
    uploadForm.value.title = fileList[0].name.replace(/\.[^/.]+$/, '');
  }
};

const handleUploadSubmit = async () => {
  if (!uploadFileList.value.length) {
    ElMessage.warning('请提供需要注入系统的文档文件');
    return;
  }
  
  const valid = await uploadFormRef.value?.validate();
  if (valid) {
    isUploading.value = true;
    try {
      const formData = new FormData();
      formData.append('file', uploadFileList.value[0].raw);
      formData.append('title', uploadForm.value.title);
      // 后端预期 tags 为逗号分隔字符串
      formData.append('tags', uploadForm.value.tags.join(','));
      formData.append('description', uploadForm.value.description);
      
      const response = await ragApi.uploadDocument(formData);
      if (response.data.success) {
        ElMessage.success('知识注入成功');
        showUploadDialog.value = false;
        resetUploadForm();
        loadDocuments();
        loadTags();
      } else {
        ElMessage.error('注入失败：' + response.data.message);
      }
    } catch (error) {
      ElMessage.error('系统响应异常：' + (error.response?.data?.message || error.message));
    } finally {
      isUploading.value = false;
    }
  }
};

const resetUploadForm = () => {
  uploadForm.value = { title: '', tags: [], description: '' };
  uploadFileList.value = [];
  uploadFormRef.value?.resetFields();
};

const handleEdit = (row) => {
  editForm.value = {
    id: row.id,
    title: row.title,
    file_name: row.file_name,
    tags: Array.isArray(row.tags) ? [...row.tags] : [],
    description: row.description,
    is_active: row.is_active === 1 || row.is_active === true
  };
  showEditDialog.value = true;
};

const handleEditSubmit = async () => {
  const valid = await editFormRef.value?.validate();
  if (valid) {
    isEditing.value = true;
    try {
      const updates = {
        title: editForm.value.title,
        tags: editForm.value.tags,
        description: editForm.value.description,
        is_active: editForm.value.is_active
      };
      
      const response = await ragApi.updateDocument(editForm.value.id, updates);
      if (response.data.success) {
        ElMessage.success('元数据修正成功');
        showEditDialog.value = false;
        loadDocuments();
        loadTags();
      } else {
        ElMessage.error('修正失败：' + response.data.message);
      }
    } catch (error) {
      ElMessage.error('通信失败：' + (error.response?.data?.message || error.message));
    } finally {
      isEditing.value = false;
    }
  }
};

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要禁用该系统文档吗？这可能会影响部分 RAG 功能。', '系统确认', {
      confirmButtonText: '确定禁用',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'cyber-message-box'
    });
    
    const response = await ragApi.deleteDocument(row.id);
    if (response.data.success) {
      ElMessage.success('文档已下线');
      loadDocuments();
    } else {
      ElMessage.error('禁用失败：' + response.data.message);
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作异常：' + (error.response?.data?.message || error.message));
    }
  }
};

const handleActivate = async (row) => {
  try {
    const response = await ragApi.updateDocument(row.id, { is_active: true });
    if (response.data.success) {
      ElMessage.success('文档重新激活');
      loadDocuments();
    } else {
      ElMessage.error('激活失败：' + response.data.message);
    }
  } catch (error) {
    ElMessage.error('通讯异常：' + (error.response?.data?.message || error.message));
  }
};

const syncDatabase = async () => {
  try {
    await ElMessageBox.confirm('是否启动向量索引全量同步？该操作将清理失效的 Chroma 向量。', '索引维护', {
      confirmButtonText: '立即同步',
      cancelButtonText: '暂缓',
      type: 'info',
      customClass: 'cyber-message-box'
    });
    
    const response = await ragApi.syncDatabase();
    if (response.data.success) {
      ElMessage.success('知识库索引同步完成');
      loadDocuments();
    } else {
      ElMessage.error('同步失败：' + response.data.message);
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('维护任务异常：' + (error.response?.data?.message || error.message));
    }
  }
};

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

onMounted(() => {
  loadDocuments();
  loadTags();
});
</script>

<style scoped>
.rag-management {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
  color: var(--color-text-primary);
}

.page-header {
  margin-bottom: 40px;
}

.text-gradient {
  font-size: 2.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, #fff 0%, var(--color-primary-light) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
  margin-bottom: 10px;
}

.text-secondary {
  color: var(--color-text-secondary);
  font-size: 1.1rem;
}

/* 布局卡片 */
.card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  transition: all var(--transition-normal);
}

.card-glass {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  background: rgba(15, 23, 42, 0.6);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* 操作面板 */
.action-card {
  padding: 24px;
  margin-bottom: 40px;
}

.action-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 20px;
}

.primary-actions {
  display: flex;
  gap: 12px;
}

.search-box {
  flex: 1;
  max-width: 400px;
}

.filter-bottom {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border-light);
}

.filter-label {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  padding-top: 4px;
  white-space: nowrap;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 按钮样式 */
.btn-cyber {
  background: var(--color-primary);
  border: none;
  color: #fff;
  font-weight: 600;
  padding: 10px 20px;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
}

.btn-cyber:hover {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
}

.btn-cyber-outline {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-cyber-outline:hover {
  border-color: var(--color-primary);
  color: var(--color-primary-light);
  background: rgba(99, 102, 241, 0.1);
}

.btn-cyber-mini {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  padding: 5px 10px;
}

.btn-cyber-mini:hover {
  color: var(--color-text-primary);
  border-color: var(--color-text-primary);
}

.btn-cyber-mini.danger:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--color-error);
  color: var(--color-error);
}

.btn-cyber-mini.success:hover {
  background: rgba(16, 185, 129, 0.1);
  border-color: var(--color-success);
  color: var(--color-success);
}

/* 文档网格 */
.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.doc-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.doc-card.inactive {
  opacity: 0.7;
  filter: grayscale(0.5);
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.doc-title {
  font-size: 1.125rem;
  font-weight: 700;
  margin: 0 0 4px 0;
  line-height: 1.4;
  word-break: break-word;
}

.doc-id {
  font-family: var(--font-family-mono);
  font-size: 0.7rem;
  color: var(--color-text-muted);
}

.doc-meta {
  font-size: 0.825rem;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
}

.meta-label {
  color: var(--color-text-muted);
}

.meta-value {
  font-weight: 500;
}

.doc-description {
  background: rgba(0, 0, 0, 0.2);
  padding: 10px;
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.doc-description p {
  margin: 0;
  font-size: 0.825rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.doc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 20px;
  flex-grow: 1;
}

.cyber-tag {
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  color: var(--color-primary-light);
  border-radius: 4px;
}

.doc-actions {
  display: flex;
  justify-content: flex-end;
}

/* 交互元素 */
.cyber-check-tag {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 4px;
  transition: all 0.2s;
}

.cyber-check-tag.is-checked {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
}

.cyber-input :deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid var(--color-border);
}

.cyber-input :deep(.el-input__inner) {
  color: #fff !important;
}

/* 分页器 */
.pagination-area {
  margin-top: 40px;
  display: flex;
  justify-content: center;
}

.cyber-pagination :deep(.el-pager li) {
  background: transparent !important;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.cyber-pagination :deep(.el-pager li.is-active) {
  background: var(--color-primary) !important;
  color: #fff !important;
  border-color: var(--color-primary);
}

/* 上传区域 */
.cyber-upload :deep(.el-upload-dragger) {
  background: rgba(0, 0, 0, 0.2);
  border: 2px dashed var(--color-border);
}

.cyber-upload :deep(.el-upload-dragger:hover) {
  border-color: var(--color-primary);
}

/* 动画 */
.fade-in {
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .action-top {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-box {
    max-width: none;
  }
  
  .text-gradient {
    font-size: 2rem;
  }
}
</style>
