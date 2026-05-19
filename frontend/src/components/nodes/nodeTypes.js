import { markRaw } from 'vue'
import DatasetNode from './DatasetNode.vue'
import ModelNode from './ModelNode.vue'
import TrainConfigNode from './TrainConfigNode.vue'
import TrainExecNode from './TrainExecNode.vue'
import ProcessNode from './ProcessNode.vue'
import EvalNode from './EvalNode.vue'

/**
 * Node type map for VueFlow.
 * Defined at module scope (not inside component setup) so Vue never wraps it
 * in a reactive proxy — required by VueFlow to resolve custom node components
 * correctly.
 */
export const nodeTypes = markRaw({
  dataset: DatasetNode,
  model: ModelNode,
  trainConfig: TrainConfigNode,
  eval: EvalNode,
  process: ProcessNode,
  trainExec: TrainExecNode
})
