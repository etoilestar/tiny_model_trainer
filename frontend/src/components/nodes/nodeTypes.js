import { markRaw } from 'vue'
import DatasetNode from './DatasetNode.vue'
import ModelNode from './ModelNode.vue'
import TrainConfigNode from './TrainConfigNode.vue'
import ProcessNode from './ProcessNode.vue'
import EvalNode from './EvalNode.vue'

/**
 * Node type map for VueFlow.
 */
export const nodeTypes = markRaw({
  dataset: DatasetNode,
  process: ProcessNode,

  // 兼容旧版通用模型节点
  model: ModelNode,

  // 明确模型族节点
  yoloModel: ModelNode,
  resnetModel: ModelNode,
  mobilenetModel: ModelNode,
  efficientnetModel: ModelNode,
  unetModel: ModelNode,
  bertModel: ModelNode,

  trainConfig: TrainConfigNode,
  eval: EvalNode
})
