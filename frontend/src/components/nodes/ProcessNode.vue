<template>
  <div class="flow-node process-node" :class="{ selected }">
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />

    <div class="node-header">
      <el-icon size="16"><operation /></el-icon>
      <span class="node-title">数据处理</span>
    </div>
    <div class="node-body">
      <div class="node-field">
        <span class="field-label">处理方式：</span>
        <el-tag size="small" type="warning">{{ methodLabel }}</el-tag>
      </div>
      <div class="node-field" v-if="data.method === 'split'">
        <span class="field-label">验证集比例：</span>
        <span class="field-value">{{ data.valRatio || 20 }}%</span>
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

const methodLabel = computed(() => {
  const map = { normalize: '标准化', augment: '数据增强', split: '分割训练/验证集' }
  return map[props.data.method] || props.data.method || '标准化'
})
</script>

<style scoped>
.flow-node {
  border-radius: 10px;
  min-width: 160px;
  max-width: 220px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 2px solid transparent;
  transition: border-color 0.2s, box-shadow 0.2s;
  cursor: pointer;
  font-size: 12px;
}

.flow-node.selected {
  border-color: #722ed1;
  box-shadow: 0 0 0 3px rgba(114, 46, 209, 0.25);
}

.process-node .node-header {
  background: linear-gradient(135deg, #722ed1, #531dab);
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
  min-width: 52px;
}

.field-value {
  color: #303133;
  font-size: 12px;
  font-weight: 500;
}
</style>
