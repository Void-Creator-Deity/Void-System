<template>
  <div class="knowledge-page">
    <div class="knowledge-shell">
      <header class="page-intro">
        <div>
          <p class="eyebrow">个人资料库</p>
          <h1>把资料变成随时可问的答案</h1>
          <p class="page-copy">上传工作文件，系统会在后台整理内容。资料准备好后，你可以直接围绕它提问。</p>
        </div>
        <div class="page-intro__actions"><el-button plain :loading="rebuilding" @click="rebuildKnowledge">重新整理资料</el-button><el-button type="primary" class="primary-action" @click="triggerFileSelect"><el-icon><Upload /></el-icon>添加资料</el-button></div>
      </header>

      <section class="upload-panel" :class="{ 'is-uploading': uploading }">
        <input ref="fileInput" class="file-input" type="file" multiple accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.csv,.jpg,.jpeg,.png" @change="onFileSelect" />
        <div class="drop-zone" role="button" tabindex="0" aria-label="选择要添加的资料" @dragover.prevent @drop.prevent="onDrop" @click="triggerFileSelect" @keydown.enter.prevent="triggerFileSelect" @keydown.space.prevent="triggerFileSelect">
          <template v-if="!uploading">
            <span class="upload-icon"><el-icon><Upload /></el-icon></span>
            <div><h2>拖进来，或选择文件</h2><p>支持 PDF、Word、Excel、图片和文本文件，单个文件最大 50 MB。</p></div>
          </template>
          <template v-else>
            <el-progress :percentage="uploadProgress" :stroke-width="8" :show-text="false" />
            <div class="uploading-copy"><strong>{{ currentFileName }}</strong><span>{{ uploadMessage }}</span></div>
          </template>
        </div>
        <div class="upload-options">
          <el-input v-model="uploadTitle" placeholder="资料名称（留空则使用文件名）" />
          <el-select v-model="uploadTags" aria-label="资料标签" multiple filterable allow-create default-first-option placeholder="添加标签，便于以后筛选"><el-option v-for="tag in knownTags" :key="tag" :label="tag" :value="tag" /></el-select>
        </div>
      </section>

      <section v-if="stats" class="overview" aria-label="资料概览">
        <article class="metric"><span class="metric-icon"><el-icon><DocumentIcon /></el-icon></span><div><span>使用中的资料</span><strong>{{ stats.total_documents || 0 }}</strong></div></article>
        <article class="metric metric-ready"><span class="metric-icon"><el-icon><CircleCheck /></el-icon></span><div><span>可以提问</span><strong>{{ stats.completed_documents || 0 }}</strong></div></article>
        <article class="metric metric-progress"><span class="metric-icon"><el-icon><Clock /></el-icon></span><div><span>正在整理</span><strong>{{ inProgressCount }}</strong></div></article>
        <article class="metric metric-size"><span class="metric-icon"><el-icon><FolderOpened /></el-icon></span><div><span>已用空间</span><strong>{{ formatFileSize(stats.total_size) }}</strong></div></article>
      </section>

      <section class="library-layout">
        <main class="library-panel">
          <header class="panel-heading">
            <div><h2>{{ retentionView === 'archived' ? '回收站' : '我的资料' }}</h2><p>{{ retentionView === 'archived' ? '归档资料不会参与回答，可随时恢复或永久清除。' : totalCount + ' 份资料，按状态和内容快速找到需要的内容。' }}</p></div>
            <div class="library-toolbar">
              <el-segmented v-model="retentionView" :options="retentionOptions" size="small" aria-label="资料范围" @change="changeRetentionView" />
              <div class="library-controls" :class="{ 'is-archived': retentionView === 'archived' }">
                <el-input v-if="retentionView === 'active'" v-model="searchQuery" clearable placeholder="在资料中查找" @clear="clearSearch" @keyup.enter="performKnowledgeSearch"><template #prefix><el-icon><Search /></el-icon></template></el-input>
                <el-select v-if="retentionView === 'active'" v-model="filterStatus" aria-label="资料状态" @change="resetAndLoadDocuments"><el-option label="全部状态" value="" /><el-option label="整理中" value="processing" /><el-option label="可以提问" value="completed" /><el-option label="整理失败" value="failed" /></el-select>
                <el-tooltip content="刷新资料列表" placement="top"><el-button circle aria-label="刷新资料列表" :loading="loading" @click="refreshLibrary"><el-icon><RefreshRight /></el-icon></el-button></el-tooltip>
              </div>
            </div>
          </header>

          <div v-if="searchResults.length" class="search-results">
            <div class="search-results-heading"><div><strong>找到 {{ searchResults.length }} 条相关内容</strong><span>结果来自已整理的资料</span></div><el-button text @click="clearSearch">清除结果</el-button></div>
            <button v-for="(result, index) in searchResults" :key="result.chunk_id || index" class="search-result" @click="openSearchResult(result)"><span class="result-index">{{ index + 1 }}</span><span class="result-content">{{ result.content }}</span></button>
          </div>

          <div v-if="loading" class="state-panel"><el-icon class="is-loading"><Loading /></el-icon><span>正在加载资料…</span></div>
          <el-empty v-else-if="!documents.length" :description="retentionView === 'archived' ? '回收站是空的' : '这里还没有资料，先上传一份开始吧。'" />
          <div v-else class="document-list">
            <article v-for="doc in documents" :key="doc.doc_id" class="document-row">
              <div class="document-type"><el-icon><component :is="getFileIcon(doc.file_type)" /></el-icon></div>
              <div class="document-body">
                <div class="document-title-row"><h3>{{ doc.title || '未命名资料' }}</h3><el-tag size="small" effect="plain" :type="retentionView === 'archived' ? 'info' : getStatusTagType(documentStatus(doc))">{{ retentionView === 'archived' ? '已归档' : getStatusText(documentStatus(doc)) }}</el-tag></div>
                <p class="document-meta">{{ fileTypeLabel(doc.file_type) }} <i></i> {{ formatFileSize(doc.file_size) }} <i></i> {{ formatDate(doc.created_at) }}</p>
                <p v-if="documentStatus(doc) === 'failed' && documentError(doc)" class="document-error">{{ documentError(doc) }}</p>
                <p v-else class="document-preview">{{ doc.content_preview || statusDescription(documentStatus(doc)) }}</p>
                <div v-if="doc.tags?.length" class="tag-list"><el-tag v-for="tag in doc.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag></div>
              </div>
              <div class="document-actions">
                <template v-if="retentionView === 'archived'">
                  <el-tooltip content="恢复到资料库" placement="top"><el-button type="primary" circle aria-label="恢复资料" @click="restoreDoc(doc)"><el-icon><RefreshLeft /></el-icon></el-button></el-tooltip>
                  <el-tooltip content="查看内容" placement="top"><el-button circle aria-label="查看资料内容" @click="previewDocument(doc)"><el-icon><View /></el-icon></el-button></el-tooltip>
                  <el-tooltip content="永久清除" placement="top"><el-button circle type="danger" plain aria-label="永久清除资料" @click="purgeDoc(doc)"><el-icon><Delete /></el-icon></el-button></el-tooltip>
                </template>
                <template v-else>
                  <el-tooltip v-if="canAsk(doc)" content="围绕这份资料提问" placement="top"><el-button type="primary" circle aria-label="围绕资料提问" @click="askWithDocument(doc)"><el-icon><ChatLineRound /></el-icon></el-button></el-tooltip>
                  <el-tooltip content="查看内容" placement="top"><el-button circle aria-label="查看资料内容" @click="previewDocument(doc)"><el-icon><View /></el-icon></el-button></el-tooltip>
                  <el-dropdown trigger="click" @command="command => handleDocumentAction(command, doc)"><el-button circle aria-label="更多操作"><el-icon><MoreFilled /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="edit">编辑资料</el-dropdown-item><el-dropdown-item command="archive" divided>移到回收站</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
                </template>
              </div>
            </article>
          </div>
          <footer v-if="totalCount > pageSize" class="pagination-footer"><el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :total="totalCount" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="handleSizeChange" @current-change="handleCurrentChange" /></footer>
        </main>

        <aside class="activity-panel">
          <header class="activity-heading"><div><h2>最近提问</h2><p>你最近在资料库里查过什么。</p></div><el-icon><ChatDotRound /></el-icon></header>
          <div v-if="activityLoading" class="activity-loading"><el-icon class="is-loading"><Loading /></el-icon> 正在整理记录…</div>
          <el-empty v-else-if="!activity.length" :image-size="72" description="还没有提问记录" />
          <ol v-else class="activity-list"><li v-for="item in activity" :key="item.activity_id"><p>{{ item.question }}</p><div class="activity-meta"><span>{{ formatRelativeDate(item.created_at) }}</span><span>{{ item.source_count }} 份资料</span></div><div v-if="item.sources?.length" class="activity-sources"><span v-for="source in item.sources.slice(0, 2)" :key="source.document_id || source.title">{{ source.title }}</span></div></li></ol>
        </aside>
      </section>
    </div>

    <el-dialog v-model="editDialogVisible" title="编辑资料" width="min(92vw, 520px)" destroy-on-close>
      <el-form label-position="top"><el-form-item label="资料名称"><el-input v-model="editingDoc.title" maxlength="120" show-word-limit /></el-form-item><el-form-item label="标签"><el-select v-model="editingDoc.tags" aria-label="资料标签" multiple filterable allow-create default-first-option style="width: 100%" placeholder="添加标签"><el-option v-for="tag in knownTags" :key="tag" :label="tag" :value="tag" /></el-select></el-form-item></el-form>
      <template #footer><el-button @click="editDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveDocumentEdit">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="previewDialogVisible" :title="previewTitle || '资料内容'" width="min(94vw, 760px)" destroy-on-close><pre class="document-content">{{ previewContent }}</pre></el-dialog>
    <el-dialog v-model="qaDialogVisible" :title="selectedDocForQA ? '询问：' + selectedDocForQA.title : '围绕资料提问'" width="min(94vw, 760px)" destroy-on-close @closed="closeQA">
      <div class="qa-thread"><el-empty v-if="!qaMessages.length" :image-size="84" description="用自然语言提出问题，我会只依据这份资料作答。" /><article v-for="message in qaMessages" :key="message.id" class="qa-message" :class="message.type"><span class="message-label">{{ message.type === 'question' ? '你的问题' : '基于资料的回答' }}</span><p v-if="message.type === 'question'">{{ message.content }}</p><div v-else-if="message.type === 'typing'" class="thinking"><el-icon class="is-loading"><Loading /></el-icon> 正在查找资料内容…</div><div v-else class="answer-markdown" v-html="answerHtmlForMessage(message)"></div><div v-if="message.sources?.length" class="answer-sources"><span>参考资料</span><el-tag v-for="source in message.sources" :key="source.document_id || source.title" size="small" effect="plain">{{ source.title || '当前资料' }}</el-tag></div></article></div>
      <div class="qa-composer"><el-input v-model="qaQuestion" type="textarea" :rows="3" maxlength="1000" show-word-limit resize="none" placeholder="例如：这份资料里最重要的结论是什么？" @keydown.ctrl.enter.prevent="sendQuestion" /><el-button type="primary" :loading="asking" :disabled="!qaQuestion.trim()" @click="sendQuestion">发送</el-button></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChatDotRound, ChatLineRound, CircleCheck, Clock, Delete, Document as DocumentIcon, FolderOpened, Loading, MoreFilled, Picture as PictureIcon, RefreshLeft, RefreshRight, Search, Upload, View } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { documentApi } from '@/api/document'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'
import { renderAssistantMarkdown } from '@/utils/markdownThink'

const fileInput = ref(null)
const uploading = ref(false)
const rebuilding = ref(false)
const uploadProgress = ref(0)
const uploadMessage = ref('')
const currentFileName = ref('')
const uploadTitle = ref('')
const uploadTags = ref([])
const loading = ref(false)
const documents = ref([])
const stats = ref(null)
const filterStatus = ref('')
const retentionView = ref('active')
const retentionOptions = [{ label: '使用中', value: 'active' }, { label: '回收站', value: 'archived' }]
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const searchQuery = ref('')
const searchResults = ref([])
const editDialogVisible = ref(false)
const editingDoc = ref({})
const saving = ref(false)
const previewDialogVisible = ref(false)
const previewContent = ref('')
const previewTitle = ref('')
const qaDialogVisible = ref(false)
const selectedDocForQA = ref(null)
const qaQuestion = ref('')
const qaMessages = ref([])
const asking = ref(false)
const activity = ref([])
const activityLoading = ref(false)

const knownTags = computed(() => [...new Set(documents.value.flatMap(doc => doc.tags || []))].slice(0, 30))
const inProgressCount = computed(() => documents.value.filter(doc => ['queued', 'pending', 'processing', 'parsed', 'indexing'].includes(documentStatus(doc))).length || stats.value?.status_stats?.processing || 0)
const getFileIcon = fileType => ['jpg', 'jpeg', 'png', 'gif'].includes(String(fileType || '').toLowerCase()) ? PictureIcon : DocumentIcon
const documentStatus = doc => doc.ingestion?.status || doc.knowledge_status?.status || doc.parse_status || 'pending'
const documentError = doc => doc.ingestion?.error_message || doc.knowledge_status?.error_message || doc.error_message
const canAsk = doc => !doc.is_archived && documentStatus(doc) === 'completed'
function getStatusText(status) { return ({ queued: '等待整理', pending: '等待整理', processing: '正在整理', parsed: '正在整理', indexing: '正在整理', completed: '可以提问', failed: '整理失败' })[status] || '等待整理' }
function getStatusTagType(status) { return ({ queued: 'info', pending: 'info', processing: 'warning', parsed: 'warning', indexing: 'warning', completed: 'success', failed: 'danger' })[status] || 'info' }
function statusDescription(status) { return ({ queued: '已收到资料，稍后会开始整理。', pending: '已收到资料，稍后会开始整理。', processing: '正在读取内容并整理为可提问的资料。', parsed: '正在整理内容，马上就可以提问。', indexing: '正在整理内容，马上就可以提问。', completed: '资料已整理完成，可以围绕它提问。', failed: '这份资料暂时无法整理。' })[status] || '正在整理资料内容。' }
function fileTypeLabel(fileType) { const labels = { pdf: 'PDF 文档', doc: 'Word 文档', docx: 'Word 文档', xls: 'Excel 表格', xlsx: 'Excel 表格', csv: 'CSV 表格', txt: '文本', md: 'Markdown', jpg: '图片', jpeg: '图片', png: '图片', gif: '图片' }; return labels[String(fileType || '').toLowerCase()] || String(fileType || '资料').toUpperCase() }
function formatFileSize(bytes) { if (!bytes) return '0 字节'; const units = ['字节', 'KB', 'MB', 'GB']; const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1); return Number(bytes / 1024 ** index).toFixed(index ? 1 : 0) + ' ' + units[index] }
function formatDate(value) { if (!value) return '时间未知'; return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value)) }
function formatRelativeDate(value) { const date = new Date(value); const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000)); if (minutes < 1) return '刚刚'; if (minutes < 60) return minutes + ' 分钟前'; if (minutes < 1440) return Math.floor(minutes / 60) + ' 小时前'; if (minutes < 10080) return Math.floor(minutes / 1440) + ' 天前'; return formatDate(value) }
function answerHtmlForMessage(message) { return message.type === 'answer' ? renderAssistantMarkdown(message.content || '') : '' }
function triggerFileSelect() { fileInput.value?.click() }
function onDrop(event) { handleFileUpload(Array.from(event.dataTransfer.files || [])) }
function onFileSelect(event) { handleFileUpload(Array.from(event.target.files || [])); event.target.value = '' }

async function handleFileUpload(files) {
  if (!files.length || uploading.value) return
  const formData = new FormData(); files.forEach(file => formData.append('files', file))
  if (uploadTitle.value.trim()) formData.append('title', uploadTitle.value.trim())
  if (uploadTags.value.length) formData.append('tags', JSON.stringify(uploadTags.value))
  uploading.value = true; uploadProgress.value = 0; currentFileName.value = files.length === 1 ? files[0].name : '正在上传 ' + files.length + ' 份资料'; uploadMessage.value = '正在上传…'
  try { await documentApi.upload(formData, event => { uploadProgress.value = event.total ? Math.round((event.loaded * 100) / event.total) : 0; uploadMessage.value = uploadProgress.value >= 100 ? '上传完成，正在加入整理队列…' : '正在上传 ' + uploadProgress.value + '%' }); uploadMessage.value = '上传完成，资料会在后台自动整理。'; uploadTitle.value = ''; uploadTags.value = []; ElMessage.success('资料已上传，正在后台整理'); await Promise.all([loadDocuments(), loadStats()]) } catch (error) { uploadMessage.value = '上传失败'; ElMessage.error(formatAxiosErrorMessage(error, '上传失败，请稍后再试')) } finally { window.setTimeout(() => { uploading.value = false }, 1200) }
}
async function loadDocuments() { loading.value = true; try { const data = await documentApi.list({ retention: retentionView.value, status: retentionView.value === 'active' ? (filterStatus.value || undefined) : undefined, limit: pageSize.value, offset: (currentPage.value - 1) * pageSize.value }); documents.value = data?.documents || []; totalCount.value = data?.pagination?.total ?? documents.value.length } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '资料列表加载失败')) } finally { loading.value = false } }
async function loadStats() { try { stats.value = await documentApi.getStats() } catch (error) { console.warn('无法加载资料统计', error) } }
async function loadActivity() { activityLoading.value = true; try { activity.value = (await documentApi.getActivity(10))?.activity || [] } catch (error) { console.warn('无法加载提问记录', error) } finally { activityLoading.value = false } }
async function refreshLibrary() { await Promise.all([loadDocuments(), loadStats(), loadActivity()]) }
function resetAndLoadDocuments() { currentPage.value = 1; loadDocuments() }
function changeRetentionView() { currentPage.value = 1; filterStatus.value = ''; clearSearch(); loadDocuments() }
function handleSizeChange(size) { pageSize.value = size; currentPage.value = 1; loadDocuments() }
function handleCurrentChange(page) { currentPage.value = page; loadDocuments() }
async function performKnowledgeSearch() { if (!searchQuery.value.trim()) return; try { const data = await documentApi.search(searchQuery.value.trim()); searchResults.value = data?.results || []; if (!searchResults.value.length) ElMessage.info('没有找到相关内容') } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '暂时无法在资料中查找')) } }
function clearSearch() { searchResults.value = []; searchQuery.value = '' }
function openSearchResult(result) { previewTitle.value = '查找结果'; previewContent.value = result.content || '暂无内容'; previewDialogVisible.value = true }
function editDocument(doc) { editingDoc.value = { doc_id: doc.doc_id, title: doc.title || '', tags: [...(doc.tags || [])] }; editDialogVisible.value = true }
async function saveDocumentEdit() { if (!editingDoc.value.title?.trim()) { ElMessage.warning('请填写资料名称'); return } saving.value = true; try { await documentApi.update(editingDoc.value.doc_id, { title: editingDoc.value.title.trim(), tags: editingDoc.value.tags || [] }); editDialogVisible.value = false; await loadDocuments(); ElMessage.success('资料已更新') } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '保存失败')) } finally { saving.value = false } }
async function previewDocument(doc) { try { const data = await documentApi.get(doc.doc_id, { includeArchived: retentionView.value === 'archived' }); previewTitle.value = doc.title || '资料内容'; previewContent.value = data?.content_preview || '暂无可预览内容'; previewDialogVisible.value = true } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '暂时无法查看这份资料')) } }
function askWithDocument(doc) { selectedDocForQA.value = doc; qaQuestion.value = ''; qaMessages.value = []; qaDialogVisible.value = true }
async function sendQuestion() { if (!qaQuestion.value.trim() || !selectedDocForQA.value || asking.value) return; const question = qaQuestion.value.trim(); qaQuestion.value = ''; qaMessages.value.push({ id: Date.now(), type: 'question', content: question }); const answerId = Date.now() + 1; qaMessages.value.push({ id: answerId, type: 'typing', content: '' }); asking.value = true; try { const data = await documentApi.ask(question, [selectedDocForQA.value.doc_id]); const index = qaMessages.value.findIndex(message => message.id === answerId); if (index >= 0) qaMessages.value[index] = { id: answerId, type: 'answer', content: data?.answer || '没有找到可以支持回答的内容。', sources: data?.sources || [] }; loadActivity() } catch (error) { const index = qaMessages.value.findIndex(message => message.id === answerId); if (index >= 0) qaMessages.value[index] = { id: answerId, type: 'answer', content: formatAxiosErrorMessage(error, '暂时无法完成回答，请稍后再试。'), sources: [] } } finally { asking.value = false } }
function closeQA() { selectedDocForQA.value = null; qaMessages.value = []; qaQuestion.value = '' }
async function archiveDoc(doc) { try { await ElMessageBox.confirm('“' + (doc.title || '这份资料') + '”会移到回收站，并停止参与回答。之后仍可恢复。', '移到回收站', { type: 'warning', confirmButtonText: '移到回收站', cancelButtonText: '取消' }); await documentApi.archive(doc.doc_id); ElMessage.success('资料已移到回收站'); await Promise.all([loadDocuments(), loadStats()]) } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(formatAxiosErrorMessage(error, '暂时无法归档资料')) } }
async function restoreDoc(doc) { try { await documentApi.restore(doc.doc_id); ElMessage.success('资料已恢复，可以继续用于回答'); await Promise.all([loadDocuments(), loadStats()]) } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '暂时无法恢复资料')) } }
async function purgeDoc(doc) { try { await ElMessageBox.confirm('永久清除后将无法恢复“' + (doc.title || '这份资料') + '”。', '永久清除资料', { type: 'error', confirmButtonText: '永久清除', cancelButtonText: '取消' }); await documentApi.purge(doc.doc_id); ElMessage.success('资料已永久清除'); await Promise.all([loadDocuments(), loadStats()]) } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(formatAxiosErrorMessage(error, '暂时无法永久清除资料')) } }
function handleDocumentAction(command, doc) { if (command === 'edit') editDocument(doc); if (command === 'archive') archiveDoc(doc) }
async function rebuildKnowledge() {
  rebuilding.value = true
  try {
    await documentApi.rebuildIndex()
    ElMessage.success('资料已进入重新整理队列，完成后会自动更新状态。')
    await refreshLibrary()
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, '暂时无法重新整理资料。'))
  } finally {
    rebuilding.value = false
  }
}

onMounted(() => { refreshLibrary() })
</script>

<style scoped>
.knowledge-page { min-height: 100%; background: var(--bg-primary); color: var(--text-primary); }.knowledge-shell { width: min(1440px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 64px; }.page-intro { display: flex; align-items: end; justify-content: space-between; gap: 32px; padding: 6px 2px 32px; }.eyebrow { margin: 0 0 10px; color: var(--color-accent); font-size: 13px; font-weight: 700; letter-spacing: 0; }h1, h2, h3, p { margin-top: 0; }h1, h2, h3 { color: var(--text-primary); letter-spacing: 0; }h1 { margin-bottom: 12px; font-size: 40px; line-height: 1.18; }.page-copy { max-width: 680px; margin-bottom: 0; color: var(--text-secondary); font-size: 15px; line-height: 1.7; }.page-intro__actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; } .primary-action { min-height: 42px; border-color: var(--color-primary); background: var(--color-primary); box-shadow: none; }
.upload-panel { display: grid; grid-template-columns: minmax(0, 1fr) minmax(330px, .65fr); border: 1px solid var(--border-color); background: var(--bg-secondary); box-shadow: 0 12px 30px var(--shadow-md); }.drop-zone { display: flex; align-items: center; gap: 18px; min-height: 154px; padding: 28px 32px; border-right: 1px solid var(--border-color-light); cursor: pointer; transition: background-color .2s ease; }.drop-zone:hover { background: color-mix(in srgb, var(--color-primary) 6%, var(--bg-secondary)); }.drop-zone:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -3px; }.drop-zone h2 { margin-bottom: 6px; font-size: 18px; }.drop-zone p { margin-bottom: 0; color: var(--text-secondary); font-size: 14px; line-height: 1.6; }.upload-icon, .metric-icon, .document-type { display: inline-grid; place-items: center; flex: 0 0 auto; }.upload-icon { width: 46px; height: 46px; border-radius: 8px; background: color-mix(in srgb, var(--color-primary) 12%, var(--bg-secondary)); color: var(--color-primary); font-size: 22px; }.upload-options { display: grid; align-content: center; gap: 12px; padding: 24px; }.file-input { display: none; }.is-uploading .drop-zone { cursor: default; }.is-uploading .el-progress { width: min(230px, 48%); }.uploading-copy { display: grid; gap: 4px; }.uploading-copy span { color: var(--text-secondary); font-size: 14px; }
.overview { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 22px 0; }.metric { display: flex; align-items: center; gap: 13px; min-width: 0; padding: 16px; border: 1px solid var(--border-color); background: var(--bg-secondary); }.metric-icon { width: 38px; height: 38px; border-radius: 8px; background: var(--bg-tertiary); color: var(--text-secondary); }.metric-ready .metric-icon { background: color-mix(in srgb, var(--color-success) 13%, var(--bg-secondary)); color: var(--color-success); }.metric-progress .metric-icon { background: color-mix(in srgb, var(--color-warning) 13%, var(--bg-secondary)); color: var(--color-warning); }.metric-size .metric-icon { background: color-mix(in srgb, var(--color-primary) 10%, var(--bg-secondary)); color: var(--color-primary); }.metric div { display: grid; gap: 3px; }.metric span:not(.metric-icon) { color: var(--text-muted); font-size: 13px; }.metric strong { color: var(--text-primary); font-size: 19px; font-variant-numeric: tabular-nums; }
.library-layout { display: grid; grid-template-columns: minmax(0, 1fr) 304px; gap: 22px; align-items: start; }.library-panel, .activity-panel { border: 1px solid var(--border-color); background: var(--bg-secondary); }.panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; padding: 24px 24px 20px; border-bottom: 1px solid var(--border-color-light); }.panel-heading h2, .activity-heading h2 { margin-bottom: 5px; font-size: 19px; }.panel-heading p, .activity-heading p { margin-bottom: 0; color: var(--text-muted); font-size: 13px; }.library-toolbar { display: grid; gap: 10px; justify-items: end; }.library-toolbar :deep(.el-segmented) { min-width: 190px; }.library-controls { display: grid; grid-template-columns: 240px 128px 36px; gap: 8px; align-items: center; }.library-controls.is-archived { grid-template-columns: 36px; }.library-controls .el-button { padding: 8px; }
.search-results { margin: 18px 24px 0; padding: 16px; border: 1px solid color-mix(in srgb, var(--color-primary) 24%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 5%, var(--bg-secondary)); }.search-results-heading { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 10px; }.search-results-heading div { display: grid; gap: 3px; }.search-results-heading span { color: var(--text-muted); font-size: 12px; }.search-result { display: grid; grid-template-columns: 24px 1fr; gap: 10px; width: 100%; padding: 10px 0; border: 0; border-top: 1px solid var(--border-color-light); background: transparent; color: var(--text-primary); cursor: pointer; text-align: left; }.search-result:first-of-type { border-top: 0; }.search-result:hover .result-content { color: var(--color-primary); }.result-index { color: var(--color-accent); font-size: 12px; font-weight: 700; }.result-content { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-height: 1.55; transition: color .2s ease; }
.state-panel { display: flex; justify-content: center; align-items: center; gap: 8px; min-height: 250px; color: var(--text-muted); }.document-list { padding: 0 24px; }.document-row { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; gap: 14px; align-items: start; padding: 19px 0; border-bottom: 1px solid var(--border-color-light); }.document-row:last-child { border-bottom: 0; }.document-type { width: 38px; height: 38px; border-radius: 8px; background: color-mix(in srgb, var(--color-primary) 12%, var(--bg-secondary)); color: var(--color-primary); font-size: 18px; }.document-body { min-width: 0; }.document-title-row { display: flex; gap: 10px; align-items: center; min-width: 0; }.document-title-row h3 { overflow: hidden; margin-bottom: 0; font-size: 16px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }.document-meta { display: flex; align-items: center; gap: 8px; margin: 5px 0 7px; color: var(--text-muted); font-size: 12px; }.document-meta i { width: 3px; height: 3px; border-radius: 50%; background: color-mix(in srgb, var(--text-muted) 58%, transparent); }.document-preview, .document-error { display: -webkit-box; overflow: hidden; margin-bottom: 9px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; color: var(--text-secondary); font-size: 13px; line-height: 1.55; }.document-error { color: var(--color-error); }.tag-list { display: flex; flex-wrap: wrap; gap: 5px; }.tag-list :deep(.el-tag), .activity-sources :deep(.el-tag) { border-color: var(--border-color); background: var(--bg-tertiary); color: var(--text-secondary); }.document-actions { display: flex; gap: 7px; padding-top: 1px; }.document-actions :deep(.el-button) { margin: 0; }.pagination-footer { display: flex; justify-content: flex-end; padding: 18px 24px 22px; border-top: 1px solid var(--border-color-light); }
.activity-panel { padding-bottom: 4px; }.activity-heading { display: flex; justify-content: space-between; align-items: flex-start; padding: 24px 20px 18px; border-bottom: 1px solid var(--border-color-light); }.activity-heading > .el-icon { padding: 9px; border-radius: 8px; background: color-mix(in srgb, var(--color-warning) 13%, var(--bg-secondary)); color: var(--color-accent); font-size: 18px; }.activity-loading { display: flex; gap: 7px; align-items: center; padding: 20px; color: var(--text-muted); font-size: 13px; }.activity-list { display: grid; gap: 0; padding: 0 20px; list-style: none; }.activity-list li { padding: 16px 0; border-bottom: 1px solid var(--border-color-light); }.activity-list li:last-child { border-bottom: 0; }.activity-list p { display: -webkit-box; overflow: hidden; margin-bottom: 9px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; color: var(--text-primary); font-size: 13px; line-height: 1.5; }.activity-meta { display: flex; justify-content: space-between; gap: 8px; color: var(--text-muted); font-size: 12px; }.activity-sources { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }.activity-sources span { max-width: 100%; overflow: hidden; padding: 3px 6px; border: 1px solid var(--border-color); color: var(--text-secondary); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.document-content { max-height: 60vh; overflow: auto; margin: 0; padding: 16px; border: 1px solid var(--border-color); background: var(--bg-tertiary); color: var(--text-primary); font: 13px/1.7 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; white-space: pre-wrap; }.qa-thread { display: grid; gap: 16px; min-height: 240px; max-height: 52vh; overflow: auto; padding-right: 4px; }.qa-message { padding: 14px; border: 1px solid var(--border-color); background: var(--bg-secondary); }.qa-message.question { border-color: color-mix(in srgb, var(--color-primary) 26%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 8%, var(--bg-secondary)); }.message-label { display: block; margin-bottom: 7px; color: var(--text-muted); font-size: 12px; font-weight: 700; }.qa-message p { margin-bottom: 0; line-height: 1.65; }.thinking { display: flex; align-items: center; gap: 7px; color: var(--text-secondary); }.answer-markdown { color: var(--text-primary); font-size: 14px; line-height: 1.7; }.answer-markdown :deep(p:last-child) { margin-bottom: 0; }.answer-sources { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-color); }.answer-sources > span { color: var(--text-muted); font-size: 12px; }.qa-composer { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; margin-top: 20px; }
@media (max-width: 1080px) { .overview { grid-template-columns: repeat(2, 1fr); }.library-layout { grid-template-columns: 1fr; }.activity-panel { display: none; }.upload-panel { grid-template-columns: 1fr; }.drop-zone { border-right: 0; border-bottom: 1px solid var(--border-color-light); }.library-controls { grid-template-columns: minmax(200px, 1fr) 128px 36px; } }@media (max-width: 720px) { h1 { font-size: 32px; } .knowledge-shell { width: min(100% - 28px, 1440px); padding-top: 26px; }.page-intro { display: grid; align-items: start; padding-bottom: 22px; }.page-intro__actions { width: 100%; } .page-intro__actions .el-button { flex: 1; } .primary-action { width: auto; }.overview { grid-template-columns: 1fr 1fr; gap: 8px; }.metric { padding: 12px; }.metric strong { font-size: 16px; } .panel-heading { display: grid; padding: 18px 16px; }.library-toolbar { width: 100%; justify-items: stretch; }.library-toolbar :deep(.el-segmented) { width: 100%; }.library-controls { grid-template-columns: 1fr 42px; }.library-controls .el-input { grid-column: 1 / -1; }.library-controls .el-select { width: 100%; }.document-list { padding: 0 16px; }.document-row { grid-template-columns: 34px minmax(0, 1fr); gap: 10px; }.document-type { width: 34px; height: 34px; }.document-actions { grid-column: 2; padding-top: 0; }.document-title-row { align-items: flex-start; }.document-title-row h3 { white-space: normal; }.document-meta { flex-wrap: wrap; }.pagination-footer { overflow: auto; justify-content: flex-start; padding: 14px 16px 18px; }.qa-composer { grid-template-columns: 1fr; }.upload-options { padding: 16px; }.drop-zone { min-height: 128px; padding: 20px; }.upload-icon { width: 38px; height: 38px; }.drop-zone h2 { font-size: 16px; } }
</style>
