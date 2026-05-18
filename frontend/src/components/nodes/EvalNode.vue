<template>
  <div class="flow-node eval-node" :class="{ selected }">
    <Handle type="target" :position="Position.Left" />

    <div class="node-header">
      <el-icon size="16"><data-analysis /></el-icon>
      <span class="node-title">评估</span>
    </div>
    <div class="node-body">
      <div class="node-field">
        <span class="field-label">指标：</span>
        <div class="metrics-tags">
          <el-tag
            v-for="m in (data.metrics || ['Loss'])"
            :key="m"
            size="small"
            type="success"
            effect="plain"
          >
            {{ m }}
          </el-tag>
        </div>
      </div>
      <div class="node-field">
        <span class="field-label">评估频率：</span>
        <span class="field-value">每 {{ data.evalEvery || 1 }} 轮</span>
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
  border-color: #52c41a;
  box-shadow: 0 0 0 3px rgba(82, 196, 26, 0.25);
}

.eval-node .node-header {
  background: linear-gradient(135deg, #52c41a, #389e0d);
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
  align-items: flex-start;
  gap: 4px;
  margin-bottom: 6px;
}

.node-field:last-child {
  margin-bottom: 0;
}

.field-label {
  color: #909399;
  font-size: 11px;
  white-space: nowrap;
  padding-top: 2px;
}

.field-value {
  color: #303133;
  font-size: 12px;
  font-weight: 500;
}

.metrics-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}
</style>
