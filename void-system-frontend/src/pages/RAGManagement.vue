<!--
 * Void System Frontend - RAG Management Page
 * ------------------------------------------
 * 管理员专用RAG文档管理页面
-->

<template>
  <div class="rag-management">
    <div class="page-header">
      <h1>🔧 RAG文档管理</h1>
      <p>系统知识库文档的增删改查管理</p>
    </div>
    
    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon> 上传文档
      </el-button>
      <el-button @click="syncDatabase">
        <el-icon><Refresh /></el-icon> 同步数据库
      </el-button>
      <el-input
        v-model="searchKeyword"
        placeholder="搜索文档标题"
        prefix-icon="el-icon-search"
        class="search-input"
      >
      </el-input>
    </div>
    
    <!-- 文档列表 -->
    <el-table
      :data="filteredDocuments"
      stripe
      border
      style="width: 100%"
      class="documents-table"
    >
      <el-table-column prop="id" label="文档ID" width="180" show-overflow-tooltip>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip>
      </el-table-column>
      <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip>
      </el-table-column>
      <el-table-column prop="file_type" label="文件类型" width="100">
      </el-table-column>
      <el-table-column prop="file_size" label="文件大小" width="120">
        <template slot-scope="scope">
          {{ formatFileSize(scope.row.file_size) }}
        </template>
      </el-table-column>
      <el-table-column prop="upload_time" label="上传时间" width="180">
        <template slot-scope="scope">
          {{ formatDate(scope.row.upload_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template slot-scope="scope">
          <el-tag type="success" v-if="scope.row.is_active">活跃</el-tag>
          <el-tag type="danger" v-else>已删除</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="tags" label="标签" min-width="150">
        <template slot-scope="scope">
          <el-tag v-for="tag in scope.row.tags" :key="tag" size="small" class="tag-item">
            {{ tag }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template slot-scope="scope">
          <el-button
            size="small"
            @click="handleEdit(scope.row)"
            v-if="scope.row.is_active"
          >
            编辑
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="handleDelete(scope.row)"
            v-if="scope.row.is_active"
          >
            删除
          </el-button>
          <el-button
            size="small"
            type="primary"
            @click="handleActivate(scope.row)"
            v-else
          >
            激活
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        background
        layout="prev, pager, next, jumper, total"
        :total="filteredDocuments.length"
        :page-size="pageSize"
        v-model="currentPage"
      >
      </el-pagination>
    </div>
    
    <!-- 上传对话框 -->
    <el-dialog
      title="上传系统RAG文档"
      v-model="showUploadDialog"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="100px">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="uploadForm.title" placeholder="请输入文档标题"></el-input>
        </el-form-item>
        
        <el-form-item label="文件" prop="file">
          <el-upload
            :auto-upload="false"
            :on-change="handleUploadFileChange"
            :file-list="uploadFileList"
            :accept="acceptedFileTypes.map(type => '.' + type).join(',')"
            action="#"
            name="file"
            class="upload-dragger"
          >
            <i class="el-icon-upload"></i>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击上传</em>
            </div>
            <div class="el-upload__tip" slot="tip">
              支持上传 {{ acceptedFileTypesDisplay }} 文件
            </div>
          </el-upload>
        </el-form-item>
        
        <el-form-item label="标签">
          <el-input
            v-model="uploadForm.tagsInput"
            placeholder="请输入标签，逗号分隔"
          ></el-input>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            rows="3"
            placeholder="请输入文档描述"
          ></el-input>
        </el-form-item>
      </el-form>
      
      <span slot="footer" class="dialog-footer">
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUploadSubmit" :loading="isUploading">
          上传
        </el-button>
      </span>
    </el-dialog>
    
    <!-- 编辑对话框 -->
    <el-dialog
      title="编辑RAG文档"
      v-model="showEditDialog"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="editForm.title" placeholder="请输入文档标题"></el-input>
        </el-form-item>
        
        <el-form-item label="文件名" disabled>
          <el-input v-model="editForm.file_name" disabled></el-input>
        </el-form-item>
        
        <el-form-item label="标签">
          <el-input
            v-model="editForm.tagsInput"
            placeholder="请输入标签，逗号分隔"
          ></el-input>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            rows="3"
            placeholder="请输入文档描述"
          ></el-input>
        </el-form-item>
        
        <el-form-item label="状态">
          <el-switch v-model="editForm.is_active" active-text="活跃" inactive-text="禁用"></el-switch>
        </el-form-item>
      </el-form>
      
      <span slot="footer" class="dialog-footer">
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleEditSubmit" :loading="isEditing">
          保存
        </el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Upload, Refresh } from '@element-plus/icons-vue';
import { ragApi } from '@/api/rag';

// ==================== 响应式状态 ====================

// 文档列表
const documents = ref([]);

// 搜索关键字
const searchKeyword = ref('');

// 分页信息
const currentPage = ref(1);
const pageSize = ref(10);

// 对话框状态
const showUploadDialog = ref(false);
const showEditDialog = ref(false);

// 加载状态
const isUploading = ref(false);
const isEditing = ref(false);

// 表单数据
const uploadForm = ref({
  title: '',
  tagsInput: '',
  description: ''
});

const editForm = ref({
  id: '',
  title: '',
  file_name: '',
  tagsInput: '',
  description: '',
  is_active: true
});

// 文件上传
const uploadFileList = ref([]);
const acceptedFileTypes = ref(['txt', 'md', 'json', 'csv', 'py', 'js', 'html', 'css', 'xml']);

// 表单引用
const uploadFormRef = ref(null);
const editFormRef = ref(null);

// ==================== 计算属性 ====================

// 接受的文件类型显示文本
const acceptedFileTypesDisplay = computed(() => {
  return acceptedFileTypes.value.join(', ');
});

// 过滤后的文档列表
const filteredDocuments = computed(() => {
  if (!searchKeyword.value) {
    return documents.value;
  }
  return documents.value.filter(doc => 
    doc.title.includes(searchKeyword.value)
  );
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

/**
 * 加载文档列表
 */
const loadDocuments = async () => {
  try {
    const response = await ragApi.listDocuments();
    if (response.data.success) {
      documents.value = response.data.data.documents;
    } else {
      ElMessage.error('加载文档列表失败：' + response.data.message);
    }
  } catch (error) {
    ElMessage.error('加载文档列表失败：' + (error.response?.data?.message || error.message));
  }
};

/**
 * 处理文件选择
 */
const handleUploadFileChange = (file, fileList) => {
  uploadFileList.value = fileList;
  // 如果没有填写标题，自动使用文件名作为标题
  if (!uploadForm.value.title && fileList.length > 0) {
    const fileName = fileList[0].name;
    uploadForm.value.title = fileName.replace(/\.[^/.]+$/, ''); // 移除扩展名
  }
};

/**
 * 提交上传
 */
const handleUploadSubmit = async () => {
  if (!uploadFileList.value || uploadFileList.value.length === 0) {
    ElMessage.warning('请选择要上传的文件');
    return;
  }
  
  const valid = await uploadFormRef.value?.validate();
  if (valid) {
    isUploading.value = true;
    
    try {
      const formData = new FormData();
      
      // 添加文件
      formData.append('file', uploadFileList.value[0].raw);
      
      // 添加表单数据
      formData.append('title', uploadForm.value.title);
      formData.append('tags', uploadForm.value.tagsInput);
      formData.append('description', uploadForm.value.description);
      
      const response = await ragApi.uploadDocument(formData);
      if (response.data.success) {
        ElMessage.success('文档上传成功');
        showUploadDialog.value = false;
        resetUploadForm();
        loadDocuments();
      } else {
        ElMessage.error('文档上传失败：' + response.data.message);
      }
    } catch (error) {
      ElMessage.error('文档上传失败：' + (error.response?.data?.message || error.message));
    } finally {
      isUploading.value = false;
    }
  }
};

/**
 * 重置上传表单
 */
const resetUploadForm = () => {
  uploadForm.value = {
    title: '',
    tagsInput: '',
    description: ''
  };
  uploadFileList.value = [];
  uploadFormRef.value?.resetFields();
};

/**
 * 处理编辑
 */
const handleEdit = (row) => {
  editForm.value = {
    id: row.id,
    title: row.title,
    file_name: row.file_name,
    tagsInput: Array.isArray(row.tags) ? row.tags.join(', ') : '',
    description: row.description,
    is_active: row.is_active
  };
  showEditDialog.value = true;
};

/**
 * 提交编辑
 */
const handleEditSubmit = async () => {
  const valid = await editFormRef.value?.validate();
  if (valid) {
    isEditing.value = true;
    
    try {
      // 将标签字符串转换为数组
      const tags = editForm.value.tagsInput
        ? editForm.value.tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag)
        : [];
      
      const updates = {
        title: editForm.value.title,
        tags: tags,
        description: editForm.value.description,
        is_active: editForm.value.is_active
      };
      
      const response = await ragApi.updateDocument(editForm.value.id, updates);
      if (response.data.success) {
        ElMessage.success('文档更新成功');
        showEditDialog.value = false;
        loadDocuments();
      } else {
        ElMessage.error('文档更新失败：' + response.data.message);
      }
    } catch (error) {
      ElMessage.error('文档更新失败：' + (error.response?.data?.message || error.message));
    } finally {
      isEditing.value = false;
    }
  }
};

/**
 * 处理删除
 */
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该文档吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    const response = await ragApi.deleteDocument(row.id);
    if (response.data.success) {
      ElMessage.success('文档删除成功');
      loadDocuments();
    } else {
      ElMessage.error('文档删除失败：' + response.data.message);
    }
  } catch (error) {
    if (error === 'cancel') {
      ElMessage.info('已取消删除');
    } else {
      ElMessage.error('文档删除失败：' + (error.response?.data?.message || error.message));
    }
  }
};

/**
 * 处理激活
 */
const handleActivate = async (row) => {
  try {
    const response = await ragApi.updateDocument(row.id, { is_active: true });
    if (response.data.success) {
      ElMessage.success('文档激活成功');
      loadDocuments();
    } else {
      ElMessage.error('文档激活失败：' + response.data.message);
    }
  } catch (error) {
    ElMessage.error('文档激活失败：' + (error.response?.data?.message || error.message));
  }
};

/**
 * 同步数据库
 */
const syncDatabase = async () => {
  try {
    await ElMessageBox.confirm('确定要同步Chroma与数据库吗？', '同步确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    });
    
    const response = await ragApi.syncDatabase();
    if (response.data.success) {
      ElMessage.success('数据库同步成功：' + response.data.message);
      loadDocuments();
    } else {
      ElMessage.error('数据库同步失败：' + response.data.message);
    }
  } catch (error) {
    if (error === 'cancel') {
      ElMessage.info('已取消同步');
    } else {
      ElMessage.error('数据库同步失败：' + (error.response?.data?.message || error.message));
    }
  }
};

/**
 * 格式化文件大小
 */
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * 格式化日期
 */
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

// ==================== 生命周期 ====================

// 页面挂载时加载文档列表
onMounted(() => {
  loadDocuments();
});
</script>

<style scoped>
.rag-management {
  padding: 24px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin: 0 0 8px 0;
  color: #333;
}

.page-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  background-color: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.search-input {
  width: 300px;
  margin-left: auto;
}

.documents-table {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.pagination {
  background-color: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.upload-dragger {
  margin: 8px 0;
}

.tag-item {
  margin-right: 4px;
}

.upload-form-item {
  margin-bottom: 20px;
}
</style>
