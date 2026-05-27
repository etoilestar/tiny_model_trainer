<template>
  <div
    class="flow-node model-node"
    :class="[`model-node-${data.framework || 'generic'}`, { selected }]"
  >
    <Handle type="source" :position="Position.Right" />

    <div class="node-header">
      <el-icon size="16"><setting /></el-icon>
      <span class="node-title">{{ title }}</span>
    </div>

    <div class="node-body">
      <div class="node-field">
        <span class="field-label">类型：</span>
        <el-tag size="small" type="warning">{{ familyLabel }}</el-tag>
      </div>

      <div class="node-field">
        <span class="field-label">版本：</span>
        <span class="field-value">{{ data.modelVersion || '-' }}</span>
      </div>

      <div class="node-field">
        <span class="field-label">模型：</span>
        <span class="field-value">{{ data.modelName || '未设置' }}</span>
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

const familyLabel = computed(() => {
  const map = {
    yolo: 'YOLO',
    resnet: 'ResNet',
    mobilenet: 'MobileNetV3',
    efficientnet: 'EfficientNet',
    unet: 'UNet',
    bert: 'BERT',
    custom: '自定义'
  }
  return map[props.data.framework] || props.data.framework || '模型'
})

const title = computed(() => {
  const map = {
    yolo: 'YOLO 模型',
    resnet: 'ResNet 模型',
    mobilenet: 'MobileNet 模型',
    efficientnet: 'EfficientNet 模型',
    unet: 'UNet 模型',
    bert: 'BERT 模型',
    custom: '自定义模型'
  }
  return map[props.data.framework] || '模型节点'
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
  border-color: #722ed1;
  box-shadow: 0 0 0 3px rgba(114, 46, 209, 0.25);
}

.model-node .node-header {
  background: linear-gradient(135deg, #722ed1, #531dab);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px 8px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.model-node-yolo .node-header {
  background: linear-gradient(135deg, #13c2c2, #08979c);
}

.model-node-resnet .node-header {
  background: linear-gradient(135deg, #722ed1, #531dab);
}

.model-node-mobilenet .node-header {
  background: linear-gradient(135deg, #2f54eb, #1d39c4);
}

.model-node-efficientnet .node-header {
  background: linear-gradient(135deg, #389e0d, #237804);
}

.model-node-unet .node-header {
  background: linear-gradient(135deg, #fa541c, #d4380d);
}

.model-node-bert .node-header {
  background: linear-gradient(135deg, #2f54eb, #1d39c4);
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
  min-width: 40px;
}

.field-value {
  color: #303133;
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}
</style>
