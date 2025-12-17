<!--
 * Void System Frontend - Temporary File Upload Component
 * ------------------------------------------
 * 临时文件上传组件，用于会话中上传临时参考文件
-->

<template>
  <div class="temporary-upload">
    <div class="upload-container">
      <el-upload
        :action="uploadAction"
        :auto-upload="false"
        :before-upload="handleBeforeUpload"
        :on-change="handleFileChange"
        :file-list="fileList"
        :limit="maxFiles"
        :on-exceed="handleExceed"
        accept="{{ acceptedFileTypes }}"
        class="upload-dragger"
      >
        <i class="el-icon-upload"></i>
        <div class="el-upload__text">
          将文件拖到此处，或 <em>点击上传</em>
        </div>
        <div class="el-upload__tip" slot="tip">
          支持上传 {{ acceptedFileTypesDisplay }} 文件，单个文件不超过 {{ maxFileSize / 1024 / 1024 }}MB，最多上传 {{ maxFiles }} 个文件
        </div>
      </el-upload>
      
      <div class="upload-actions" v-if="fileList.length > 0">
        <el-button
          type="primary"
          size="small"
          @click="uploadFiles"
          :loading="isUploading"
          :disabled="fileList.length === 0"
        >
          开始上传
        </el-button>
        <el-button
          size="small"
          @click="clearFiles"
          :disabled="fileList.length === 0"
        >
          清空
        </el-button>
      </div>
    </div>
    
    <!-- 已上传文件列表 -->
    <div class="uploaded-files" v-if="uploadedFiles.length > 0">
      <h4 class="section-title">已上传文件 ({{ uploadedFiles.length }})</h4>
      <el-card v-for="file in uploadedFiles" :key="file.file_id" shadow="hover" class="file-card">
        <div class="file-info">
          <i class="el-icon-document"></i>
          <div class="file-details">
            <div class="file-name">{{ file.file_name }}</div>
            <div class="file-meta">
              <span>{{ formatFileSize(file.file_size) }}</span>
              <span>{{ formatUploadTime(file.upload_time) }}</span>
            </div>
          </div>
          <el-button
            type="danger"
            size="mini"
            @click="deleteFile(file.file_id)"
            :loading="deletingFiles.includes(file.file_id)"
          >
            删除
          </el-button>
        </div>
        <div class="file-preview" v-if="file.content_preview">
          <h5>内容预览：</h5>
          <pre>{{ file.content_preview }}</pre>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TemporaryUpload',
  props: {
    /**
     * 会话ID
     */
    sessionId: {
      type: String,
      required: true
    },
    /**
     * 最大文件数
     */
    maxFiles: {
      type: Number,
      default: 5
    },
    /**
     * 最大文件大小（字节）
     */
    maxFileSize: {
      type: Number,
      default: 2 * 1024 * 1024 // 2MB
    },
    /**
     * 允许的文件类型
     */
    acceptedFileTypes: {
      type: Array,
      default: () => ['txt', 'md', 'json', 'csv', 'pdf', 'doc', 'docx']
    }
  },
  data() {
    return {
      /**
       * 上传队列
       */
      fileList: [],
      /**
       * 已上传文件列表
       */
      uploadedFiles: [],
      /**
       * 是否正在上传
       */
      isUploading: false,
      /**
       * 正在删除的文件ID列表
       */
      deletingFiles: [],
      /**
       * 上传动作（未使用，因为我们使用自定义上传）
       */
      uploadAction: '#'
    };
  },
  computed: {
    /**
     * 接受的文件类型显示文本
     */
    acceptedFileTypesDisplay() {
      return this.acceptedFileTypes.join(', ');
    }
  },
  mounted() {
    // 组件挂载时获取会话上下文，加载已上传的文件
    this.loadSessionFiles();
  },
  methods: {
    /**
     * 加载会话中的文件
     */
    async loadSessionFiles() {
      try {
        const { sessionApi } = await import('../api/session');
        const response = await sessionApi.getSessionContext(this.sessionId);
        if (response.data.success) {
          this.uploadedFiles = response.data.data.files || [];
        }
      } catch (error) {
        this.$message.error('加载会话文件失败：' + (error.response?.data?.message || error.message));
      }
    },
    
    /**
     * 处理文件选择前的验证
     */
    handleBeforeUpload(file) {
      // 验证文件大小
      if (file.size > this.maxFileSize) {
        this.$message.error(`文件大小不能超过 ${this.maxFileSize / 1024 / 1024}MB`);
        return false;
      }
      
      // 验证文件类型
      const fileExtension = file.name.split('.').pop().toLowerCase();
      if (!this.acceptedFileTypes.includes(fileExtension)) {
        this.$message.error(`不支持的文件类型，仅支持：${this.acceptedFileTypes.join(', ')}`);
        return false;
      }
      
      return true;
    },
    
    /**
     * 处理文件选择
     */
    handleFileChange(file, fileList) {
      this.fileList = fileList;
    },
    
    /**
     * 处理文件超出限制
     */
    handleExceed(files, fileList) {
      this.$message.warning(`最多只能上传 ${this.maxFiles} 个文件`);
    },
    
    /**
     * 开始上传文件
     */
    async uploadFiles() {
      if (this.fileList.length === 0) return;
      
      this.isUploading = true;
      
      try {
        const { sessionApi } = await import('../api/session');
        
        for (const file of this.fileList) {
          const formData = new FormData();
          formData.append('file', file.raw);
          
          const response = await sessionApi.uploadTemporaryFile(this.sessionId, formData);
          if (response.data.success) {
            this.$message.success(`文件 ${file.name} 上传成功`);
          } else {
            this.$message.error(`文件 ${file.name} 上传失败：${response.data.message}`);
          }
        }
        
        // 清空上传队列
        this.fileList = [];
        
        // 重新加载已上传文件
        await this.loadSessionFiles();
      } catch (error) {
        this.$message.error('文件上传失败：' + (error.response?.data?.message || error.message));
      } finally {
        this.isUploading = false;
      }
    },
    
    /**
     * 清空上传队列
     */
    clearFiles() {
      this.fileList = [];
    },
    
    /**
     * 删除文件
     */
    async deleteFile(fileId) {
      this.deletingFiles.push(fileId);
      
      try {
        const { sessionApi } = await import('../api/session');
        const response = await sessionApi.deleteTemporaryFile(fileId);
        
        if (response.data.success) {
          this.$message.success('文件删除成功');
          // 从列表中移除
          this.uploadedFiles = this.uploadedFiles.filter(file => file.file_id !== fileId);
        } else {
          this.$message.error('文件删除失败：' + response.data.message);
        }
      } catch (error) {
        this.$message.error('文件删除失败：' + (error.response?.data?.message || error.message));
      } finally {
        this.deletingFiles = this.deletingFiles.filter(id => id !== fileId);
      }
    },
    
    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * 格式化上传时间
     */
    formatUploadTime(timeString) {
      const date = new Date(timeString);
      return date.toLocaleString();
    }
  }
};
</script>

<style scoped>
.temporary-upload {
  margin: 16px 0;
}

.upload-container {
  margin-bottom: 24px;
}

.upload-dragger {
  margin-bottom: 16px;
}

.upload-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.uploaded-files {
  margin-top: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #333;
}

.file-card {
  margin-bottom: 16px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.file-info i {
  font-size: 24px;
  color: #6366f1;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.file-meta {
  font-size: 12px;
  color: #999;
  display: flex;
  gap: 16px;
}

.file-preview {
  margin-top: 12px;
  padding: 12px;
  background-color: #f5f5f5;
  border-radius: 6px;
}

.file-preview h5 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
}

.file-preview pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
  background-color: #fff;
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}
</style>
