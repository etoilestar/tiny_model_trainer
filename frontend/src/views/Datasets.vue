<template>
  <Layout>
    <div class="datasets-page">
      <div class="page-header">
        <div>
          <h2>数据集管理</h2>
          <p class="subtitle">管理项目 "{{ currentProjectName }}" 的数据集</p>
        </div>
        <el-button type="primary" :icon="Upload" size="large" @click="uploadDialogVisible = true">
          上传数据集
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="datasets"
        border
        stripe
        style="width: 100%"
        empty-text="暂无数据集，请先上传"
      >
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="format" label="格式" width="140">
          <template #default="{ row }">
            <el-tag>{{ formatLabel(row.format) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" size="small" text @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 上传数据集对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传数据集"
      width="560px"
      :close-on-click-modal="false"
      @close="resetUploadForm"
    >
      <el-form
        ref="uploadFormRef"
        :model="uploadForm"
        :rules="uploadRules"
        label-width="100px"
        size="large"
      >
        <el-form-item label="数据集名称" prop="name">
          <el-input v-model="uploadForm.name" placeholder="请输入数据集名称" clearable />
        </el-form-item>
        <el-form-item label="数据格式" prop="format">
          <el-select v-model="uploadForm.format" placeholder="请选择数据格式" style="width: 100%">
            <el-option label="YOLO格式" value="yolo" />
            <el-option label="COCO格式" value="coco" />
            <el-option label="ImageFolder格式" value="imagefolder" />
            <el-option label="文本CSV" value="csv" />
            <el-option label="文本JSONL" value="jsonl" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据集文件" prop="file">
          <el-upload
            ref="uploadRef"
            class="upload-area"
            drag
            :auto-upload="false"
            :limit="1"
            accept=".zip,.tar,.tar.gz,.csv,.jsonl"
            :on-change="handleFileChange"
            :on-remove="() => (uploadForm.file = null)"
          >
            <el-icon class="el-icon--upload" size="40"><upload-filled /></el-icon>
            <div class="el-upload__text">
              点击或拖拽文件到此处上传
              <em>（支持 zip / csv / jsonl 格式）</em>
            </div>
          </el-upload>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入数据集描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>
  </Layout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import Layout from '@/components/Layout.vue'
import { getDatasets, uploadDataset, deleteDataset } from '@/api'
import { useProjectStore } from '@/stores/project'

const route = useRoute()
const projectStore = useProjectStore()
const projectId = computed(() => route.params.id)
const currentProjectName = computed(
  () => projectStore.currentProject?.name || `项目 ${projectId.value}`
)

const loading = ref(false)
const datasets = ref([])
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadFormRef = ref(null)
const uploadRef = ref(null)

const uploadForm = reactive({ name: '', format: '', file: null, description: '' })
const uploadRules = {
  name: [{ required: true, message: '请输入数据集名称', trigger: 'blur' }],
  format: [{ required: true, message: '请选择数据格式', trigger: 'change' }],
  file: [{ required: true, message: '请选择上传文件', trigger: 'change' }]
}

function formatLabel(fmt) {
  const map = { yolo: 'YOLO', coco: 'COCO', imagefolder: 'ImageFolder', csv: '文本CSV', jsonl: '文本JSONL' }
  return map[fmt] || fmt
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}

function statusType(s) {
  return { ready: 'success', processing: 'warning', error: 'danger' }[s] || 'info'
}

function statusLabel(s) {
  return { ready: '就绪', processing: '处理中', error: '错误' }[s] || s || '未知'
}

function handleFileChange(file) {
  uploadForm.file = file.raw
}

function resetUploadForm() {
  uploadForm.name = ''
  uploadForm.format = ''
  uploadForm.file = null
  uploadForm.description = ''
  uploadFormRef.value?.resetFields()
}

async function fetchDatasets() {
  loading.value = true
  try {
    const res = await getDatasets(projectId.value)
    datasets.value = res?.data || res || []
  } catch (e) {
    ElMessage.error('加载数据集失败')
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  if (!uploadFormRef.value) return
  const valid = await uploadFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (!uploadForm.file) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('name', uploadForm.name)
    formData.append('format', uploadForm.format)
    formData.append('project_id', projectId.value)
    formData.append('description', uploadForm.description)
    formData.append('file', uploadForm.file)
    await uploadDataset(formData)
    ElMessage.success('数据集上传成功')
    uploadDialogVisible.value = false
    await fetchDatasets()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认要删除数据集 "${row.name}" 吗？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消'
  })
  try {
    await deleteDataset(row.id)
    ElMessage.success('删除成功')
    await fetchDatasets()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '删除失败')
  }
}

onMounted(fetchDatasets)
</script>

<style scoped>
.datasets-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.subtitle {
  color: #909399;
  font-size: 14px;
}

.upload-area {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
}
</style>
