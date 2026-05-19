<template>
  <div class="flow-node trainexec-node" :class="{ selected }">
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />

    <div class="node-header">
      <el-icon size="16"><video-play /></el-icon>
      <span class="node-title">训练执行</span>
    </div>
    <div class="node-body">
      <div class="node-field">
        <span class="field-label">任务名称：</span>
        <span class="field-value">{{ data.jobName || '训练任务' }}</span>
      </div>
      <div class="node-field">
        <span class="field-label">输出目录：</span>
        <span class="field-value">{{ data.outputDir || './outputs' }}</span>
      </div>
      <div class="node-field">
        <span class="field-label">保存最优：</span>
        <el-tag size="small" :type="data.saveBest ? 'success' : 'info'">
          {{ data.saveBest ? '是' : '否' }}
        </el-tag>
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
  border-color: #fa541c;
  box-shadow: 0 0 0 3px rgba(250, 84, 28, 0.25);
}

.trainexec-node .node-header {
  background: linear-gradient(135deg, #fa541c, #d4380d);
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
