<template>
  <Layout :full-width="true">
    <div class="canvas-page">
      <!-- Toolbar -->
      <div class="canvas-toolbar">
        <div class="toolbar-left">
          <el-icon size="18" color="#409EFF"><cpu /></el-icon>
          <el-input
            v-model="workflowName"
            placeholder="工作流名称"
            size="small"
            style="width: 200px; margin-left: 8px"
          />
        </div>
        <div class="toolbar-center">
          <span class="toolbar-title">画布编辑器</span>
        </div>
        <div class="toolbar-right">
          <el-button size="small" :icon="Delete" @click="clearCanvas">清空画布</el-button>
          <el-button size="small" :icon="FolderOpened" :loading="saving" @click="saveCanvas">
            保存画布
          </el-button>
          <el-button size="small" type="primary" :icon="VideoPlay" :loading="starting" @click="startTraining">
            开始训练
          </el-button>
        </div>
      </div>

      <div class="canvas-body">
        <!-- Left panel: Node palette -->
        <div class="node-palette">
          <div class="palette-title">节点面板</div>

          <div class="palette-section">
            <div class="section-label">数据节点</div>
            <div
              class="palette-item dataset-item"
              data-node-type="dataset"
              draggable="true"
              @pointerdown="setPendingNodeType('dataset')"
              @dragstart="onDragStart($event, 'dataset')"
              @dragend="onDragEnd"
            >
              <el-icon><files /></el-icon>
              <span>数据集节点</span>
            </div>
          </div>

          <div class="palette-section">
            <div class="section-label">处理节点</div>
            <div
              class="palette-item process-item"
              data-node-type="process"
              draggable="true"
              @pointerdown="setPendingNodeType('process')"
              @dragstart="onDragStart($event, 'process')"
              @dragend="onDragEnd"
            >
              <el-icon><operation /></el-icon>
              <span>数据处理节点</span>
            </div>
          </div>

          <div class="palette-section">
            <div class="section-label">模型节点</div>
            <div
              class="palette-item model-item"
              data-node-type="model"
              draggable="true"
              @pointerdown="setPendingNodeType('model')"
              @dragstart="onDragStart($event, 'model')"
              @dragend="onDragEnd"
            >
              <el-icon><setting /></el-icon>
              <span>模型选择节点</span>
            </div>
          </div>

          <div class="palette-section">
            <div class="section-label">训练节点</div>
            <div
              class="palette-item trainconfig-item"
              data-node-type="trainConfig"
              draggable="true"
              @pointerdown="setPendingNodeType('trainConfig')"
              @dragstart="onDragStart($event, 'trainConfig')"
              @dragend="onDragEnd"
            >
              <el-icon><data-line /></el-icon>
              <span>训练配置节点</span>
            </div>
            <div
              class="palette-item train-item"
              data-node-type="trainExec"
              draggable="true"
              @pointerdown="setPendingNodeType('trainExec')"
              @dragstart="onDragStart($event, 'trainExec')"
              @dragend="onDragEnd"
            >
              <el-icon><video-play /></el-icon>
              <span>训练执行节点</span>
            </div>
          </div>

          <div class="palette-section">
            <div class="section-label">评估节点</div>
            <div
              class="palette-item eval-item"
              data-node-type="eval"
              draggable="true"
              @pointerdown="setPendingNodeType('eval')"
              @dragstart="onDragStart($event, 'eval')"
              @dragend="onDragEnd"
            >
              <el-icon><data-analysis /></el-icon>
              <span>评估节点</span>
            </div>
          </div>
        </div>

        <!-- Center: Vue Flow canvas -->
        <div
          class="flow-wrapper"
        >
          <VueFlow
            :id="FLOW_ID"
            v-model:nodes="nodes"
            v-model:edges="edges"
            :node-types="nodeTypes"
            :default-viewport="{ zoom: 1 }"
            :min-zoom="0.3"
            :max-zoom="2"
            fit-view-on-init
            @node-click="onNodeClick"
            @pane-click="selectedNode = null"
            @connect="addEdges"
            @dragover.prevent
            @drop="onDrop"
          >
            <Background pattern-color="#e0e0e0" :gap="20" />
            <Controls />
            <MiniMap
              :node-color="miniMapNodeColor"
              node-stroke-width="2"
            />
          </VueFlow>
        </div>

        <!-- Right panel: Node properties -->
        <div class="props-panel" :class="{ 'props-visible': selectedNode }">
          <div class="props-title">
            <el-icon><edit /></el-icon>
            节点属性
          </div>

          <template v-if="selectedNode">
            <!-- Dataset Node Props -->
            <template v-if="selectedNode.type === 'dataset'">
              <el-form label-position="top" size="small">
                <el-form-item label="数据集">
                  <el-select
                    v-model="selectedNode.data.datasetId"
                    placeholder="请选择数据集"
                    style="width: 100%"
                    @change="updateNodeData"
                  >
                    <el-option
                      v-for="ds in datasets"
                      :key="ds.id"
                      :label="ds.name"
                      :value="ds.id"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="数据集名称">
                  <el-input v-model="selectedNode.data.label" @input="updateNodeData" />
                </el-form-item>
              </el-form>
            </template>

            <!-- Process Node Props -->
            <template v-else-if="selectedNode.type === 'process'">
              <el-form label-position="top" size="small">
                <el-form-item label="处理方式">
                  <el-select v-model="selectedNode.data.method" style="width:100%" @change="updateNodeData">
                    <el-option label="标准化" value="normalize" />
                    <el-option label="数据增强" value="augment" />
                    <el-option label="分割训练/验证集" value="split" />
                  </el-select>
                </el-form-item>
                <el-form-item label="验证集比例" v-if="selectedNode.data.method === 'split'">
                  <el-slider v-model="selectedNode.data.valRatio" :min="5" :max="40" :step="5" show-input @change="updateNodeData" />
                </el-form-item>
              </el-form>
            </template>

            <!-- Model Node Props -->
            <template v-else-if="selectedNode.type === 'model'">
              <el-form label-position="top" size="small">
                <el-form-item label="框架">
                  <el-select v-model="selectedNode.data.framework" style="width:100%" @change="updateNodeData">
                    <el-option label="YOLO" value="yolo" />
                    <el-option label="BERT" value="bert" />
                    <el-option label="ResNet" value="resnet" />
                    <el-option label="自定义" value="custom" />
                  </el-select>
                </el-form-item>
                <el-form-item label="模型名称/路径">
                  <el-input v-model="selectedNode.data.modelName" placeholder="如 yolov8n.pt" @input="updateNodeData" />
                </el-form-item>
              </el-form>
            </template>

            <!-- TrainConfig Node Props -->
            <template v-else-if="selectedNode.type === 'trainConfig'">
              <el-form label-position="top" size="small">
                <el-form-item label="训练轮数 (Epochs)">
                  <el-input-number v-model="selectedNode.data.epochs" :min="1" :max="1000" style="width:100%" @change="updateNodeData" />
                </el-form-item>
                <el-form-item label="批次大小 (Batch Size)">
                  <el-input-number v-model="selectedNode.data.batchSize" :min="1" :max="512" style="width:100%" @change="updateNodeData" />
                </el-form-item>
                <el-form-item label="学习率 (Learning Rate)">
                  <el-input v-model="selectedNode.data.learningRate" placeholder="0.001" @input="updateNodeData" />
                </el-form-item>
                <el-form-item label="优化器">
                  <el-select v-model="selectedNode.data.optimizer" style="width:100%" @change="updateNodeData">
                    <el-option label="Adam" value="adam" />
                    <el-option label="SGD" value="sgd" />
                    <el-option label="AdamW" value="adamw" />
                  </el-select>
                </el-form-item>
                <el-form-item label="设备">
                  <el-select v-model="selectedNode.data.device" style="width:100%" @change="updateNodeData">
                    <el-option label="CPU" value="cpu" />
                    <el-option label="GPU (cuda)" value="cuda" />
                  </el-select>
                </el-form-item>
              </el-form>
            </template>

            <!-- TrainExec Node Props -->
            <template v-else-if="selectedNode.type === 'trainExec'">
              <el-form label-position="top" size="small">
                <el-form-item label="任务名称">
                  <el-input v-model="selectedNode.data.jobName" placeholder="训练任务名称" @input="updateNodeData" />
                </el-form-item>
                <el-form-item label="输出目录">
                  <el-input v-model="selectedNode.data.outputDir" placeholder="./outputs" @input="updateNodeData" />
                </el-form-item>
                <el-form-item label="保存最优模型">
                  <el-switch v-model="selectedNode.data.saveBest" @change="updateNodeData" />
                </el-form-item>
              </el-form>
            </template>

            <!-- Eval Node Props -->
            <template v-else-if="selectedNode.type === 'eval'">
              <el-form label-position="top" size="small">
                <el-form-item label="评估指标">
                  <el-checkbox-group v-model="selectedNode.data.metrics" @change="updateNodeData">
                    <el-checkbox label="mAP">mAP</el-checkbox>
                    <el-checkbox label="Accuracy">Accuracy</el-checkbox>
                    <el-checkbox label="F1">F1</el-checkbox>
                    <el-checkbox label="Loss">Loss</el-checkbox>
                    <el-checkbox label="Precision">Precision</el-checkbox>
                    <el-checkbox label="Recall">Recall</el-checkbox>
                  </el-checkbox-group>
                </el-form-item>
                <el-form-item label="评估频率 (每N轮)">
                  <el-input-number v-model="selectedNode.data.evalEvery" :min="1" style="width:100%" @change="updateNodeData" />
                </el-form-item>
              </el-form>
            </template>

            <div class="delete-node-btn">
              <el-button type="danger" size="small" :icon="Delete" @click="deleteSelectedNode">
                删除节点
              </el-button>
            </div>
          </template>

          <div v-else class="props-empty">
            <el-icon size="32" color="#c0c4cc"><pointer /></el-icon>
            <p>点击画布中的节点<br>查看和编辑属性</p>
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, FolderOpened, VideoPlay } from '@element-plus/icons-vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'

import Layout from '@/components/Layout.vue'
import { nodeTypes } from '@/components/nodes/nodeTypes.js'
import { getDatasets, getWorkflows, createWorkflow, updateWorkflow, createJob } from '@/api'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.id)

const FLOW_ID = 'canvas-flow'
const NODE_TYPE_TRANSFER_KEY = 'application/x-tiny-model-node-type'

const { screenToFlowCoordinate, addNodes, removeNodes, addEdges } = useVueFlow(FLOW_ID)

const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const workflowName = ref('未命名工作流')
const saving = ref(false)
const starting = ref(false)
const datasets = ref([])
const currentWorkflowId = ref(null)

let nodeIdCounter = 1
let _dragNodeType = null

function generateNodeId() {
  return `node_${Date.now()}_${nodeIdCounter++}`
}

function setPendingNodeType(type) {
  _dragNodeType = validNodeTypes.has(type) ? type : null
}

function getDefaultNodeData(type) {
  const defaults = {
    dataset: { label: '数据集', datasetId: null, format: '' },
    process: { label: '数据处理', method: 'normalize', valRatio: 20 },
    model: { label: '模型选择', framework: 'yolo', modelName: 'yolov8n.pt' },
    trainConfig: { label: '训练配置', epochs: 50, batchSize: 16, learningRate: '0.001', optimizer: 'adam', device: 'cpu' },
    trainExec: { label: '训练执行', jobName: '训练任务', outputDir: './outputs', saveBest: true },
    eval: { label: '评估', metrics: ['mAP', 'Loss'], evalEvery: 1 }
  }
  const defaultData = defaults[type] || { label: type }
  return JSON.parse(JSON.stringify(defaultData))
}

function miniMapNodeColor(node) {
  const colors = {
    dataset: '#1890ff',
    process: '#722ed1',
    model: '#722ed1',
    trainConfig: '#fa8c16',
    trainExec: '#fa541c',
    eval: '#52c41a'
  }
  return colors[node.type] || '#409EFF'
}

function onDragStart(event, nodeType) {
  if (!validNodeTypes.has(nodeType)) return

  _dragNodeType = nodeType
  const transfer = event.dataTransfer
  if (!transfer) return
  transfer.clearData()
  transfer.effectAllowed = 'move'
  transfer.setData(NODE_TYPE_TRANSFER_KEY, nodeType)
  transfer.setData('application/vueflow', nodeType)
  transfer.setData('application/x-node-type', nodeType)
}

function onDragEnd() {
  _dragNodeType = null
}

const validNodeTypes = new Set(['dataset', 'process', 'model', 'trainConfig', 'trainExec', 'eval'])

function onDrop(event) {
  const transfer = event.dataTransfer
  const type = (transfer && (transfer.getData(NODE_TYPE_TRANSFER_KEY)
    || transfer.getData('application/x-node-type')
    || transfer.getData('application/vueflow')))
    || _dragNodeType
  _dragNodeType = null
  if (!type || !validNodeTypes.has(type)) return

  const position = screenToFlowCoordinate({
    x: event.clientX,
    y: event.clientY
  })

  const newNode = {
    id: generateNodeId(),
    type,
    position,
    data: getDefaultNodeData(type)
  }
  addNodes([newNode])
}

function onNodeClick({ node }) {
  selectedNode.value = node
}

function updateNodeData() {
  if (!selectedNode.value) return
  const idx = nodes.value.findIndex(n => n.id === selectedNode.value.id)
  if (idx !== -1) {
    nodes.value[idx] = { ...nodes.value[idx], data: { ...selectedNode.value.data } }
  }
}

function deleteSelectedNode() {
  if (!selectedNode.value) return
  nodes.value = nodes.value.filter(n => n.id !== selectedNode.value.id)
  edges.value = edges.value.filter(
    e => e.source !== selectedNode.value.id && e.target !== selectedNode.value.id
  )
  selectedNode.value = null
}

function clearCanvas() {
  ElMessageBox.confirm('确认清空画布？所有节点和连线将被删除。', '清空确认', {
    type: 'warning',
    confirmButtonText: '清空',
    cancelButtonText: '取消'
  }).then(() => {
    nodes.value = []
    edges.value = []
    selectedNode.value = null
    ElMessage.success('画布已清空')
  }).catch(() => {})
}

async function saveCanvas() {
  saving.value = true
  try {
    const payload = {
      name: workflowName.value,
      project_id: projectId.value,
      nodes: nodes.value.map(n => ({ id: n.id, type: n.type, position: n.position, data: n.data })),
      edges: edges.value.map(e => ({ id: e.id, source: e.source, target: e.target }))
    }
    if (currentWorkflowId.value) {
      await updateWorkflow(currentWorkflowId.value, payload)
    } else {
      const res = await createWorkflow(payload)
      currentWorkflowId.value = res?.data?.id || res?.id
    }
    ElMessage.success('画布保存成功')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function startTraining() {
  if (nodes.value.length === 0) {
    ElMessage.warning('请先在画布上添加节点')
    return
  }
  const configNode = nodes.value.find(n => n.type === 'trainConfig')
  const modelNode = nodes.value.find(n => n.type === 'model')
  const datasetNode = nodes.value.find(n => n.type === 'dataset')

  if (!configNode || !modelNode || !datasetNode) {
    ElMessage.warning('请确保画布包含数据集节点、模型节点和训练配置节点')
    return
  }

  starting.value = true
  try {
    await saveCanvas()
    const jobData = {
      name: configNode.data.jobName || workflowName.value,
      project_id: projectId.value,
      workflow_id: currentWorkflowId.value,
      config: {
        framework: modelNode.data.framework,
        model_name: modelNode.data.modelName,
        dataset_id: datasetNode.data.datasetId,
        epochs: configNode.data.epochs,
        batch_size: configNode.data.batchSize,
        learning_rate: parseFloat(configNode.data.learningRate) || 0.001,
        optimizer: configNode.data.optimizer,
        device: configNode.data.device
      }
    }
    const res = await createJob(jobData)
    const jobId = res?.data?.id || res?.id
    ElMessage.success('训练任务已启动')
    router.push(`/projects/${projectId.value}/jobs${jobId ? `/${jobId}` : ''}`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '启动训练失败')
  } finally {
    starting.value = false
  }
}

async function loadWorkflow() {
  try {
    const res = await getWorkflows(projectId.value)
    const workflows = res?.data || res || []
    if (workflows.length > 0) {
      const wf = workflows[0]
      currentWorkflowId.value = wf.id
      workflowName.value = wf.name || '未命名工作流'
      if (wf.nodes) nodes.value = wf.nodes
      if (wf.edges) edges.value = wf.edges
    }
  } catch {
    // no workflow yet
  }
}

onMounted(async () => {
  await loadWorkflow()
  try {
    const res = await getDatasets(projectId.value)
    datasets.value = res?.data || res || []
  } catch {
    // ignore
  }
})
</script>

<style scoped>
.canvas-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

.canvas-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
  z-index: 10;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 220px;
}

.toolbar-right {
  justify-content: flex-end;
}

.toolbar-center {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.canvas-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.node-palette {
  width: 160px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
  flex-shrink: 0;
  padding: 12px 8px;
}

.palette-title {
  font-size: 13px;
  font-weight: 700;
  color: #303133;
  padding: 4px 4px 8px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 8px;
}

.palette-section {
  margin-bottom: 12px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  padding: 4px;
  margin-bottom: 4px;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  margin-bottom: 4px;
  font-size: 12px;
  cursor: grab;
  color: #fff;
  transition: all 0.15s;
  user-select: none;
}

.palette-item * {
  pointer-events: none;
}

.palette-item:hover {
  opacity: 0.85;
  transform: translateX(2px);
}

.palette-item:active {
  cursor: grabbing;
}

.dataset-item { background: linear-gradient(135deg, #1890ff, #096dd9); }
.process-item { background: linear-gradient(135deg, #722ed1, #531dab); }
.model-item { background: linear-gradient(135deg, #7c3aed, #5b21b6); }
.trainconfig-item { background: linear-gradient(135deg, #fa8c16, #d46b08); }
.train-item { background: linear-gradient(135deg, #fa541c, #d4380d); }
.eval-item { background: linear-gradient(135deg, #52c41a, #389e0d); }

.flow-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.props-panel {
  width: 0;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  overflow: hidden;
  transition: width 0.25s ease;
  flex-shrink: 0;
}

.props-panel.props-visible {
  width: 280px;
  overflow-y: auto;
  padding: 16px;
}

.props-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.props-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #c0c4cc;
  text-align: center;
  font-size: 13px;
  padding: 16px;
}

.props-empty p {
  margin-top: 12px;
  line-height: 1.6;
}

.delete-node-btn {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

:deep(.vue-flow) {
  background: #f8f9fb;
}

:deep(.vue-flow__node) {
  border-radius: 10px;
}
</style>
