<template>
  <div class="flow-node dataset-node" :class="{ selected }">
    <Handle type="source" :position="Position.Right" />

    <div class="node-header">
      <el-icon size="16"><files /></el-icon>
      <span class="node-title">数据集</span>
    </div>
    <div class="node-body">
      <div class="node-field">
        <span class="field-label">名称：</span>
        <span class="field-value">{{ data.label || '未命名' }}</span>
      </div>
      <div class="node-field" v-if="data.format">
        <span class="field-label">格式：</span>
        <el-tag size="small" type="info">{{ data.format }}</el-tag>
      </div>
      <div class="node-field" v-if="data.datasetId">
        <span class="field-label">ID：</span>
        <span class="field-value">{{ data.datasetId }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'

defineProps({
  id: String,
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
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
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.25);
}

.dataset-node .node-header {
  background: linear-gradient(135deg, #1890ff, #096dd9);
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
}

.field-value {
  color: #303133;
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}
</style>
