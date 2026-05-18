import os
from typing import Callable

from .base import BaseTrainer


class YOLOTrainer(BaseTrainer):
    """YOLO object-detection trainer backed by the ultralytics library."""

    def train(
        self,
        config: dict,
        log_callback: Callable[[str, str], None],
        metric_callback: Callable[[int, str, float, int], None],
    ) -> dict:
        try:
            from ultralytics import YOLO
        except ImportError:
            raise RuntimeError('ultralytics 未安装，请执行: pip install ultralytics')

        model_folder = config.get('model_folder', './models')
        model_name = config.get('model_name', 'yolov8n.pt')
        model_path = os.path.join(model_folder, model_name)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f'模型文件不存在: {model_path}')

        dataset_path = config.get('dataset_path')
        if not dataset_path or not os.path.exists(dataset_path):
            raise FileNotFoundError(f'数据集路径不存在: {dataset_path}')

        epochs = int(config.get('epochs', 10))
        batch_size = int(config.get('batch_size', 16))
        lr = float(config.get('lr', 0.01))
        img_size = int(config.get('img_size', 640))
        checkpoint_dir = config.get('checkpoint_dir', './checkpoints')

        log_callback('INFO', f'加载 YOLO 模型: {model_path}')
        model = YOLO(model_path)

        # Build a per-epoch callback to relay metrics
        def on_train_epoch_end(trainer_obj):
            epoch = trainer_obj.epoch + 1  # 0-indexed internally
            metrics = trainer_obj.metrics or {}
            for key, value in metrics.items():
                try:
                    metric_callback(epoch, key, float(value), epoch)
                except (TypeError, ValueError):
                    pass
            log_callback('INFO', f'Epoch {epoch}/{epochs} 完成，指标: {metrics}')

        model.add_callback('on_train_epoch_end', on_train_epoch_end)

        log_callback('INFO', f'开始 YOLO 训练: epochs={epochs}, batch={batch_size}, lr={lr}')

        results = model.train(
            data=dataset_path,
            epochs=epochs,
            batch=batch_size,
            lr0=lr,
            imgsz=img_size,
            project=checkpoint_dir,
            name='run',
            exist_ok=True,
            verbose=True,
        )

        # Collect final results
        final_metrics: dict = {}
        if results and hasattr(results, 'results_dict'):
            for k, v in results.results_dict.items():
                try:
                    metric_callback(epochs, k, float(v), epochs)
                    final_metrics[k] = float(v)
                except (TypeError, ValueError):
                    pass

        best_model_path = os.path.join(checkpoint_dir, 'run', 'weights', 'best.pt')
        log_callback('INFO', f'YOLO 训练完成，最优模型: {best_model_path}')

        return {
            'metrics': final_metrics,
            'best_model_path': best_model_path if os.path.exists(best_model_path) else None,
        }
