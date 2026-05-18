<template>
  <Layout>
    <div class="job-detail-page">
      <!-- Header -->
      <div class="page-header">
        <div class="header-left">
          <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
          <div>
            <h2>{{ jobInfo.name || '训练任务详情' }}</h2>
            <div class="header-meta">
              <el-tag :type="statusType(jobInfo.status)" size="small">
                <el-icon v-if="jobInfo.status === 'running'" class="is-loading" style="margin-right:3px">
                  <loading />
                </el-icon>
                {{ statusLabel(jobInfo.status) }}
              </el-tag>
              <span class="meta-item">创建时间：{{ formatDate(jobInfo.created_at) }}</span>
              <span class="meta-item" v-if="jobInfo.started_at">
                开始时间：{{ formatDate(jobInfo.started_at) }}
              </span>
              <span class="meta-item" v-if="jobInfo.completed_at">
                完成时间：{{ formatDate(jobInfo.completed_at) }}
              </span>
            </div>
          </div>
        </div>
        <el-button
          v-if="jobInfo.status === 'running' || jobInfo.status === 'pending'"
          type="danger"
          :icon="VideoPause"
          @click="handleStop"
        >
          停止训练
        </el-button>
      </div>

      <!-- Tabs -->
      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- Training Logs Tab -->
        <el-tab-pane label="训练日志" name="logs">
          <div class="log-panel">
            <div class="log-toolbar">
              <el-tag :type="statusType(jobInfo.status)" effect="dark">
                {{ statusLabel(jobInfo.status) }}
              </el-tag>
              <div class="log-actions">
                <el-switch v-model="autoScroll" active-text="自动滚动" />
                <el-button size="small" :icon="RefreshRight" @click="refreshLogs">刷新日志</el-button>
                <el-button size="small" :icon="Delete" @click="clearLogs">清空显示</el-button>
              </div>
            </div>
            <div ref="logContainer" class="log-container">
              <div
                v-for="(entry, idx) in logEntries"
                :key="idx"
                class="log-entry"
                :class="logLevelClass(entry.level)"
              >
                <span class="log-time">{{ entry.time }}</span>
                <span class="log-level">{{ entry.level }}</span>
                <span class="log-msg">{{ entry.message }}</span>
              </div>
              <div v-if="logEntries.length === 0" class="log-empty">
                暂无日志，训练开始后将实时显示...
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- Metrics Tab -->
        <el-tab-pane label="训练指标" name="metrics">
          <div class="metrics-panel">
            <div class="metrics-toolbar">
              <el-button :icon="RefreshRight" @click="fetchMetrics">刷新指标</el-button>
            </div>
            <div v-if="metricsLoading" class="metrics-loading">
              <el-skeleton :rows="4" animated />
            </div>
            <div v-else-if="hasMetrics" class="charts-grid">
              <MetricsChart
                v-if="trainLossData.length > 0"
                title="训练损失曲线"
                :data="trainLossData"
                color="#f56c6c"
                x-label="Epoch"
                y-label="Loss"
              />
              <MetricsChart
                v-if="valLossData.length > 0"
                title="验证损失曲线"
                :data="valLossData"
                color="#e6a23c"
                x-label="Epoch"
                y-label="Val Loss"
              />
              <MetricsChart
                v-if="lrData.length > 0"
                title="学习率曲线"
                :data="lrData"
                color="#909399"
                x-label="Epoch"
                y-label="Learning Rate"
              />
              <MetricsChart
                v-if="mapData.length > 0"
                title="评估指标 (mAP / Accuracy / F1)"
                :data="mapData"
                color="#67c23a"
                :extra-series="extraMetricsSeries"
                x-label="Epoch"
                y-label="Score"
              />
            </div>
            <div v-else class="metrics-empty">
              <el-empty description="暂无训练指标数据，训练开始后将显示" />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, RefreshRight, Delete, VideoPause } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import Layout from '@/components/Layout.vue'
import MetricsChart from '@/components/charts/MetricsChart.vue'
import { getJob, stopJob, getJobLogs, getMetrics } from '@/api'

const route = useRoute()
const router = useRouter()
const jobId = computed(() => route.params.jobId)
const projectId = computed(() => route.params.id)

const activeTab = ref('logs')
const jobInfo = ref({})
const logEntries = ref([])
const logContainer = ref(null)
const autoScroll = ref(true)
const metricsLoading = ref(false)

const trainLossData = ref([])
const valLossData = ref([])
const lrData = ref([])
const mapData = ref([])
const extraMetricsSeries = ref([])

let sseSource = null
let pollTimer = null

const hasMetrics = computed(
  () => trainLossData.value.length > 0 || valLossData.value.length > 0 || mapData.value.length > 0
)

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function statusType(s) {
  return { pending: 'info', running: 'warning', completed: 'success', failed: 'danger', stopped: 'info' }[s] || 'info'
}

function statusLabel(s) {
  return { pending: '等待中', running: '运行中', completed: '已完成', failed: '失败', stopped: '已停止' }[s] || s || '未知'
}

function logLevelClass(level) {
  return {
    error: level === 'ERROR',
    warning: level === 'WARNING' || level === 'WARN',
    info: level === 'INFO',
    debug: level === 'DEBUG'
  }
}

function parseLogLine(line) {
  if (!line || !line.trim()) return null
  // Try to parse JSON log
  try {
    const obj = JSON.parse(line)
    return {
      time: obj.time || obj.timestamp || dayjs().format('HH:mm:ss'),
      level: (obj.level || obj.levelname || 'INFO').toUpperCase(),
      message: obj.message || obj.msg || line
    }
  } catch {
    // Plain text - try to extract timestamp and level
    const match = line.match(/^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*)\s+(\w+)\s+(.*)$/)
    if (match) {
      return { time: dayjs(match[1]).format('HH:mm:ss'), level: match[2].toUpperCase(), message: match[3] }
    }
    return { time: dayjs().format('HH:mm:ss'), level: 'INFO', message: line }
  }
}

async function scrollToBottom() {
  if (!autoScroll.value || !logContainer.value) return
  await nextTick()
  logContainer.value.scrollTop = logContainer.value.scrollHeight
}

function appendLog(text) {
  const lines = text.split('\n')
  for (const line of lines) {
    const entry = parseLogLine(line)
    if (entry) {
      logEntries.value.push(entry)
    }
  }
  // Keep only last 2000 entries
  if (logEntries.value.length > 2000) {
    logEntries.value = logEntries.value.slice(-2000)
  }
  scrollToBottom()
}

function startSSE() {
  if (sseSource) {
    sseSource.close()
    sseSource = null
  }
  const token = localStorage.getItem('token')
  const url = `/api/training/jobs/${jobId.value}/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`
  sseSource = new EventSource(url)

  sseSource.onmessage = (event) => {
    appendLog(event.data)
  }

  sseSource.addEventListener('log', (event) => {
    appendLog(event.data)
  })

  sseSource.addEventListener('status', (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.status) jobInfo.value = { ...jobInfo.value, ...data }
    } catch { /* ignore */ }
  })

  sseSource.onerror = () => {
    // SSE failed, fall back to polling logs
    sseSource?.close()
    sseSource = null
    startLogPolling()
  }
}

function startLogPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    await refreshLogs()
    if (jobInfo.value.status === 'completed' || jobInfo.value.status === 'failed' || jobInfo.value.status === 'stopped') {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }, 3000)
}

async function refreshLogs() {
  try {
    const res = await getJobLogs(jobId.value)
    const raw = res?.data || res || {}
    const logText = raw.logs || raw.log || ''
    if (typeof logText === 'string' && logText.trim()) {
      logEntries.value = []
      appendLog(logText)
    }
    // Also refresh job info
    const jobRes = await getJob(jobId.value)
    jobInfo.value = jobRes?.data || jobRes || {}
  } catch { /* ignore */ }
}

function clearLogs() {
  logEntries.value = []
}

async function fetchMetrics() {
  metricsLoading.value = true
  try {
    const res = await getMetrics(jobId.value)
    const data = res?.data || res || []
    const list = Array.isArray(data) ? data : data.metrics || []

    trainLossData.value = list.filter(m => m.metric_name === 'train_loss' || m.name === 'train_loss')
      .map(m => ({ epoch: m.epoch || m.step, value: m.value }))

    valLossData.value = list.filter(m => m.metric_name === 'val_loss' || m.name === 'val_loss')
      .map(m => ({ epoch: m.epoch || m.step, value: m.value }))

    lrData.value = list.filter(m => m.metric_name === 'lr' || m.name === 'learning_rate' || m.name === 'lr')
      .map(m => ({ epoch: m.epoch || m.step, value: m.value }))

    mapData.value = list.filter(m => m.metric_name === 'mAP' || m.name === 'mAP')
      .map(m => ({ epoch: m.epoch || m.step, value: m.value }))

    // Extra metrics (Accuracy, F1)
    const extraNames = ['accuracy', 'f1', 'precision', 'recall']
    extraMetricsSeries.value = extraNames
      .map(name => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        data: list.filter(m => (m.metric_name || m.name) === name)
          .map(m => ({ epoch: m.epoch || m.step, value: m.value }))
      }))
      .filter(s => s.data.length > 0)
  } catch {
    // ignore
  } finally {
    metricsLoading.value = false
  }
}

async function handleStop() {
  await ElMessageBox.confirm('确认停止此训练任务吗？', '停止确认', {
    type: 'warning',
    confirmButtonText: '停止',
    cancelButtonText: '取消'
  })
  try {
    await stopJob(jobId.value)
    ElMessage.success('已发送停止指令')
    jobInfo.value = { ...jobInfo.value, status: 'stopped' }
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '停止失败')
  }
}

function goBack() {
  router.push(`/projects/${projectId.value}/jobs`)
}

watch(activeTab, (tab) => {
  if (tab === 'metrics') fetchMetrics()
})

onMounted(async () => {
  try {
    const res = await getJob(jobId.value)
    jobInfo.value = res?.data || res || {}
  } catch { /* ignore */ }

  if (jobInfo.value.status === 'running' || jobInfo.value.status === 'pending') {
    startSSE()
  } else {
    // Load existing logs
    await refreshLogs()
  }
})

onUnmounted(() => {
  sseSource?.close()
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.job-detail-page {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.header-left h2 {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 6px;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 13px;
  color: #909399;
}

.detail-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

:deep(.el-tab-pane) {
  height: 100%;
}

.log-panel {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 280px);
}

.log-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #1a1a2e;
  border-radius: 8px 8px 0 0;
}

.log-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

:deep(.log-toolbar .el-switch__label) {
  color: #ccc;
}

.log-container {
  flex: 1;
  background: #0d1117;
  border-radius: 0 0 8px 8px;
  overflow-y: auto;
  padding: 12px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}

.log-entry {
  display: flex;
  gap: 10px;
  padding: 2px 0;
  line-height: 1.5;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.log-entry.error .log-msg { color: #ff6b6b; }
.log-entry.warning .log-msg { color: #ffa94d; }
.log-entry.info .log-msg { color: #c9d1d9; }
.log-entry.debug .log-msg { color: #6e7681; }

.log-time {
  color: #484f58;
  white-space: nowrap;
  min-width: 80px;
}

.log-level {
  min-width: 70px;
  font-weight: 600;
}

.log-entry.error .log-level { color: #ff6b6b; }
.log-entry.warning .log-level { color: #ffa94d; }
.log-entry.info .log-level { color: #58a6ff; }
.log-entry.debug .log-level { color: #6e7681; }

.log-msg {
  flex: 1;
  word-break: break-all;
  white-space: pre-wrap;
}

.log-empty {
  color: #484f58;
  padding: 40px;
  text-align: center;
}

.metrics-panel {
  padding: 16px 0;
}

.metrics-toolbar {
  margin-bottom: 16px;
}

.metrics-loading {
  padding: 24px 0;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
  gap: 20px;
}

.metrics-empty {
  padding: 60px 0;
  display: flex;
  justify-content: center;
}
</style>
