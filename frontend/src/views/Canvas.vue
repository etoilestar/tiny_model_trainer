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
              class="palette-item model-item yolo-model-item"
              data-node-type="yoloModel"
              draggable="true"
              @pointerdown="setPendingNodeTypeFromEvent"
              @dragstart="onDragStart($event)"
              @dragend="onDragEnd"
            >
              <el-icon><setting /></el-icon>
              <span>YOLO模型节点</span>
            </div>

            <div
              class="palette-item model-item resnet-model-item"
              data-node-type="resnetModel"
              draggable="true"
              @pointerdown="setPendingNodeTypeFromEvent"
              @dragstart="onDragStart($event)"
              @dragend="onDragEnd"
            >
              <el-icon><setting /></el-icon>
              <span>ResNet模型节点</span>
            </div>

            <div
              class="palette-item model-item mobilenet-model-item"
              data-node-type="mobilenetModel"
              draggable="true"
              @pointerdown="setPendingNodeTypeFromEvent"
              @dragstart="onDragStart($event)"
              @dragend="onDragEnd"
            >
              <el-icon><setting /></el-icon>
              <span>MobileNet模型节点</span>
            </div>

            <div
              class="palette-item model-item efficientnet-model-item"
              data-node-type="efficientnetModel"
              draggable="true"
              @pointerdown="setPendingNodeTypeFromEvent"
              @dragstart="onDragStart($event)"
              @dragend="onDragEnd"
            >
              <el-icon><setting /></el-icon>
              <span>EfficientNet模型节点</span>
            </div>

            <div
              class="palette-item model-item unet-model-item"
              data-node-type="unetModel"
              draggable="true"
              @pointerdown="setPendingNodeTypeFromEvent"
              @dragstart="onDragStart($event)"
              @dragend="onDragEnd"
            >
              <el-icon><setting /></el-icon>
              <span>UNet模型节点</span>
            </div>

            <div
              class="palette-item model-item bert-model-item"
              data-node-type="bertModel"
              draggable="true"
              @pointerdown="setPendingNodeTypeFromEvent"
              @dragstart="onDragStart($event)"
              @dragend="onDragEnd"
            >
              <el-icon><setting /></el-icon>
              <span>BERT模型节点</span>
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
        <div class="flow-wrapper">
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
            @connect="onConnect"
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
            <template v-else-if="isModelNode(selectedNode)">
              <el-form label-position="top" size="small">
                <el-form-item label="模型类型">
                  <el-input :model-value="selectedNode.data.familyLabel" disabled />
                </el-form-item>

                <el-form-item label="模型版本">
                  <el-select
                    v-model="selectedNode.data.modelVersion"
                    placeholder="请选择模型版本"
                    style="width:100%"
                    @change="onModelVersionChange"
                  >
                    <el-option
                      v-for="item in currentModelVersionOptions"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="模型文件/路径">
                  <el-input
                    v-model="selectedNode.data.modelName"
                    placeholder="如 yolov8n.pt / resnet18 / mobilenet_v3_small / efficientnet_b0 / unet"
                    @input="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="预训练">
                  <el-switch v-model="selectedNode.data.pretrained" @change="updateNodeData" />
                </el-form-item>

                <el-alert
                  v-if="['resnet', 'mobilenet', 'efficientnet'].includes(selectedNode.data.framework)"
                  title="分类模型使用 ImageFolder 数据集：train/class_x/*.jpg，可选 val/class_x/*.jpg；建议输入尺寸 224。"
                  type="info"
                  :closable="false"
                  show-icon
                />

                <template v-if="selectedNode.data.framework === 'unet'">
                  <el-form-item label="类别数 num_classes">
                    <el-input-number
                      v-model="selectedNode.data.numClasses"
                      :min="2"
                      :max="255"
                      style="width:100%"
                      @change="updateNodeData"
                    />
                  </el-form-item>

                  <el-alert
                    title="UNet 分割使用 MMSeg-like 数据集：images/train、images/val、annotations/train、annotations/val；mask 为单通道类别索引 PNG。"
                    type="info"
                    :closable="false"
                    show-icon
                  />
                </template>

                <el-alert
                  v-if="selectedNode.data.framework === 'bert'"
                  title="BERT 节点用于文本任务，数据集和训练器需要走 BERTTrainer。"
                  type="info"
                  :closable="false"
                  show-icon
                />
              </el-form>
            </template>

            <!-- TrainConfig Node Props -->
            <template v-else-if="selectedNode.type === 'trainConfig'">
              <el-form label-position="top" size="small">
                <el-form-item label="训练轮数 (Epochs)">
                  <el-input-number
                    v-model="selectedNode.data.epochs"
                    :min="1"
                    :max="1000"
                    style="width:100%"
                    @change="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="批次大小 (Batch Size)">
                  <el-input-number
                    v-model="selectedNode.data.batchSize"
                    :min="1"
                    :max="512"
                    style="width:100%"
                    @change="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="输入尺寸 (Image Size)">
                  <el-input-number
                    v-model="selectedNode.data.imgSize"
                    :min="32"
                    :max="2048"
                    :step="32"
                    style="width:100%"
                    @change="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="学习率 (Learning Rate)">
                  <el-input
                    v-model="selectedNode.data.learningRate"
                    placeholder="0.001"
                    @input="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="优化器">
                  <el-select v-model="selectedNode.data.optimizer" style="width:100%" @change="updateNodeData">
                    <el-option label="Auto" value="auto" />
                    <el-option label="SGD" value="SGD" />
                    <el-option label="Adam" value="Adam" />
                    <el-option label="AdamW" value="AdamW" />
                  </el-select>
                </el-form-item>

                <el-form-item label="学习率调度">
                  <el-select v-model="selectedNode.data.scheduler" style="width:100%" @change="updateNodeData">
                    <el-option label="不使用调度" value="none" />
                    <el-option label="余弦退火 Cosine Annealing" value="cosine" />
                    <el-option label="StepLR" value="step" />
                    <el-option label="MultiStepLR" value="multistep" />
                  </el-select>
                </el-form-item>

                <el-form-item label="Warmup Epochs">
                  <el-input-number
                    v-model="selectedNode.data.warmupEpochs"
                    :min="0"
                    :max="20"
                    :step="0.5"
                    style="width:100%"
                    @change="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="Warmup Momentum">
                  <el-input
                    v-model="selectedNode.data.warmupMomentum"
                    placeholder="0.8"
                    @input="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="Momentum">
                  <el-input
                    v-model="selectedNode.data.momentum"
                    placeholder="0.937"
                    @input="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="Weight Decay">
                  <el-input
                    v-model="selectedNode.data.weightDecay"
                    placeholder="0.0005"
                    @input="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="Early Stop Patience">
                  <el-input-number
                    v-model="selectedNode.data.patience"
                    :min="0"
                    :max="500"
                    style="width:100%"
                    @change="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="DataLoader Workers">
                  <el-input-number
                    v-model="selectedNode.data.workers"
                    :min="0"
                    :max="16"
                    style="width:100%"
                    @change="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="DDP 进程数">
                  <el-input-number
                    v-model="selectedNode.data.nprocPerNode"
                    :min="1"
                    :max="8"
                    style="width:100%"
                    @change="updateNodeData"
                  />
                </el-form-item>

                <el-form-item label="设备">
                  <el-select v-model="selectedNode.data.device" style="width:100%" @change="updateNodeData">
                    <el-option label="CPU" value="cpu" />
                    <el-option label="GPU 0" value="0" />
                    <el-option label="CUDA 自动" value="cuda" />
                  </el-select>
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

const { screenToFlowCoordinate, addNodes, addEdges } = useVueFlow(FLOW_ID)

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

function getNodeTypeFromEvent(event) {
  const nodeType = event?.currentTarget?.dataset?.nodeType
  return validNodeTypes.has(nodeType) ? nodeType : null
}

function setPendingNodeTypeFromEvent(event) {
  setPendingNodeType(getNodeTypeFromEvent(event))
}

function getDefaultNodeData(type) {
  const defaults = {
    dataset: {
      label: '数据集',
      datasetId: null,
      format: ''
    },

    process: {
      label: '数据处理',
      method: 'normalize',
      valRatio: 20
    },

    // 兼容旧工作流
    model: {
      label: 'YOLO模型',
      familyLabel: 'YOLO',
      framework: 'yolo',
      modelVersion: 'yolov8n',
      modelName: 'yolov8n.pt',
      pretrained: true
    },

    yoloModel: {
      label: 'YOLO模型',
      familyLabel: 'YOLO',
      framework: 'yolo',
      modelVersion: 'yolov8n',
      modelName: 'yolov8n.pt',
      pretrained: true
    },

    resnetModel: {
      label: 'ResNet模型',
      familyLabel: 'ResNet',
      framework: 'resnet',
      modelVersion: 'resnet18',
      modelName: 'resnet18',
      pretrained: true
    },

    mobilenetModel: {
      label: 'MobileNet模型',
      familyLabel: 'MobileNetV3',
      framework: 'mobilenet',
      modelVersion: 'mobilenet_v3_small',
      modelName: 'mobilenet_v3_small',
      pretrained: true
    },

    efficientnetModel: {
      label: 'EfficientNet模型',
      familyLabel: 'EfficientNet',
      framework: 'efficientnet',
      modelVersion: 'efficientnet_b0',
      modelName: 'efficientnet_b0',
      pretrained: true
    },

    unetModel: {
      label: 'UNet模型',
      familyLabel: 'UNet',
      framework: 'unet',
      modelVersion: 'unet',
      modelName: 'unet',
      pretrained: false,
      numClasses: 2
    },

    bertModel: {
      label: 'BERT模型',
      familyLabel: 'BERT',
      framework: 'bert',
      modelVersion: 'bert-base-chinese',
      modelName: 'bert-base-chinese',
      pretrained: true
    },

    trainConfig: {
      label: '训练配置',
      epochs: 50,
      batchSize: 16,
      imgSize: 640,
      learningRate: '0.001',
      optimizer: 'auto',
      scheduler: 'cosine',
      warmupEpochs: 3,
      warmupMomentum: '0.8',
      momentum: '0.937',
      weightDecay: '0.0005',
      patience: 50,
      workers: 0,
      nprocPerNode: 1,
      device: 'cuda'
    },

    eval: {
      label: '评估',
      metrics: ['mAP', 'Loss'],
      evalEvery: 1
    }
  }

  const defaultData = defaults[type] || { label: type }
  return JSON.parse(JSON.stringify(defaultData))
}

function miniMapNodeColor(node) {
  const colors = {
    dataset: '#1890ff',
    process: '#722ed1',

    model: '#722ed1',
    yoloModel: '#13c2c2',
    resnetModel: '#722ed1',
    mobilenetModel: '#2f54eb',
    efficientnetModel: '#389e0d',
    unetModel: '#fa541c',
    bertModel: '#2f54eb',

    trainConfig: '#fa8c16',
    eval: '#52c41a'
  }

  return colors[node.type] || '#409EFF'
}

function onDragStart(event, nodeType) {
  const resolvedType = nodeType || getNodeTypeFromEvent(event) || _dragNodeType
  if (!validNodeTypes.has(resolvedType)) return

  _dragNodeType = resolvedType
  const transfer = event.dataTransfer
  if (!transfer) return

  transfer.clearData()
  transfer.effectAllowed = 'move'
  transfer.setData(NODE_TYPE_TRANSFER_KEY, resolvedType)
}

function onDragEnd() {
  _dragNodeType = null
}

const MODEL_NODE_TYPES = new Set(['model', 'yoloModel', 'resnetModel', 'mobilenetModel', 'efficientnetModel', 'unetModel', 'bertModel'])

const MODEL_VERSION_OPTIONS = {
  yolo: [
    { label: 'YOLOv8n - Nano', value: 'yolov8n', modelName: 'yolov8n.pt' },
    { label: 'YOLOv8s - Small', value: 'yolov8s', modelName: 'yolov8s.pt' },
    { label: 'YOLOv8m - Medium', value: 'yolov8m', modelName: 'yolov8m.pt' },
    { label: 'YOLOv8l - Large', value: 'yolov8l', modelName: 'yolov8l.pt' },
    { label: 'YOLOv8x - XLarge', value: 'yolov8x', modelName: 'yolov8x.pt' }
  ],
  resnet: [
    { label: 'ResNet-18', value: 'resnet18', modelName: 'resnet18' },
    { label: 'ResNet-34', value: 'resnet34', modelName: 'resnet34' },
    { label: 'ResNet-50', value: 'resnet50', modelName: 'resnet50' },
    { label: 'ResNet-101', value: 'resnet101', modelName: 'resnet101' },
    { label: 'ResNet-152', value: 'resnet152', modelName: 'resnet152' }
  ],
  mobilenet: [
    { label: 'MobileNetV3 Small', value: 'mobilenet_v3_small', modelName: 'mobilenet_v3_small' },
    { label: 'MobileNetV3 Large', value: 'mobilenet_v3_large', modelName: 'mobilenet_v3_large' }
  ],
  efficientnet: [
    { label: 'EfficientNet-B0', value: 'efficientnet_b0', modelName: 'efficientnet_b0' }
  ],
  unet: [
    { label: 'UNet', value: 'unet', modelName: 'unet' },
    { label: 'UNet Small', value: 'unet_small', modelName: 'unet_small' }
  ],
  bert: [
    { label: 'BERT Base Chinese', value: 'bert-base-chinese', modelName: 'bert-base-chinese' },
    { label: 'BERT Base Uncased', value: 'bert-base-uncased', modelName: 'bert-base-uncased' }
  ]
}

function isModelNode(node) {
  return !!node && MODEL_NODE_TYPES.has(node.type)
}

const currentModelVersionOptions = computed(() => {
  const framework = selectedNode.value?.data?.framework
  return MODEL_VERSION_OPTIONS[framework] || []
})

function onModelVersionChange() {
  if (!selectedNode.value) return

  const framework = selectedNode.value.data.framework
  const version = selectedNode.value.data.modelVersion
  const options = MODEL_VERSION_OPTIONS[framework] || []
  const option = options.find(item => item.value === version)

  if (option) {
    selectedNode.value.data.modelName = option.modelName
  }

  updateNodeData()
}

const validNodeTypes = new Set([
  'dataset',
  'process',
  'model',
  'yoloModel',
  'resnetModel',
  'mobilenetModel',
  'efficientnetModel',
  'unetModel',
  'bertModel',
  'trainConfig',
  'eval'
])

function onDrop(event) {
  const transfer = event.dataTransfer
  const type = (transfer && transfer.getData(NODE_TYPE_TRANSFER_KEY)) || _dragNodeType
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

const allowedConnectionMap = {
  dataset: ['process', 'trainConfig'],
  process: ['trainConfig'],

  model: ['trainConfig'],
  yoloModel: ['trainConfig'],
  resnetModel: ['trainConfig'],
  mobilenetModel: ['trainConfig'],
  efficientnetModel: ['trainConfig'],
  unetModel: ['trainConfig'],
  bertModel: ['trainConfig'],

  trainConfig: ['eval'],
  eval: []
}

const connectionTipMap = {
  dataset: '数据集节点只能连接到数据处理节点或训练配置节点',
  process: '数据处理节点只能连接到训练配置节点',

  model: '模型节点只能连接到训练配置节点',
  yoloModel: 'YOLO模型节点只能连接到训练配置节点',
  resnetModel: 'ResNet模型节点只能连接到训练配置节点',
  mobilenetModel: 'MobileNet模型节点只能连接到训练配置节点',
  efficientnetModel: 'EfficientNet模型节点只能连接到训练配置节点',
  unetModel: 'UNet模型节点只能连接到训练配置节点',
  bertModel: 'BERT模型节点只能连接到训练配置节点',

  trainConfig: '训练配置节点只能连接到评估节点',
  eval: '评估节点是流程末端节点，不能继续向外连接'
}

function getNodeById(nodeId) {
  return nodes.value.find(n => n.id === nodeId)
}

function isAllowedConnection(sourceType, targetType) {
  return allowedConnectionMap[sourceType]?.includes(targetType) || false
}

function hasPath(sourceId, targetId) {
  if (!sourceId || !targetId) return false
  if (sourceId === targetId) return true

  const visited = new Set()
  const queue = [sourceId]

  while (queue.length > 0) {
    const current = queue.shift()
    if (current === targetId) return true
    if (visited.has(current)) continue
    visited.add(current)

    edges.value
      .filter(e => e.source === current)
      .forEach(e => {
        if (!visited.has(e.target)) queue.push(e.target)
      })
  }

  return false
}

function onConnect(connection) {
  const sourceNode = getNodeById(connection.source)
  const targetNode = getNodeById(connection.target)

  if (!sourceNode || !targetNode) {
    ElMessage.warning('连线失败：节点不存在')
    return
  }

  if (sourceNode.id === targetNode.id) {
    ElMessage.warning('不能连接节点自身')
    return
  }

  if (!isAllowedConnection(sourceNode.type, targetNode.type)) {
    ElMessage.warning(connectionTipMap[sourceNode.type] || '当前节点之间不允许连接')
    return
  }

  if (hasPath(targetNode.id, sourceNode.id)) {
    ElMessage.warning('不能形成循环依赖')
    return
  }

  const duplicated = edges.value.some(
    e => e.source === connection.source && e.target === connection.target
  )
  if (duplicated) {
    ElMessage.warning('这两个节点已经连接过了')
    return
  }

  addEdges([{
    ...connection,
    id: `edge_${connection.source}_${connection.target}_${Date.now()}`
  }])
}

function sanitizeNodes(rawNodes = []) {
  return rawNodes.filter(n => validNodeTypes.has(n.type))
}

function sanitizeEdges(rawEdges = [], validNodes = nodes.value) {
  const nodeMap = new Map(validNodes.map(n => [n.id, n]))
  return rawEdges.filter(edge => {
    const sourceNode = nodeMap.get(edge.source)
    const targetNode = nodeMap.get(edge.target)
    return sourceNode && targetNode && isAllowedConnection(sourceNode.type, targetNode.type)
  })
}

function getSingleNodeByType(type, name) {
  const matched = nodes.value.filter(n => n.type === type)
  if (matched.length === 0) {
    ElMessage.warning(`请添加${name}`)
    return null
  }
  if (matched.length > 1) {
    ElMessage.warning(`${name}暂时只支持保留一个`)
    return null
  }
  return matched[0]
}

function getOptionalSingleNodeByType(type, name) {
  const matched = nodes.value.filter(n => n.type === type)
  if (matched.length > 1) {
    ElMessage.warning(`${name}暂时只支持保留一个`)
    return null
  }
  return matched[0] || null
}

function getSingleModelNode() {
  const matched = nodes.value.filter(n => isModelNode(n))

  if (matched.length === 0) {
    ElMessage.warning('请添加模型节点，例如 YOLO、ResNet、MobileNet、EfficientNet 或 UNet 模型节点')
    return null
  }

  if (matched.length > 1) {
    ElMessage.warning('当前暂时只支持一个模型节点，请只保留 YOLO、ResNet、MobileNet、EfficientNet、UNet、BERT 中的一种')
    return null
  }

  return matched[0]
}

function validateWorkflowBeforeStart() {
  const datasetNode = getSingleNodeByType('dataset', '数据集节点')
  if (!datasetNode) return null

  const modelNode = getSingleModelNode()
  if (!modelNode) return null

  const trainConfigNode = getSingleNodeByType('trainConfig', '训练配置节点')
  if (!trainConfigNode) return null

  const processNode = getOptionalSingleNodeByType('process', '数据处理节点')
  if (processNode === null && nodes.value.some(n => n.type === 'process')) return null

  const evalNode = getOptionalSingleNodeByType('eval', '评估节点')
  if (evalNode === null && nodes.value.some(n => n.type === 'eval')) return null

  if (!datasetNode.data?.datasetId) {
    ElMessage.warning('请在数据集节点中选择数据集')
    return null
  }

  if (!modelNode.data?.modelName) {
    ElMessage.warning('请在模型节点中选择模型版本或填写模型名称/路径')
    return null
  }

  if (!hasPath(datasetNode.id, trainConfigNode.id)) {
    ElMessage.warning('请将数据集节点连接到训练配置节点，可直接连接，也可经过数据处理节点')
    return null
  }

  if (!hasPath(modelNode.id, trainConfigNode.id)) {
    ElMessage.warning('请将模型节点连接到训练配置节点')
    return null
  }

  if (processNode && !hasPath(datasetNode.id, processNode.id)) {
    ElMessage.warning('请将数据集节点连接到数据处理节点')
    return null
  }

  if (processNode && !hasPath(processNode.id, trainConfigNode.id)) {
    ElMessage.warning('请将数据处理节点连接到训练配置节点')
    return null
  }

  if (evalNode && !hasPath(trainConfigNode.id, evalNode.id)) {
    ElMessage.warning('请将训练配置节点连接到评估节点')
    return null
  }

  return {
    datasetNode,
    processNode,
    modelNode,
    trainConfigNode,
    evalNode
  }
}

function normalizeTrainerType(framework) {
  const value = String(framework || '').trim().toLowerCase()

  const aliasMap = {
    yolo: 'yolo',
    yolov5: 'yolo',
    yolov8: 'yolo',
    ultralytics: 'yolo',
    bert: 'bert',
    resnet: 'resnet',
    mobilenet: 'mobilenet',
    mobilenetv3: 'mobilenet',
    mobile_net: 'mobilenet',
    efficientnet: 'efficientnet',
    efficientnet_b0: 'efficientnet',
    efficient_net: 'efficientnet',
    unet: 'unet',
    segmentation: 'unet',
    semantic_segmentation: 'unet'
  }

  return aliasMap[value] || value
}

function buildJobDataFromWorkflow(compiledWorkflow) {
  const { datasetNode, processNode, modelNode, trainConfigNode, evalNode } = compiledWorkflow

  const learningRate = parseFloat(trainConfigNode.data.learningRate)
  const warmupMomentum = parseFloat(trainConfigNode.data.warmupMomentum)
  const momentum = parseFloat(trainConfigNode.data.momentum)
  const weightDecay = parseFloat(trainConfigNode.data.weightDecay)

  const trainerType = normalizeTrainerType(modelNode.data.framework)
  const parsedNumClasses = Number(modelNode.data.numClasses)
  const numClasses = Number.isFinite(parsedNumClasses)
    ? parsedNumClasses : (trainerType === 'unet' ? 2 : undefined)

  return {
    name: workflowName.value,
    project_id: projectId.value,
    workflow_id: currentWorkflowId.value,
    config: {
      trainer_type: trainerType,

      model_node_type: modelNode.type,
      framework: modelNode.data.framework,
      model_family: modelNode.data.familyLabel,
      model_version: modelNode.data.modelVersion,
      model_name: modelNode.data.modelName,
      pretrained: !!modelNode.data.pretrained,
      num_classes: numClasses,

      dataset_id: datasetNode.data.datasetId,

      data_process: processNode
        ? {
            method: processNode.data.method,
            val_ratio: processNode.data.valRatio
          }
        : null,

      epochs: trainConfigNode.data.epochs,
      batch_size: trainConfigNode.data.batchSize,
      img_size: trainConfigNode.data.imgSize || 640,

      lr: Number.isFinite(learningRate) ? learningRate : 0.001,
      learning_rate: Number.isFinite(learningRate) ? learningRate : 0.001,

      optimizer: trainConfigNode.data.optimizer || 'auto',

      scheduler: trainConfigNode.data.scheduler || 'none',
      cos_lr: trainConfigNode.data.scheduler === 'cosine',

      warmup_epochs: trainConfigNode.data.warmupEpochs ?? 3,
      warmup_momentum: Number.isFinite(warmupMomentum) ? warmupMomentum : 0.8,

      momentum: Number.isFinite(momentum) ? momentum : 0.937,
      weight_decay: Number.isFinite(weightDecay) ? weightDecay : 0.0005,

      patience: trainConfigNode.data.patience ?? 50,
      workers: trainConfigNode.data.workers ?? 0,
      nproc_per_node: trainConfigNode.data.nprocPerNode ?? 1,

      device: trainConfigNode.data.device || 'cpu',

      evaluation: evalNode
        ? {
            metrics: evalNode.data.metrics || [],
            eval_every: evalNode.data.evalEvery || 1
          }
        : null,

      workflow: {
        nodes: nodes.value.map(n => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data
        })),
        edges: edges.value.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target
        }))
      }
    }
  }
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

async function saveCanvas(showMessage = true) {
  const shouldNotify = showMessage !== false
  saving.value = true
  try {
    const payload = {
      name: workflowName.value,
      project_id: projectId.value,
      nodes: sanitizeNodes(nodes.value).map(n => ({ id: n.id, type: n.type, position: n.position, data: n.data })),
      edges: sanitizeEdges(edges.value, sanitizeNodes(nodes.value)).map(e => ({ id: e.id, source: e.source, target: e.target }))
    }
    if (currentWorkflowId.value) {
      await updateWorkflow(currentWorkflowId.value, payload)
    } else {
      const res = await createWorkflow(payload)
      currentWorkflowId.value = res?.data?.id || res?.id
    }
    if (shouldNotify) ElMessage.success('画布保存成功')
    return true
  } catch (e) {
    if (shouldNotify) ElMessage.error(e?.response?.data?.message || '保存失败')
    throw e
  } finally {
    saving.value = false
  }
}

async function startTraining() {
  if (nodes.value.length === 0) {
    ElMessage.warning('请先在画布上添加节点')
    return
  }

  const compiledWorkflow = validateWorkflowBeforeStart()
  if (!compiledWorkflow) return

  starting.value = true
  try {
    await saveCanvas(false)
    const jobData = buildJobDataFromWorkflow(compiledWorkflow)
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
      if (wf.nodes) nodes.value = sanitizeNodes(wf.nodes)
      if (wf.edges) edges.value = sanitizeEdges(wf.edges, nodes.value)
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
.unet-model-item { background: linear-gradient(135deg, #fa541c, #d4380d); }
.trainconfig-item { background: linear-gradient(135deg, #fa8c16, #d46b08); }
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
