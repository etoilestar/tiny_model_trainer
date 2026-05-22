<template>
  <div class="flow-node trainconfig-node" :class="{ selected }">
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />

    <div class="node-header">
      <el-icon size="16"><data-line /></el-icon>
      <span class="node-title">训练配置</span>
    </div>

    <div class="node-body">
      <div class="node-field">
        <span class="field-label">Epochs：</span>
        <span class="field-value">{{ data.epochs || 50 }}</span>
      </div>

      <div class="node-field">
        <span class="field-label">Batch：</span>
        <span class="field-value">{{ data.batchSize || 16 }}</span>
      </div>

      <div class="node-field">
        <span class="field-label">LR：</span>
        <span class="field-value">{{ data.learningRate || '0.001' }}</span>
      </div>

      <div class="node-field">
        <span class="field-label">优化器：</span>
        <el-tag size="small" type="warning">{{ optimizerLabel }}</el-tag>
      </div>

      <div class="node-field">
        <span class="field-label">调度：</span>
        <el-tag size="small" :type="schedulerTagType">{{ schedulerLabel }}</el-tag>
      </div>

      <div class="node-field">
        <span class="field-label">Warmup：</span>
        <span class="field-value">{{ data.warmupEpochs ?? 3 }} epoch</span>
      </div>

      <div class="node-field">
        <span class="field-label">设备：</span>
        <el-tag size="small" :type="data.device === 'cuda' || data.device === '0' ? 'success' : 'info'">
          {{ data.device === 'cuda' || data.device === '0' ? 'GPU' : 'CPU' }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: String,
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const optimizerLabel = computed(() => {
  const value = props.data.optimizer || 'auto'
  const map = {
    auto: 'AUTO',
    SGD: 'SGD',
    Adam: 'Adam',
    AdamW: 'AdamW',
    adam: 'Adam',
    adamw: 'AdamW',
    sgd: 'SGD'
  }
  return map[value] || String(value).toUpperCase()
})

const schedulerLabel = computed(() => {
  const value = props.data.scheduler || 'none'
  const map = {
    none: '无',
    cosine: '余弦退火',
    step: 'StepLR',
    multistep: 'MultiStepLR'
  }
  return map[value] || value
})

const schedulerTagType = computed(() => {
  return props.data.scheduler === 'cosine' ? 'success' : 'info'
})
</script>

<style scoped>
.flow-node {
  border-radius: 10px;
  min-width: 170px;
  max-width: 240px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 2px solid transparent;
  transition: border-color 0.2s, box-shadow 0.2s;
  cursor: pointer;
  font-size: 12px;
}

.flow-node.selected {
  border-color: #fa8c16;
  box-shadow: 0 0 0 3px rgba(250, 140, 22, 0.25);
}

.trainconfig-node .node-header {
  background: linear-gradient(135deg, #fa8c16, #d46b08);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px 8px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.node-title {
  font-weight: 600;
  font-size: 13px;
}

.node-body {
  background: #fff;
  padding: 10px 12px;
  border-radius: 0 0 8px 8px;
}

.node-field {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 5px;
}

.node-field:last-child {
  margin-bottom: 0;
}

.field-label {
  color: #909399;
  font-size: 11px;
  white-space: nowrap;
  min-width: 56px;
}

.field-value {
  color: #303133;
  font-size: 12px;
  font-weight: 500;
}
</style>