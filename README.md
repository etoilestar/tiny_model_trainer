# tiny_model_trainer

**可视化小模型训练系统** —— 基于拖拽式画布的端到端模型训练与管理平台。

---

## 项目背景

随着行业场景中视觉识别、文本分类、目标检测、语义分割、实体抽取等小模型训练需求不断增加，传统模型训练流程通常依赖算法工程师手工编写脚本、准备配置文件、管理数据集、启动训练任务、查看日志并导出模型。这种方式对非算法人员门槛较高，也不利于训练过程标准化、模型产物管理和后续部署复用。

本项目建设一套**基于可视化画布拖拽的模型训练系统**，用户可以通过拖拽节点的方式完成数据接入、数据处理、模型选择、训练配置、评估验证、模型导出和服务发布等全流程。系统底层集成 OpenMMLab、YOLO、BERT/Transformers 等训练能力，面向图像、文本以及后续多模态任务，形成一套覆盖全流程的小模型训练与管理平台。

---

## 核心能力

- 🎨 **可视化画布编排**：拖拽节点组建训练流程，支持节点参数配置、连线类型校验和流程版本管理
- 📦 **多格式数据集管理**：支持图像分类、目标检测（YOLO/COCO/VOC）、语义分割、文本分类、序列标注等数据格式
- 🚀 **多框架训练支持**：集成 YOLO、OpenMMLab、Hugging Face Transformers，通过统一适配器层屏蔽框架差异
- 📊 **训练过程可视化**：实时日志回传、Loss 曲线、学习率曲线、评估指标（mAP、Accuracy、F1、IoU 等）展示
- 🗂️ **模型版本管理**：模型注册、版本对比、最优模型自动选择、checkpoint 管理
- 📤 **模型导出部署**：支持 PyTorch / ONNX / TorchScript 导出，一键发布 REST API 推理服务
- 🔒 **统一对象存储**：数据集、日志、checkpoint、导出模型统一存入 MinIO，跨节点一致访问

---

## 技术架构

系统采用分层架构，分为前端交互层、后端编排层、训练适配器层、任务执行层、数据与产物管理层。

```
前端画布 (Vue Flow)
    ↓
Canvas DAG JSON
    ↓
Pipeline IR（统一训练流程中间表示）
    ↓
Framework Adapter（YOLO / OpenMMLab / Transformers）
    ↓
Docker Swarm Training Job
    ↓
Metrics / Checkpoint / Model Artifact → MinIO
```

### 技术栈

| 层次 | 技术选型 |
|------|----------|
| **前端** | Vue 3、Vue Flow、Element Plus、ECharts、Pinia、Vue Router、WebSocket/SSE |
| **后端** | Flask、Flask-RESTful、SQLAlchemy、Marshmallow/Pydantic、Celery、Redis |
| **数据库** | PostgreSQL / MySQL |
| **对象存储** | MinIO |
| **任务调度** | Docker Swarm、Docker SDK |
| **训练框架** | PyTorch、Ultralytics YOLO、OpenMMLab、Hugging Face Transformers |
| **模型导出** | ONNX Runtime、TorchScript、TensorRT（后续扩展） |

---

## 画布节点体系

画布节点按照训练生命周期分为以下几大类：

| 节点类别 | 说明 |
|----------|------|
| **数据接入节点** | 本地上传、MinIO、YOLO/COCO/VOC/ImageFolder/CSV/JSONL 等格式数据集接入 |
| **数据校验节点** | 完整性校验、标注格式校验、类别统计、训练/验证集比例检查 |
| **数据处理节点** | 数据划分、格式转换、图像 Resize/Normalize/增强、文本清洗/Tokenizer |
| **模型选择节点** | YOLO、OpenMMLab、BERT、Sentence-BERT、自定义 PyTorch、历史模型版本 |
| **训练配置节点** | 超参数、优化器、学习率策略、Batch Size、混合精度、冻结层微调、Early Stop |
| **训练执行节点** | YOLO 检测/分割/姿态、OpenMMLab 分类/检测/分割、BERT 分类/序列标注 |
| **评估节点** | 分类/检测/分割/文本指标，混淆矩阵、PR 曲线、ROC 曲线、模型对比 |
| **模型导出节点** | PyTorch / ONNX / TorchScript / TensorRT / OpenVINO 导出 |
| **模型注册节点** | 注册模型、创建版本、绑定指标、最优模型自动选择 |
| **部署推理节点** | REST API 推理服务、批量推理、在线测试、版本切换、服务回滚 |
| **控制流节点** | 条件判断、分支、合并、失败重试、人工确认、并行训练 |

每个节点通过声明输入端口、输出端口和参数 Schema 进行类型约束，禁止不兼容的节点连接。

---

## 阶段规划

### 第一阶段：基础框架与最小闭环
- 画布拖拽组件与节点基础数据结构
- 后端 API、任务队列与 Worker
- 数据集上传与管理（YOLO 格式）
- YOLO 目标检测训练节点（含日志实时回传、指标展示、checkpoint 保存）

### 第二阶段：多任务训练能力扩展
- OpenMMLab 图像分类 / 目标检测 / 语义分割
- BERT 文本分类
- 多任务评估指标统一展示
- 训练配置模板与模型版本管理

### 第三阶段：模型导出、部署与推理闭环
- ONNX / TorchScript 导出
- 模型仓库与版本注册
- 推理服务发布与在线测试
- REST API 调用示例自动生成

### 第四阶段：高级训练能力与平台化增强
- 单机多卡 / 分布式训练
- 自动超参数搜索
- 模型蒸馏 / 剪枝 / 量化
- 多租户权限与资源配额管理
- 实验对比与自动训练报告

---

## 项目里程碑

| 里程碑 | 关键交付 |
|--------|----------|
| M1 基础平台原型 | 用户登录、项目管理、数据集上传、画布编辑、训练任务列表、日志展示 |
| M2 YOLO 训练闭环 | YOLO 数据校验、训练执行、日志回传、mAP 展示、best.pt 保存 |
| M3 OpenMMLab 视觉扩展 | 图像分类 / 目标检测 / 语义分割训练，视觉任务指标统一展示 |
| M4 BERT 文本任务扩展 | 文本分类训练、文本推理测试、BERT checkpoint 管理 |
| M5 模型导出与部署 | ONNX 导出、模型注册、推理服务发布、在线推理测试 |
| M6 平台化增强 | 多用户权限、资源配额、实验对比、训练报告、模型压缩 |

---

## 数据库核心表

`user` · `project` · `dataset` · `dataset_version` · `workflow` · `workflow_version` · `training_job` · `training_log` · `metric` · `model` · `model_version` · `model_artifact` · `deployment` · `inference_record`

---

## MinIO 对象存储路径规范

```
/minio-bucket
  /projects/{project_id}/datasets/{dataset_id}/{version}/
  /projects/{project_id}/workflows/{workflow_id}/{version}/
  /projects/{project_id}/jobs/{job_id}/logs/
  /projects/{project_id}/jobs/{job_id}/checkpoints/
  /projects/{project_id}/jobs/{job_id}/metrics/
  /projects/{project_id}/models/{model_id}/{version}/
  /projects/{project_id}/exports/{export_id}/
  /projects/{project_id}/reports/{report_id}/
```

---

## 部署方式（第一阶段）

采用 Docker Swarm Stack 统一部署，包含以下服务容器：

- Vue 前端服务
- Flask API 服务
- Worker 训练执行服务
- Redis 消息队列
- PostgreSQL / MySQL 数据库
- MinIO 对象存储
- Docker Registry 镜像仓库
- Nginx 网关

---

## 推荐开发顺序

1. 系统基础框架
2. 数据集管理
3. YOLO 目标检测闭环（最先打通）
4. 抽象 Pipeline IR
5. 接入 OpenMMLab
6. 接入 BERT/Transformers
7. 模型导出
8. 模型仓库
9. 推理服务发布
10. 高级训练与资源调度

> 优先以 YOLO 目标检测打通最小闭环，验证画布流程可以被稳定转换为真实训练任务且结果可被平台统一管理，再逐步扩展。

---

## 能力闭环

```
数据接入 → 数据校验 → 数据处理 → 模型选择 → 训练配置
    → 任务执行 → 指标评估 → 模型导出 → 模型注册 → 服务发布
```

---

## License

MIT
