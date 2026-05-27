import { markRaw } from 'vue'
import DatasetNode from './DatasetNode.vue'
import ModelNode from './ModelNode.vue'
import TrainConfigNode from './TrainConfigNode.vue'
import ProcessNode from './ProcessNode.vue'
import EvalNode from './EvalNode.vue'

/**
 * Node type map for VueFlow.
 *
 * 注意：
 * - 不再把“模型选择”作为一个总节点暴露给用户；
 * - 画布上使用 yoloModel / resnetModel / mobilenetModel / efficientnetModel / unetModel / bertModel 等明确模型族节点；
 * - model 保留只是为了兼容历史保存的旧工作流。
 */
export const nodeTypes = markRaw({
  dataset: DatasetNode,
  process: ProcessNode,

  // 兼容旧版通用模型节点
  model: ModelNode,

  // 新版明确模型族节点
  yoloModel: ModelNode,
  resnetModel: ModelNode,
  mobilenetModel: ModelNode,
  efficientnetModel: ModelNode,
  unetModel: ModelNode,
  bertModel: ModelNode,

  trainConfig: TrainConfigNode,
  eval: EvalNode
})
