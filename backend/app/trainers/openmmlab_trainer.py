import logging
import os
from pathlib import Path
from typing import Callable, Optional

from .base import BaseTrainer


# ---------------------------------------------------------------------------
# MMEngine hook – relays per-epoch metrics and log lines to our callbacks
# ---------------------------------------------------------------------------

class _TrainingProgressHook:
    """
    Minimal MMEngine-compatible Hook that forwards training progress to the
    tiny_trainer callback API.

    MMEngine calls hook methods by name via runner.call_hook(...).  We only
    need to implement the two methods we care about; everything else falls
    back to the Hook base-class no-ops.
    """

    # MMEngine priority constants: lower number == higher priority.
    # 'LOW' (60) is fine for a monitoring-only hook.
    priority = 60

    def __init__(
        self,
        total_epochs: int,
        log_callback: Callable[[str, str], None],
        metric_callback: Callable[[int, str, float, int], None],
    ) -> None:
        self.total_epochs = total_epochs
        self.log_callback = log_callback
        self.metric_callback = metric_callback

    # ------------------------------------------------------------------
    # Satisfy the MMEngine Hook interface (no-ops for unused hooks)
    # ------------------------------------------------------------------

    def before_run(self, runner) -> None:
        pass

    def after_run(self, runner) -> None:
        pass

    def before_train(self, runner) -> None:
        pass

    def after_train(self, runner) -> None:
        pass

    def before_train_epoch(self, runner) -> None:
        pass

    def after_train_iter(self, runner, batch_idx, data_batch=None, outputs=None) -> None:
        pass

    def before_train_iter(self, runner, batch_idx, data_batch=None) -> None:
        pass

    def before_val(self, runner) -> None:
        pass

    def after_val(self, runner) -> None:
        pass

    def before_val_epoch(self, runner) -> None:
        pass

    def after_val_iter(self, runner, batch_idx, data_batch=None, outputs=None) -> None:
        pass

    def before_val_iter(self, runner, batch_idx, data_batch=None) -> None:
        pass

    def before_save_checkpoint(self, runner, checkpoint) -> None:
        pass

    def after_load_checkpoint(self, runner, checkpoint) -> None:
        pass

    # ------------------------------------------------------------------
    # The hooks we actually use
    # ------------------------------------------------------------------

    def after_train_epoch(self, runner) -> None:
        # runner.epoch is 0-indexed *before* the post-epoch increment
        epoch = runner.epoch + 1
        self.log_callback('INFO', f'Epoch {epoch}/{self.total_epochs} 训练完成')

    def after_val_epoch(self, runner, metrics: Optional[dict] = None) -> None:
        epoch = runner.epoch + 1
        if metrics:
            for name, value in metrics.items():
                try:
                    self.metric_callback(epoch, name, float(value), epoch)
                except (TypeError, ValueError):
                    pass
            self.log_callback(
                'INFO',
                f'Epoch {epoch}/{self.total_epochs} 验证完成，指标: {metrics}',
            )
        else:
            self.log_callback('INFO', f'Epoch {epoch}/{self.total_epochs} 验证完成')


# ---------------------------------------------------------------------------
# Python logging handler – forwards MMEngine log records to log_callback
# ---------------------------------------------------------------------------

class _MMEngineLogHandler(logging.Handler):
    """Attach to the 'mmengine' root logger to relay records to log_callback."""

    def __init__(self, log_callback: Callable[[str, str], None]) -> None:
        super().__init__()
        self.log_callback = log_callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.log_callback(record.levelname, self.format(record))
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# Config builders
# ---------------------------------------------------------------------------

def _build_resnet_cfg(config: dict) -> dict:
    """Return a dict that MMEngine's Runner.from_cfg() can consume for ResNet
    image classification (via mmpretrain)."""

    model_folder = config.get('model_folder', './models')
    model_name = config.get('model_name', 'resnet50')
    dataset_path = config.get('dataset_path', '')
    epochs = int(config.get('epochs', 10))
    batch_size = int(config.get('batch_size', 32))
    lr = float(config.get('lr', 0.01))
    num_classes = int(config.get('num_classes', 10))
    checkpoint_dir = config.get('checkpoint_dir', './checkpoints')
    workers = int(config.get('workers', 2))
    img_size = int(config.get('img_size', 224))

    depth_map = {
        'resnet18': 18, 'resnet34': 34, 'resnet50': 50,
        'resnet101': 101, 'resnet152': 152,
    }
    depth = depth_map.get(model_name.lower(), 50)
    # Channels at the output of stage-4
    out_channels = 512 if depth <= 34 else 2048

    pretrained = os.path.join(model_folder, f'{model_name}.pth')
    init_cfg = (
        dict(type='Pretrained', checkpoint=pretrained)
        if os.path.exists(pretrained)
        else None
    )

    dataset_root = Path(dataset_path)
    train_root = (
        str(dataset_root / 'train')
        if (dataset_root / 'train').is_dir()
        else str(dataset_root)
    )
    val_root = (
        str(dataset_root / 'val')
        if (dataset_root / 'val').is_dir()
        else train_root
    )
    work_dir = os.path.join(checkpoint_dir, 'resnet_run')

    backbone_cfg = dict(
        type='ResNet',
        depth=depth,
        num_stages=4,
        out_indices=(3,),
        style='pytorch',
    )
    if init_cfg:
        backbone_cfg['init_cfg'] = init_cfg

    short_edge = int(img_size * 256 / 224)

    return dict(
        default_scope='mmpretrain',
        model=dict(
            type='ImageClassifier',
            backbone=backbone_cfg,
            neck=dict(type='GlobalAveragePooling'),
            head=dict(
                type='LinearClsHead',
                num_classes=num_classes,
                in_channels=out_channels,
                loss=dict(type='CrossEntropyLoss', loss_weight=1.0),
                topk=(1, 5) if num_classes >= 5 else (1,),
            ),
        ),
        train_dataloader=dict(
            batch_size=batch_size,
            num_workers=workers,
            persistent_workers=workers > 0,
            sampler=dict(type='DefaultSampler', shuffle=True),
            dataset=dict(
                type='CustomDataset',
                data_root=train_root,
                with_label=True,
                pipeline=[
                    dict(type='LoadImageFromFile'),
                    dict(type='RandomResizedCrop', scale=img_size),
                    dict(type='RandomFlip', prob=0.5, direction='horizontal'),
                    dict(type='PackInputs'),
                ],
            ),
        ),
        val_dataloader=dict(
            batch_size=batch_size,
            num_workers=workers,
            persistent_workers=workers > 0,
            sampler=dict(type='DefaultSampler', shuffle=False),
            dataset=dict(
                type='CustomDataset',
                data_root=val_root,
                with_label=True,
                pipeline=[
                    dict(type='LoadImageFromFile'),
                    dict(type='ResizeEdge', scale=short_edge, edge='short'),
                    dict(type='CenterCrop', crop_size=img_size),
                    dict(type='PackInputs'),
                ],
            ),
        ),
        val_evaluator=dict(type='Accuracy', topk=(1,)),
        optim_wrapper=dict(
            type='OptimWrapper',
            optimizer=dict(type='SGD', lr=lr, momentum=0.9, weight_decay=1e-4),
        ),
        param_scheduler=dict(
            type='MultiStepLR',
            by_epoch=True,
            milestones=[max(1, int(epochs * 0.6)), max(1, int(epochs * 0.8))],
            gamma=0.1,
        ),
        train_cfg=dict(type='EpochBasedTrainLoop', max_epochs=epochs, val_interval=1),
        val_cfg=dict(type='ValLoop'),
        default_hooks=dict(
            timer=dict(type='IterTimerHook'),
            logger=dict(type='LoggerHook', interval=10),
            param_scheduler=dict(type='ParamSchedulerHook'),
            checkpoint=dict(
                type='CheckpointHook',
                interval=1,
                save_best='accuracy/top1',
                rule='greater',
            ),
            sampler_seed=dict(type='DistSamplerSeedHook'),
            visualization=dict(type='VisualizationHook', enable=False),
        ),
        visualizer=dict(
            type='UniversalVisualizer',
            vis_backends=[dict(type='LocalVisBackend')],
        ),
        env_cfg=dict(
            mp_cfg=dict(mp_start_method='fork', opencv_num_threads=0),
            dist_cfg=dict(backend='nccl'),
        ),
        log_processor=dict(window_size=10, by_epoch=True),
        log_level='INFO',
        load_from=None,
        resume=False,
        work_dir=work_dir,
        launcher='none',
    )


def _build_unet_cfg(config: dict) -> dict:
    """Return a dict that MMEngine's Runner.from_cfg() can consume for UNet
    semantic segmentation (via mmseg).

    Expected dataset layout::

        dataset_path/
            images/
                train/  *.jpg
                val/    *.jpg
            annotations/
                train/  *.png   (single-channel class-index masks)
                val/    *.png
    """

    dataset_path = config.get('dataset_path', '')
    epochs = int(config.get('epochs', 10))
    batch_size = int(config.get('batch_size', 4))
    lr = float(config.get('lr', 0.01))
    num_classes = int(config.get('num_classes', 2))
    checkpoint_dir = config.get('checkpoint_dir', './checkpoints')
    workers = int(config.get('workers', 2))
    img_size = int(config.get('img_size', 256))
    img_dir = config.get('img_dir', 'images')
    ann_dir = config.get('ann_dir', 'annotations')
    img_suffix = config.get('img_suffix', '.jpg')
    seg_map_suffix = config.get('seg_map_suffix', '.png')

    work_dir = os.path.join(checkpoint_dir, 'unet_run')

    return dict(
        default_scope='mmseg',
        model=dict(
            type='EncoderDecoder',
            data_preprocessor=dict(
                type='SegDataPreProcessor',
                mean=[123.675, 116.28, 103.53],
                std=[58.395, 57.12, 57.375],
                bgr_to_rgb=True,
                pad_val=0,
                seg_pad_val=255,
            ),
            backbone=dict(
                type='UNet',
                in_channels=3,
                base_channels=64,
                num_stages=5,
                strides=(1, 1, 1, 1, 1),
                enc_num_convs=(2, 2, 2, 2, 2),
                dec_num_convs=(2, 2, 2, 2),
                downsamples=(True, True, True, True),
                enc_dilations=(1, 1, 1, 1, 1),
                dec_dilations=(1, 1, 1, 1),
                with_cp=False,
                conv_cfg=None,
                norm_cfg=dict(type='BN'),
                act_cfg=dict(type='ReLU'),
                upsample_cfg=dict(type='InterpConv'),
                norm_eval=False,
            ),
            decode_head=dict(
                type='FCNHead',
                in_channels=64,
                in_index=4,
                channels=64,
                num_convs=1,
                concat_input=False,
                dropout_ratio=0.1,
                num_classes=num_classes,
                norm_cfg=dict(type='BN'),
                align_corners=False,
                loss_decode=dict(
                    type='CrossEntropyLoss',
                    use_sigmoid=False,
                    loss_weight=1.0,
                ),
            ),
            auxiliary_head=None,
            train_cfg=dict(),
            test_cfg=dict(mode='whole'),
        ),
        train_dataloader=dict(
            batch_size=batch_size,
            num_workers=workers,
            persistent_workers=workers > 0,
            sampler=dict(type='DefaultSampler', shuffle=True),
            dataset=dict(
                type='BaseSegDataset',
                data_root=str(dataset_path),
                img_suffix=img_suffix,
                seg_map_suffix=seg_map_suffix,
                data_prefix=dict(
                    img_path=f'{img_dir}/train',
                    seg_map_path=f'{ann_dir}/train',
                ),
                pipeline=[
                    dict(type='LoadImageFromFile'),
                    dict(type='LoadAnnotations'),
                    dict(
                        type='RandomCrop',
                        crop_size=(img_size, img_size),
                        cat_max_ratio=0.75,
                    ),
                    dict(type='RandomFlip', prob=0.5),
                    dict(type='PhotoMetricDistortion'),
                    dict(type='PackSegInputs'),
                ],
            ),
        ),
        val_dataloader=dict(
            batch_size=1,
            num_workers=workers,
            persistent_workers=workers > 0,
            sampler=dict(type='DefaultSampler', shuffle=False),
            dataset=dict(
                type='BaseSegDataset',
                data_root=str(dataset_path),
                img_suffix=img_suffix,
                seg_map_suffix=seg_map_suffix,
                data_prefix=dict(
                    img_path=f'{img_dir}/val',
                    seg_map_path=f'{ann_dir}/val',
                ),
                pipeline=[
                    dict(type='LoadImageFromFile'),
                    dict(type='Resize', scale=(img_size, img_size), keep_ratio=True),
                    dict(type='LoadAnnotations'),
                    dict(type='PackSegInputs'),
                ],
            ),
        ),
        val_evaluator=dict(type='IoUMetric', iou_metrics=['mIoU']),
        optim_wrapper=dict(
            type='OptimWrapper',
            optimizer=dict(type='SGD', lr=lr, momentum=0.9, weight_decay=5e-4),
            clip_grad=None,
        ),
        param_scheduler=dict(
            type='PolyLR',
            eta_min=1e-4,
            power=0.9,
            begin=0,
            end=epochs,
            by_epoch=True,
        ),
        train_cfg=dict(type='EpochBasedTrainLoop', max_epochs=epochs, val_interval=1),
        val_cfg=dict(type='ValLoop'),
        default_hooks=dict(
            timer=dict(type='IterTimerHook'),
            logger=dict(type='LoggerHook', interval=50),
            param_scheduler=dict(type='ParamSchedulerHook'),
            checkpoint=dict(
                type='CheckpointHook',
                interval=1,
                save_best='mIoU',
                rule='greater',
            ),
            sampler_seed=dict(type='DistSamplerSeedHook'),
            visualization=dict(type='SegVisualizationHook', draw=False),
        ),
        visualizer=dict(
            type='SegLocalVisualizer',
            vis_backends=[dict(type='LocalVisBackend')],
            name='visualizer',
        ),
        env_cfg=dict(
            mp_cfg=dict(mp_start_method='fork', opencv_num_threads=0),
            dist_cfg=dict(backend='nccl'),
        ),
        log_processor=dict(window_size=50, by_epoch=True),
        log_level='INFO',
        load_from=None,
        resume=False,
        work_dir=work_dir,
        launcher='none',
    )


# ---------------------------------------------------------------------------
# Trainer class
# ---------------------------------------------------------------------------

class OpenMMLabTrainer(BaseTrainer):
    """
    OpenMMLab-based trainer supporting:

    * ResNet image classification  (trainer_type='resnet')  via mmpretrain
    * UNet semantic segmentation   (trainer_type='unet')    via mmseg

    Both use MMEngine's Runner under the hood, which handles the training loop,
    checkpointing, and logging.

    Required config keys
    --------------------
    trainer_type    : 'resnet' | 'unet'
    dataset_path    : path to the dataset root directory
    model_folder    : directory that may contain pretrained .pth weights
    checkpoint_dir  : directory where checkpoints are written
    epochs          : number of training epochs (default 10)
    batch_size      : mini-batch size
    lr              : initial learning rate
    num_classes     : number of output classes
    img_size        : spatial resolution used for training / validation crops

    ResNet-only
    -----------
    model_name      : 'resnet18' | 'resnet34' | 'resnet50' | 'resnet101' | 'resnet152'
                      (default 'resnet50')

    UNet-only
    ---------
    img_dir         : sub-directory inside dataset_path that holds images (default 'images')
    ann_dir         : sub-directory inside dataset_path that holds masks   (default 'annotations')
    img_suffix      : image file extension (default '.jpg')
    seg_map_suffix  : mask  file extension (default '.png')
    """

    def train(
        self,
        config: dict,
        log_callback: Callable[[str, str], None],
        metric_callback: Callable[[int, str, float, int], None],
    ) -> dict:
        try:
            from mmengine.runner import Runner
            from mmengine.config import Config
        except ImportError as exc:
            raise RuntimeError(
                f'mmengine 未安装或导入失败: {exc}。'
                '请执行: pip install mmengine'
            ) from exc

        trainer_type = config.get('trainer_type', '').lower()

        if trainer_type == 'resnet':
            try:
                import mmpretrain  # noqa: F401 – ensure the scope is registered
            except ImportError as exc:
                raise RuntimeError(
                    f'mmpretrain 未安装或导入失败: {exc}。'
                    '请执行: pip install mmpretrain'
                ) from exc
            cfg_dict = _build_resnet_cfg(config)
            best_metric_key = 'accuracy/top1'

        elif trainer_type == 'unet':
            try:
                import mmseg  # noqa: F401 – ensure the scope is registered
            except ImportError as exc:
                raise RuntimeError(
                    f'mmseg 未安装或导入失败: {exc}。'
                    '请执行: pip install mmseg'
                ) from exc
            cfg_dict = _build_unet_cfg(config)
            best_metric_key = 'mIoU'

        else:
            raise ValueError(
                f'OpenMMLabTrainer 不支持的 trainer_type: {trainer_type}，'
                '支持: resnet, unet'
            )

        epochs = int(config.get('epochs', 10))

        # Attach a Python log handler to mmengine's logger so we can forward
        # its output to our log_callback.
        mm_logger = logging.getLogger('mmengine')
        log_handler = _MMEngineLogHandler(log_callback)
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        mm_logger.addHandler(log_handler)

        progress_hook = _TrainingProgressHook(epochs, log_callback, metric_callback)

        final_metrics: dict = {}
        best_model_path: Optional[str] = None

        try:
            cfg = Config(cfg_dict)
            log_callback('INFO', f'启动 OpenMMLab [{trainer_type.upper()}] 训练')
            log_callback('INFO', f'工作目录: {cfg.work_dir}')

            runner = Runner.from_cfg(cfg)
            runner.register_hook(progress_hook)

            runner.train()

            # Collect final metrics from the message hub
            try:
                scalars = runner.message_hub.log_scalars
                for key, meter in scalars.items():
                    try:
                        val = meter.mean
                        metric_callback(epochs, key, float(val), epochs)
                        final_metrics[key] = float(val)
                    except (TypeError, ValueError, AttributeError):
                        pass
            except Exception:
                pass

            # Locate best checkpoint
            work_dir = Path(cfg.work_dir)
            best_ckpt = work_dir / 'best_checkpoint.pth'
            if not best_ckpt.exists():
                # CheckpointHook names the file based on the metric
                candidates = sorted(work_dir.glob('best_*.pth'))
                if candidates:
                    best_ckpt = candidates[-1]

            if best_ckpt.exists():
                best_model_path = str(best_ckpt)

            log_callback(
                'INFO',
                f'OpenMMLab [{trainer_type.upper()}] 训练完成，'
                f'最优模型: {best_model_path}',
            )

        finally:
            mm_logger.removeHandler(log_handler)

        return {
            'metrics': final_metrics,
            'best_model_path': best_model_path,
        }
