<!--
 * Void System Frontend - RAG Management Page
 * ------------------------------------------
 * 管理员专用RAG文档管理页面
-->

<template>
  <div class="void-page-container rag-management void-fade-in">
    <!-- 页面头部 -->
    <header class="page-header">
      <h1 class="logo-text"><span class="void-text-gradient">RAG</span> 引擎</h1>
      <p class="subtitle">管理员终端：矩阵同步与知识库编排。</p>
    </header>

    <!-- 操作与过滤栏 -->
    <section class="action-section">
      <div class="void-card action-card">
        <div class="action-top">
          <div class="primary-actions">
            <el-button type="primary" class="void-btn primary" @click="showUploadDialog = true">
              <el-icon><Upload /></el-icon> 注入数据
            </el-button>
            <el-button class="void-btn secondary" @click="syncDatabase">
              <el-icon><Refresh /></el-icon> 同步向量库
            </el-button>
          </div>
          <div class="search-box">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索档案模式..."
              prefix-icon="Search"
              clearable
              class="void-input"
            />
          </div>
        </div>

        <div class="filter-bottom">
          <div class="filter-label">矩阵过滤器:</div>
          <div class="filter-tags">
            <el-check-tag
              :checked="!filterTags.length"
              @change="clearTagFilter"
              class="void-tag clickable"
            >
              所有通道
            </el-check-tag>
            <el-check-tag
              v-for="tag in allTags"
              :key="tag"
              :checked="filterTags.includes(tag)"
              @change="(val) => handleTagFilterToggle(tag, val)"
              class="void-tag clickable"
              :class="{ 'primary': filterTags.includes(tag) }"
            >
              {{ tag }}
            </el-check-tag>
          </div>
        </div>
      </div>
    </section>

    <!-- 文档卡片网格 -->
    <section class="documents-grid" v-loading="loading">
      <div v-if="filteredDocuments.length === 0" class="void-empty-state">
        <el-empty description="未匹配到当前模式的切片。" />
      </div>
      
      <div
        v-for="doc in paginatedDocuments"
        :key="doc.id"
        class="void-card doc-card"
        :class="{ 'inactive': !doc.is_active }"
      >
        <div class="card-glow"></div>
        <div class="doc-header">
          <div class="doc-title-area">
            <h3 class="doc-title">{{ doc.title }}</h3>
            <span class="doc-id">切片ID: {{ doc.id.substring(0, 8) }}</span>
          </div>
          <div class="doc-status">
            <div class="void-status-pill" :class="getStatusType(doc.parse_status, doc.is_active)">
              {{ getStatusText(doc.parse_status, doc.is_active) }}
            </div>
          </div>
        </div>

        <div v-if="doc.parse_status === 'failed' && doc.error_message" class="error-strip">
          <el-icon><Warning /></el-icon> {{ doc.error_message }}
        </div>

        <div class="doc-meta">
          <div class="meta-item">
            <span class="meta-label">来源</span>
            <span class="meta-value">{{ doc.file_name }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">格式</span>
            <span class="meta-value primary-text">{{ doc.file_type.toUpperCase() }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">负载</span>
            <span class="meta-value">{{ formatFileSize(doc.file_size) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">已索引</span>
            <span class="meta-value">{{ formatDate(doc.upload_time) }}</span>
          </div>
        </div>
Line 106:           <div class="meta-item">
Line 107:             <span class="meta-label">已索引</span>
Line 108:             <span class="meta-value">{{ formatDate(doc.upload_time) }}</span>
Line 109:           </div>

        <div class="doc-description" v-if="doc.description">
          <p>{{ doc.description }}</p>
        </div>

        <div class="doc-tags">
          <el-tag
            v-for="tag in doc.tags"
            :key="tag"
            size="small"
            class="void-tag sm"
          >
            {{ tag }}
          </el-tag>
        </div>

        <div class="doc-actions">
          <div class="action-dock">
            <el-button size="small" class="void-btn sm" @click="handleEdit(doc)">
              <el-icon><Edit /></el-icon> 修正
            </el-button>
            <el-button
              v-if="doc.is_active"
              size="small"
              class="void-btn danger sm"
              @click="handleDelete(doc)"
            >
              <el-icon><Delete /></el-icon> 清除
            </el-button>
            <el-button
              v-else
              size="small"
              class="void-btn primary sm"
              @click="handleActivate(doc)"
            >
              <el-icon><Check /></el-icon> 唤醒
            </el-button>
          </div>
        </div>

        <!-- 处理进度条 -->
        <div v-if="doc.parse_status === 'processing'" class="void-shimmer-line"></div>
      </div>
    </section>

    <!-- 分页器 -->
    <footer class="pagination-area" v-if="filteredDocuments.length > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        layout="prev, pager, next"
        :total="filteredDocuments.length"
        class="void-pagination"
      />
    </footer>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="系统切片注入"
      width="600px"
      append-to-body
      class="void-dialog"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-position="top" class="void-form">
        <div class="void-form-group">
          <label>切片标识符</label>
          <el-input v-model="uploadForm.title" placeholder="定义识别协议..." class="void-input" />
        </div>
        
        <div class="void-form-group">
          <label>核心缓冲区</label>
          <el-upload
            class="void-upload"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleUploadFileChange"
            :file-list="uploadFileList"
            :limit="1"
            :accept="acceptedFileTypes.map(t => '.' + t).join(',')"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将切片拖入此处或 <em>手动部署</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                兼容协议: {{ acceptedFileTypesDisplay }}
              </div>
            </template>
          </el-upload>
        </div>
        
        <div class="void-form-group">
          <label>索引分类器</label>
          <el-select
            v-model="uploadForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="分配分类标签..."
            class="void-select"
            style="width: 100%"
          >
            <el-option
              v-for="item in allTags"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </div>
        
        <div class="void-form-group">
          <label>神经描述词</label>
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            rows="3"
            placeholder="为 RAG 集成定义神经上下文..."
            class="void-input"
          />
        </div>
      </el-form>
      <template #footer>
        <div class="modal-footer">
          <el-button @click="showUploadDialog = false" class="void-btn text">中止</el-button>
          <el-button type="primary" @click="handleUploadSubmit" :loading="isUploading" class="void-btn primary">
            执行注入
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="元数据修正"
      width="600px"
      append-to-body
      class="void-dialog"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top" class="void-form">
        <div class="void-form-group">
          <label>切片标识符</label>
          <el-input v-model="editForm.title" class="void-input" />
        </div>
        
        <div class="void-form-group">
          <label>原始文件引用</label>
          <el-input v-model="editForm.file_name" disabled class="void-input" />
        </div>
        
        <div class="void-form-group">
          <label>索引分类器</label>
          <el-select
            v-model="editForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="分配分类标签..."
            class="void-select"
            style="width: 100%"
          >
            <el-option
              v-for="item in allTags"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </div>
        
        <div class="void-form-group">
          <label>神经描述词</label>
          <el-input
            v-model="editForm.description"
            type="textarea"
            rows="3"
            class="void-input"
          />
        </div>
        
        <div class="void-form-group flex justify-between items-center">
          <label>神经状态</label>
          <el-switch
            v-model="editForm.is_active"
            active-text="活跃"
            inactive-text="停滞"
            active-color="var(--color-primary)"
          />
        </div>
      </el-form>
      <template #footer>
        <div class="modal-footer">
          <el-button @click="showEditDialog = false" class="void-btn text">舍弃</el-button>
          <el-button type="primary" @click="handleEditSubmit" :loading="isEditing" class="void-btn primary">
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
const acceptedFileTypes = ref(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'md', 'json', 'csv', 'py', 'js', 'html', 'css', 'xml']);

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

// 状态解析方法
const getStatusText = (status, isActive) => {
  if (status === 'processing') return '正在注入向量库...';
  if (status === 'failed') return '注入失败';
  return isActive ? '核心活跃' : '离线已禁用';
};

const getStatusType = (status, isActive) => {
  if (status === 'processing') return 'warning';
  if (status === 'failed') return 'danger';
  return isActive ? 'success' : 'info';
};

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
      customClass: 'void-message-box'
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
      customClass: 'void-message-box'
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
  min-height: 100vh;
}

.page-header {
  margin-bottom: var(--spacing-xxxl);
  text-align: center;
}

.action-section {
  margin-bottom: var(--spacing-xl);
}

.action-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.primary-actions {
  display: flex;
  gap: var(--spacing-md);
}

.search-box {
  flex: 1;
  max-width: 400px;
}

.filter-bottom {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color-light);
}

.filter-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 800;
  padding-top: 4px;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* Documents Grid */
.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-lg);
}

.doc-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  position: relative;
  overflow: hidden;
}

.doc-card.inactive {
  opacity: 0.4;
  filter: grayscale(0.5);
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.doc-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.doc-id {
  font-family: var(--font-family-mono);
  font-size: 0.65rem;
  color: var(--text-muted);
}

.doc-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.8rem;
  padding: var(--spacing-md) 0;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color-light);
  padding-bottom: 4px;
}

.meta-label { 
  color: var(--text-muted); 
  font-size: 0.7rem;
  font-weight: 800;
}

.meta-value { 
  color: var(--text-secondary); 
  font-weight: 500; 
}

.doc-description {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: var(--spacing-sm);
}

.doc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.doc-actions {
  margin-top: auto;
  padding-top: var(--spacing-md);
  display: flex;
  justify-content: flex-end;
}

.action-dock {
  display: flex;
  gap: var(--spacing-xs);
}

.error-strip {
  background: var(--color-danger-transparent);
  border-left: 3px solid var(--color-danger);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--color-danger-light);
  display: flex;
  align-items: center;
  gap: 6px;
}

.void-shimmer-line {
  height: 3px;
  width: 100%;
  position: absolute;
  bottom: 0;
  left: 0;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
  animation: voidShimmerAnim 2s infinite linear;
}

.pagination-area {
  margin-top: var(--spacing-xxl);
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .action-top { flex-direction: column; align-items: stretch; }
  .search-box { max-width: none; }
}
</style>
