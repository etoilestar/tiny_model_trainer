<template>
  <Layout>
    <div class="jobs-page">
      <div class="page-header">
        <div>
          <h2>训练任务</h2>
          <p class="subtitle">管理和监控模型训练任务</p>
        </div>
        <el-button type="primary" :icon="Plus" size="large" @click="newJobDialogVisible = true">
          新建训练
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="jobs"
        border
        stripe
        style="width: 100%"
        empty-text="暂无训练任务"
      >
        <el-table-column prop="name" label="任务名称" min-width="160" />
        <el-table-column prop="status" label="状态" width="130">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              <el-icon v-if="row.status === 'running'" class="is-loading" style="margin-right:4px">
                <loading />
              </el-icon>
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">{{ formatDate(row.started_at) }}</template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">{{ formatDate(row.completed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" text @click="viewJobDetail(row)">
              查看详情
            </el-button>
            <el-button
              v-if="row.status === 'running' || row.status === 'pending'"
              size="small"
              type="danger"
              text
              @click="handleStopJob(row)"
            >
              停止
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper" v-if="jobs.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchJobs"
        />
      </div>
    </div>

    <!-- 新建训练对话框 -->
    <el-dialog
      v-model="newJobDialogVisible"
      title="新建训练任务"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="newJobFormRef"
        :model="newJobForm"
        :rules="newJobRules"
        label-width="100px"
        size="large"
      >
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="newJobForm.name" placeholder="请输入任务名称" clearable />
        </el-form-item>
        <el-form-item label="选择工作流" prop="workflowId">
          <el-select v-model="newJobForm.workflowId" placeholder="请选择工作流" style="width:100%">
            <el-option
              v-for="wf in workflows"
              :key="wf.id"
              :label="wf.name"
              :value="wf.id"
            />
            <template #empty>
              <div style="padding: 12px; text-align: center; color: #909399; font-size: 13px">
                暂无工作流，请先在画布中创建并保存
              </div>
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newJobForm.description" type="textarea" :rows="2" placeholder="可选备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newJobDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createJobLoading" @click="handleCreateJob">
          开始训练
        </el-button>
      </template>
    </el-dialog>
  </Layout>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import Layout from '@/components/Layout.vue'
import { getJobs, createJob, stopJob, getWorkflows } from '@/api'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.id)

const loading = ref(false)
const jobs = ref([])
const workflows = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const newJobDialogVisible = ref(false)
const createJobLoading = ref(false)
const newJobFormRef = ref(null)
let pollTimer = null

const newJobForm = reactive({ name: '', workflowId: '', description: '' })
const newJobRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  workflowId: [{ required: true, message: '请选择工作流', trigger: 'change' }]
}

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function statusType(s) {
  return { pending: 'info', running: 'warning', completed: 'success', failed: 'danger', stopped: 'info' }[s] || 'info'
}

function statusLabel(s) {
  return { pending: '等待中', running: '运行中', completed: '已完成', failed: '失败', stopped: '已停止' }[s] || s || '未知'
}

function viewJobDetail(row) {
  router.push(`/projects/${projectId.value}/jobs/${row.id}`)
}

async function handleStopJob(row) {
  await ElMessageBox.confirm(`确认停止任务 "${row.name}" 吗？`, '停止确认', {
    type: 'warning',
    confirmButtonText: '停止',
    cancelButtonText: '取消'
  })
  try {
    await stopJob(row.id)
    ElMessage.success('任务已停止')
    await fetchJobs()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '停止失败')
  }
}

async function fetchJobs() {
  loading.value = true
  try {
    const res = await getJobs(projectId.value)
    const list = res?.data || res || []
    jobs.value = Array.isArray(list) ? list : list.items || []
    total.value = jobs.value.length
  } catch (e) {
    ElMessage.error('加载训练任务失败')
  } finally {
    loading.value = false
  }
}

async function fetchWorkflows() {
  try {
    const res = await getWorkflows(projectId.value)
    workflows.value = res?.data || res || []
  } catch {
    // ignore
  }
}

async function handleCreateJob() {
  if (!newJobFormRef.value) return
  const valid = await newJobFormRef.value.validate().catch(() => false)
  if (!valid) return
  createJobLoading.value = true
  try {
    const res = await createJob({
      name: newJobForm.name,
      project_id: projectId.value,
      workflow_id: newJobForm.workflowId,
      description: newJobForm.description
    })
    const jobId = res?.data?.id || res?.id
    ElMessage.success('训练任务已启动')
    newJobDialogVisible.value = false
    await fetchJobs()
    if (jobId) router.push(`/projects/${projectId.value}/jobs/${jobId}`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '创建失败')
  } finally {
    createJobLoading.value = false
  }
}

function startPolling() {
  pollTimer = setInterval(() => {
    const hasRunning = jobs.value.some(j => j.status === 'running' || j.status === 'pending')
    if (hasRunning) fetchJobs()
  }, 5000)
}

onMounted(async () => {
  await Promise.all([fetchJobs(), fetchWorkflows()])
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.jobs-page {
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

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
