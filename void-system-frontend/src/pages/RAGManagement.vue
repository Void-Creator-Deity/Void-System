<template>
  <div class="knowledge-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">管理员</p>
        <h1>共享资料维护</h1>
        <p>让工作台在回答、规划和建议时引用可靠的共享内容。</p>
      </div>
      <div class="header-actions">
        <el-button @click="rebuildKnowledgeIndex"><el-icon><Refresh /></el-icon>重新整理资料</el-button>
        <el-button type="primary" @click="showUploadDialog = true"><el-icon><Upload /></el-icon>添加资料</el-button>
      </div>
    </header>

    <div v-if="loadError" class="page-error" role="alert">
      <el-icon><WarningFilled /></el-icon>
      <div>
        <strong>共享资料暂时无法读取</strong>
        <p>{{ loadError }}</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadDocuments">重新加载</el-button>
    </div>

    <template v-else>
    <section class="overview" aria-label="资料状态概览">
      <div><span>资料总数</span><strong>{{ documents.length }}</strong></div>
      <div><span>正在引用</span><strong class="success-value">{{ activeDocumentCount }}</strong></div>
      <div><span>正在处理</span><strong class="warning-value">{{ processingDocumentCount }}</strong></div>
      <div><span>需要关注</span><strong :class="failedDocumentCount ? 'danger-value' : ''">{{ failedDocumentCount }}</strong></div>
    </section>

    <section class="library-controls">
      <el-input v-model="searchKeyword" clearable placeholder="搜索资料标题、文件名或说明" class="search-input" @input="currentPage = 1">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-segmented v-model="statusFilter" :options="statusOptions" @change="currentPage = 1" aria-label="筛选资料状态" />
      <el-select v-model="filterTags" multiple collapse-tags collapse-tags-tooltip clearable placeholder="按分类筛选" class="tag-filter" @change="currentPage = 1">
        <el-option v-for="tag in allTags" :key="tag" :label="tag" :value="tag" />
      </el-select>
    </section>

    <section class="library-section" v-loading="loading">
      <div v-if="!paginatedDocuments.length" class="empty-state">
        <el-empty :description="documents.length ? '没有匹配的资料' : '还没有共享资料'">
          <el-button v-if="!documents.length" type="primary" @click="showUploadDialog = true"><el-icon><Upload /></el-icon>添加第一份资料</el-button>
        </el-empty>
      </div>

      <article v-for="doc in paginatedDocuments" :key="doc.id" class="document-row" :class="{ 'document-row--muted': !isDocumentActive(doc), 'document-row--problem': doc.parse_status === 'failed' }">
        <div class="document-main">
          <div class="document-title">
            <h2>{{ doc.title || doc.file_name || '未命名资料' }}</h2>
            <span class="status-badge" :class="getStatusClass(doc)">{{ getStatusLabel(doc) }}</span>
          </div>
          <p v-if="doc.description" class="document-description">{{ doc.description }}</p>
          <p v-else class="document-description document-description--empty">没有说明</p>
          <div v-if="doc.parse_status === 'failed' && doc.error_message" class="problem-note"><el-icon><Warning /></el-icon><span>{{ doc.error_message }}</span></div>
          <div v-if="doc.tags?.length" class="tag-list"><span v-for="tag in doc.tags" :key="tag">{{ tag }}</span></div>
        </div>

        <div class="document-meta">
          <span :title="doc.file_name"><strong>文件</strong>{{ doc.file_name || '-' }}</span>
          <span><strong>格式</strong>{{ formatFileType(doc.file_type) }}</span>
          <span><strong>更新</strong>{{ formatDate(doc.upload_time) }}</span>
        </div>

        <div class="document-actions">
          <el-tooltip content="编辑资料" placement="top"><el-button text circle aria-label="编辑资料" @click="handleEdit(doc)"><el-icon><Edit /></el-icon></el-button></el-tooltip>
          <el-button v-if="isDocumentActive(doc)" plain size="small" @click="handlePause(doc)">暂停引用</el-button>
          <el-button v-else plain type="primary" size="small" @click="handleActivate(doc)">恢复引用</el-button>
        </div>
      </article>
    </section>

    <footer v-if="filteredDocuments.length > pageSize" class="pagination-area"><el-pagination v-model:current-page="currentPage" :page-size="pageSize" layout="prev, pager, next" :total="filteredDocuments.length" /></footer>
    </template>

    <el-dialog v-model="showUploadDialog" title="添加共享资料" width="min(92vw, 620px)" append-to-body @closed="resetUploadForm">
      <p class="dialog-intro">添加后，系统会自动整理内容；完成后即可用于共享问答和规划。</p>
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-position="top">
        <el-form-item label="资料标题" prop="title"><el-input v-model="uploadForm.title" placeholder="例如：产品使用说明" maxlength="255" show-word-limit /></el-form-item>
        <el-form-item label="资料文件" required>
          <el-upload class="upload-area" drag action="#" :auto-upload="false" :on-change="handleUploadFileChange" :file-list="uploadFileList" :limit="1" :accept="acceptedFileTypes.map(type => '.' + type).join(',')">
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖入文件，或点击选择</div>
            <template #tip><div class="el-upload__tip">支持 {{ acceptedFileTypesDisplay }}</div></template>
          </el-upload>
        </el-form-item>
        <el-form-item label="分类标签"><el-select v-model="uploadForm.tags" multiple filterable allow-create default-first-option placeholder="选择或新建分类" style="width:100%"><el-option v-for="tag in allTags" :key="tag" :label="tag" :value="tag" /></el-select></el-form-item>
        <el-form-item label="资料说明"><el-input v-model="uploadForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="说明这份资料适合解决什么问题" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showUploadDialog = false">取消</el-button><el-button type="primary" :loading="isUploading" @click="handleUploadSubmit">添加资料</el-button></template>
    </el-dialog>

    <el-dialog v-model="showEditDialog" title="编辑共享资料" width="min(92vw, 620px)" append-to-body>
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="资料标题" prop="title"><el-input v-model="editForm.title" maxlength="255" show-word-limit /></el-form-item>
        <el-form-item label="原始文件"><el-input v-model="editForm.file_name" disabled /></el-form-item>
        <el-form-item label="分类标签"><el-select v-model="editForm.tags" multiple filterable allow-create default-first-option placeholder="选择或新建分类" style="width:100%"><el-option v-for="tag in allTags" :key="tag" :label="tag" :value="tag" /></el-select></el-form-item>
        <el-form-item label="资料说明"><el-input v-model="editForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        <div class="reference-switch"><div><strong>允许引用</strong><p>关闭后，系统不会在新的回答中引用这份资料。</p></div><el-switch v-model="editForm.is_active" aria-label="允许引用" /></div>
      </el-form>
      <template #footer><el-button @click="showEditDialog = false">取消</el-button><el-button type="primary" :loading="isEditing" @click="handleEditSubmit">保存更改</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Edit, Refresh, Search, Upload, UploadFilled, Warning, WarningFilled } from '@element-plus/icons-vue'
import { getApiErrorMessage } from '@/api/index'
import { knowledgeAdministrationApi } from '@/api/knowledgeAdministration'

const documents = ref([])
const allTags = ref([])
const loading = ref(false)
const loadError = ref('')
const searchKeyword = ref('')
const filterTags = ref([])
const statusFilter = ref('全部')
const currentPage = ref(1)
const pageSize = 10
const statusOptions = ['全部', '正在引用', '处理中', '需处理', '已暂停']
const showUploadDialog = ref(false)
const showEditDialog = ref(false)
const isUploading = ref(false)
const isEditing = ref(false)
const uploadForm = ref({ title: '', tags: [], description: '' })
const editForm = ref({ id: '', title: '', file_name: '', tags: [], description: '', is_active: true })
const uploadFileList = ref([])
const acceptedFileTypes = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'md', 'json', 'csv', 'py', 'js', 'html', 'css', 'xml']
const uploadFormRef = ref(null)
const editFormRef = ref(null)
const acceptedFileTypesDisplay = computed(() => acceptedFileTypes.map(type => `.${type}`).join(' / '))
const activeDocumentCount = computed(() => documents.value.filter(isDocumentActive).length)
const processingDocumentCount = computed(() => documents.value.filter(doc => doc.parse_status === 'processing').length)
const failedDocumentCount = computed(() => documents.value.filter(doc => doc.parse_status === 'failed').length)
const filteredDocuments = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return documents.value.filter(doc => {
    const matchesKeyword = !keyword || [doc.title, doc.file_name, doc.description].filter(Boolean).some(value => String(value).toLowerCase().includes(keyword))
    const matchesTags = !filterTags.value.length || filterTags.value.every(tag => doc.tags?.includes(tag))
    const matchesStatus = statusFilter.value === '全部'
      || (statusFilter.value === '正在引用' && isDocumentActive(doc) && doc.parse_status !== 'processing')
      || (statusFilter.value === '处理中' && doc.parse_status === 'processing')
      || (statusFilter.value === '需处理' && doc.parse_status === 'failed')
      || (statusFilter.value === '已暂停' && !isDocumentActive(doc))
    return matchesKeyword && matchesTags && matchesStatus
  })
})
const paginatedDocuments = computed(() => filteredDocuments.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize))
const uploadRules = { title: [{ required: true, message: '请输入资料标题', trigger: 'blur' }, { min: 2, max: 255, message: '标题长度为 2 至 255 个字符', trigger: 'blur' }] }
const editRules = { title: [{ required: true, message: '请输入资料标题', trigger: 'blur' }, { min: 2, max: 255, message: '标题长度为 2 至 255 个字符', trigger: 'blur' }] }

function isDocumentActive(doc) { return doc?.is_active === true || doc?.is_active === 1 }
function getStatusLabel(doc) { if (doc.parse_status === 'processing') return '处理中'; if (doc.parse_status === 'failed') return '需处理'; return isDocumentActive(doc) ? '正在引用' : '已暂停' }
function getStatusClass(doc) { if (doc.parse_status === 'processing') return 'is-processing'; if (doc.parse_status === 'failed') return 'is-problem'; return isDocumentActive(doc) ? 'is-active' : 'is-paused' }
function formatFileSize(bytes) { if (!bytes) return '0 B'; const sizes = ['B', 'KB', 'MB', 'GB']; const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), sizes.length - 1); return `${parseFloat((bytes / Math.pow(1024, index)).toFixed(2))} ${sizes[index]}` }
function formatFileType(fileType) { return fileType ? String(fileType).toUpperCase() : '-' }
function formatDate(dateString) { return dateString ? new Date(dateString).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-' }

async function loadTags() { try { const data = await knowledgeAdministrationApi.getTags(); allTags.value = data?.tags || [] } catch { ElMessage.warning('资料分类暂时无法加载') } }
async function loadDocuments() { loading.value = true; loadError.value = ''; try { const data = await knowledgeAdministrationApi.listDocuments(); documents.value = data?.documents || []; if ((currentPage.value - 1) * pageSize >= filteredDocuments.value.length) currentPage.value = 1 } catch (error) { loadError.value = getApiErrorMessage(error, '请检查服务连接后重试。') } finally { loading.value = false } }
function handleUploadFileChange(file, fileList) { uploadFileList.value = fileList.slice(-1); if (!uploadForm.value.title && uploadFileList.value.length) uploadForm.value.title = uploadFileList.value[0].name.replace(/\.[^/.]+$/, '') }
function resetUploadForm() { uploadForm.value = { title: '', tags: [], description: '' }; uploadFileList.value = []; uploadFormRef.value?.resetFields() }
async function handleUploadSubmit() { if (!uploadFileList.value.length) return ElMessage.warning('请选择要添加的资料文件'); const valid = await uploadFormRef.value?.validate(); if (!valid) return; isUploading.value = true; try { const formData = new FormData(); formData.append('file', uploadFileList.value[0].raw); formData.append('title', uploadForm.value.title); formData.append('tags', uploadForm.value.tags.join(',')); formData.append('description', uploadForm.value.description); await knowledgeAdministrationApi.uploadDocument(formData); ElMessage.success('资料已添加，正在整理内容'); showUploadDialog.value = false; resetUploadForm(); await Promise.all([loadDocuments(), loadTags()]) } catch (error) { ElMessage.error(getApiErrorMessage(error, '添加资料失败')) } finally { isUploading.value = false } }
function handleEdit(row) { editForm.value = { id: row.id, title: row.title || '', file_name: row.file_name || '', tags: Array.isArray(row.tags) ? [...row.tags] : [], description: row.description || '', is_active: isDocumentActive(row) }; showEditDialog.value = true }
async function handleEditSubmit() { const valid = await editFormRef.value?.validate(); if (!valid) return; isEditing.value = true; try { await knowledgeAdministrationApi.updateDocument(editForm.value.id, { title: editForm.value.title, tags: editForm.value.tags, description: editForm.value.description, is_active: editForm.value.is_active }); ElMessage.success('资料已保存'); showEditDialog.value = false; await Promise.all([loadDocuments(), loadTags()]) } catch (error) { ElMessage.error(getApiErrorMessage(error, '保存资料失败')) } finally { isEditing.value = false } }
async function handlePause(row) { try { await ElMessageBox.confirm('暂停后，新的回答和规划不会再引用这份资料。', '暂停引用', { confirmButtonText: '暂停引用', cancelButtonText: '取消', type: 'warning' }); await knowledgeAdministrationApi.updateDocument(row.id, { is_active: false }); ElMessage.success('已暂停引用'); await loadDocuments() } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error, '操作失败')) } }
async function handleActivate(row) { try { await knowledgeAdministrationApi.updateDocument(row.id, { is_active: true }); ElMessage.success('已恢复引用'); await loadDocuments() } catch (error) { ElMessage.error(getApiErrorMessage(error, '操作失败')) } }
async function rebuildKnowledgeIndex() { try { await ElMessageBox.confirm('系统会重新整理共享资料的可引用状态。适合资料导入异常或迁移后使用。', '重新整理资料', { confirmButtonText: '开始整理', cancelButtonText: '取消', type: 'info' }); await knowledgeAdministrationApi.rebuildIndex(); ElMessage.success('资料已重新整理'); await loadDocuments() } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error, '重新整理失败')) } }

onMounted(() => { loadDocuments(); loadTags() })
</script>

<style scoped>
.knowledge-page { width:min(100%, 1080px); margin:0 auto; padding:32px 0 64px; color:var(--text-primary); }.page-header { display:flex; align-items:flex-end; justify-content:space-between; gap:24px; padding:0 2px 25px; border-bottom:1px solid var(--border-color); }.page-kicker { margin:0 0 6px; color:var(--color-primary); font-size:12px; font-weight:700; }.page-header h1 { margin:0; font-size:28px; line-height:1.2; }.page-header p:not(.page-kicker) { margin:9px 0 0; color:var(--text-secondary); }.header-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; }.page-error { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:14px; margin:22px 2px 0; padding:16px; border:1px solid color-mix(in srgb,var(--color-danger) 26%,var(--border-color)); border-radius:7px; background:color-mix(in srgb,var(--color-danger) 5%,var(--bg-secondary)); }.page-error > .el-icon { color:var(--color-danger); font-size:22px; }.page-error strong { font-size:14px; }.page-error p { margin:4px 0 0; color:var(--text-secondary); font-size:13px; line-height:1.5; }.overview { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); margin:0 2px; border-bottom:1px solid var(--border-color-light); }.overview > div { display:grid; gap:7px; padding:22px 18px 22px 0; border-right:1px solid var(--border-color-light); }.overview > div:not(:first-child) { padding-left:18px; }.overview > div:last-child { border-right:0; }.overview span { color:var(--text-muted); font-size:13px; }.overview strong { font-size:25px; line-height:1; }.success-value { color:var(--color-success); }.warning-value { color:var(--color-warning); }.danger-value { color:var(--color-danger); }.library-controls { display:grid; grid-template-columns:minmax(200px,1fr) auto minmax(160px,220px); align-items:center; gap:12px; padding:22px 2px; border-bottom:1px solid var(--border-color-light); }.search-input :deep(.el-input__wrapper),.tag-filter :deep(.el-select__wrapper) { min-height:40px; border:1px solid var(--border-color); border-radius:7px; background:var(--bg-secondary); box-shadow:none; }.library-controls :deep(.el-segmented) { --el-segmented-bg-color:var(--bg-tertiary); }.library-section { min-height:240px; }.empty-state { display:grid; place-items:center; min-height:300px; }.document-row { display:grid; grid-template-columns:minmax(0,1fr) minmax(200px,260px) auto; align-items:center; gap:22px; padding:21px 2px; border-bottom:1px solid var(--border-color-light); }.document-row--muted { opacity:.7; }.document-row--problem { background:color-mix(in srgb, var(--color-danger) 3%, transparent); }.document-title { display:flex; align-items:center; flex-wrap:wrap; gap:9px; }.document-title h2 { margin:0; font-size:16px; line-height:1.4; }.status-badge { display:inline-flex; align-items:center; min-height:23px; padding:3px 7px; border:1px solid transparent; border-radius:5px; font-size:11px; font-weight:700; }.status-badge.is-active { color:var(--color-success); border-color:color-mix(in srgb,var(--color-success) 24%,var(--border-color)); background:color-mix(in srgb,var(--color-success) 8%,var(--bg-secondary)); }.status-badge.is-processing { color:#9a651a; border-color:color-mix(in srgb,#d99a35 26%,var(--border-color)); background:color-mix(in srgb,#d99a35 8%,var(--bg-secondary)); }.status-badge.is-problem { color:var(--color-danger); border-color:color-mix(in srgb,var(--color-danger) 22%,var(--border-color)); background:color-mix(in srgb,var(--color-danger) 7%,var(--bg-secondary)); }.status-badge.is-paused { color:var(--text-muted); border-color:var(--border-color); background:var(--bg-tertiary); }.document-description { max-width:640px; margin:7px 0 0; color:var(--text-secondary); font-size:13px; line-height:1.55; }.document-description--empty { color:var(--text-muted); }.problem-note { display:flex; align-items:flex-start; gap:6px; margin-top:10px; color:var(--color-danger); font-size:12px; line-height:1.5; }.problem-note .el-icon { flex:0 0 auto; margin-top:2px; }.tag-list { display:flex; flex-wrap:wrap; gap:5px; margin-top:10px; }.tag-list span { padding:3px 6px; border:1px solid var(--border-color-light); border-radius:4px; color:var(--text-secondary); background:var(--bg-tertiary); font-size:11px; }.document-meta { display:grid; gap:7px; min-width:0; }.document-meta span { display:grid; grid-template-columns:34px minmax(0,1fr); gap:7px; overflow:hidden; color:var(--text-secondary); font-size:12px; white-space:nowrap; text-overflow:ellipsis; }.document-meta strong { color:var(--text-muted); font-weight:500; }.document-actions { display:flex; align-items:center; justify-content:flex-end; gap:5px; }.pagination-area { display:flex; justify-content:center; padding:24px 0; }.dialog-intro { margin:0 0 20px; color:var(--text-secondary); font-size:13px; line-height:1.55; }.upload-area :deep(.el-upload-dragger) { border-radius:7px; background:var(--bg-secondary); }.reference-switch { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:14px 0 0; border-top:1px solid var(--border-color-light); }.reference-switch strong { font-size:14px; }.reference-switch p { margin:4px 0 0; color:var(--text-muted); font-size:12px; line-height:1.45; }@media (max-width:900px) { .library-controls { grid-template-columns:1fr 1fr; }.search-input { grid-column:1/-1; }.tag-filter { min-width:0; }.document-row { grid-template-columns:minmax(0,1fr) auto; }.document-meta { grid-column:1/-1; grid-template-columns:repeat(3,minmax(0,1fr)); }.document-actions { grid-column:2; grid-row:1; align-self:start; } }@media (max-width:640px) { .page-error { grid-template-columns:auto minmax(0,1fr); }.page-error .el-button { grid-column:1/-1; width:100%; }.knowledge-page { padding:22px 0 48px; }.page-header { align-items:flex-start; flex-direction:column; gap:15px; }.header-actions { justify-content:flex-start; }.overview { grid-template-columns:repeat(2,minmax(0,1fr)); }.overview > div { border-bottom:1px solid var(--border-color-light); }.overview > div:nth-child(2) { border-right:0; }.overview > div:nth-child(3),.overview > div:nth-child(4) { border-bottom:0; }.library-controls { grid-template-columns:1fr; }.search-input { grid-column:auto; }.document-row { grid-template-columns:minmax(0,1fr); gap:14px; }.document-actions { grid-column:auto; grid-row:auto; justify-content:flex-start; }.document-meta { grid-column:auto; grid-template-columns:1fr; }.document-meta span { grid-template-columns:34px minmax(0,1fr); }.reference-switch { align-items:flex-start; flex-direction:column; }.reference-switch .el-switch { align-self:flex-end; } }
</style>
