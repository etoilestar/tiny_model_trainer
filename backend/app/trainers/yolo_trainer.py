import os
import zipfile
import hashlib
from pathlib import Path
from typing import Callable, Any

import yaml

from .base import BaseTrainer


def _is_zip_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".zip"


def _safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_root = extract_dir.resolve()

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target_path = (extract_root / member.filename).resolve()

            # 防止 zip slip：禁止压缩包写出 extract_root
            if not str(target_path).startswith(str(extract_root)):
                raise RuntimeError(f"非法压缩包路径: {member.filename}")

        zf.extractall(extract_root)


def _find_data_yaml(dataset_dir: Path) -> Path:
    candidates = []

    for name in ("data.yaml", "data.yml"):
        direct = dataset_dir / name
        if direct.exists():
            return direct

    for pattern in ("**/data.yaml", "**/data.yml"):
        candidates.extend(dataset_dir.glob(pattern))

    candidates = [p for p in candidates if p.is_file()]

    if not candidates:
        raise FileNotFoundError(f"未找到 YOLO data.yaml: {dataset_dir}")

    # 优先选择层级最浅的 data.yaml
    candidates.sort(key=lambda p: len(p.relative_to(dataset_dir).parts))
    return candidates[0]


def _resolve_path_entry(entry: Any, root: Path) -> Any:
    """
    支持 YOLO yaml 中 train/val/test 为字符串或列表。
    相对路径会根据 root 转成绝对路径。
    """
    if entry is None:
        return None

    if isinstance(entry, list):
        return [_resolve_path_entry(x, root) for x in entry]

    if not isinstance(entry, str):
        return entry

    p = Path(entry)
    if p.is_absolute():
        return str(p)

    return str((root / p).resolve())


def _prepare_yolo_data_yaml(dataset_path: str, dataset_root: str | None = None) -> str:
    """
    将任意 YOLO 数据集路径规范化为一个绝对路径版 data.yaml。

    支持三种输入：
    1. /path/to/data.yaml
    2. /path/to/dataset_dir
    3. /path/to/dataset.zip

    输出：
    /tmp/tiny_trainer_yolo_data/xxx.fixed.yaml
    """
    if not dataset_path:
        raise FileNotFoundError("dataset_path 为空")

    src = Path(dataset_path)

    # 如果是 zip，先解压到统一数据集根目录
    if _is_zip_file(src):
        root = Path(dataset_root or os.environ.get("DATASET_ROOT", "/app/datasets"))
        extract_dir = root / src.stem

        # 如果还没解压，或者目录里找不到 data.yaml，就解压
        try:
            _find_data_yaml(extract_dir)
        except FileNotFoundError:
            _safe_extract_zip(src, extract_dir)

        data_yaml = _find_data_yaml(extract_dir)

    elif src.is_dir():
        data_yaml = _find_data_yaml(src)

    elif src.is_file():
        data_yaml = src

    else:
        raise FileNotFoundError(f"数据集路径不存在: {src}")

    with data_yaml.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    yaml_dir = data_yaml.parent.resolve()

    # YOLO 原始 path 规则：
    # - 如果 path 是绝对路径，直接使用
    # - 如果 path 是相对路径，相对 data.yaml 所在目录解析
    # - 如果没有 path，则默认 data.yaml 所在目录
    raw_path = cfg.get("path", None)
    if raw_path:
        raw_root = Path(str(raw_path))
        if raw_root.is_absolute():
            dataset_base = raw_root.resolve()
        else:
            dataset_base = (yaml_dir / raw_root).resolve()
    else:
        dataset_base = yaml_dir

    if "train" not in cfg:
        raise FileNotFoundError(f"data.yaml 缺少 train 字段: {data_yaml}")

    if "val" not in cfg:
        raise FileNotFoundError(f"data.yaml 缺少 val 字段: {data_yaml}")

    fixed_cfg = dict(cfg)
    fixed_cfg["path"] = str(dataset_base)
    fixed_cfg["train"] = _resolve_path_entry(cfg.get("train"), dataset_base)
    fixed_cfg["val"] = _resolve_path_entry(cfg.get("val"), dataset_base)

    if "test" in cfg:
        fixed_cfg["test"] = _resolve_path_entry(cfg.get("test"), dataset_base)

    # 简单检查 train/val 目录是否存在，方便提前报出清楚错误
    for key in ("train", "val"):
        value = fixed_cfg.get(key)

        check_paths = value if isinstance(value, list) else [value]

        for p in check_paths:
            if isinstance(p, str) and not Path(p).exists():
                raise FileNotFoundError(
                    f"YOLO 数据集字段 {key} 指向的路径不存在: {p}，"
                    f"原始 data.yaml: {data_yaml}"
                )

    out_dir = Path("/tmp/tiny_trainer_yolo_data")
    out_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.md5(str(data_yaml.resolve()).encode("utf-8")).hexdigest()[:10]
    fixed_yaml = out_dir / f"{data_yaml.parent.name}_{digest}.fixed.yaml"

    with fixed_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(fixed_cfg, f, allow_unicode=True, sort_keys=False)

    return str(fixed_yaml)


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
        except ImportError as exc:
            raise RuntimeError(
                f"ultralytics 或其依赖导入失败: {exc}. "
                "如果错误与 cv2/Qt/libGL 有关，请使用 opencv-python-headless。"
            ) from exc

        model_folder = config.get("model_folder", "./models")
        model_name = config.get("model_name", "yolov8n.pt")

        model_candidate = Path(model_name)
        if model_candidate.is_absolute():
            model_path = model_candidate
        else:
            model_path = Path(model_folder) / model_name

        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        raw_dataset_path = config.get("dataset_path")
        dataset_root = config.get("dataset_root") or os.environ.get("DATASET_ROOT", "/app/datasets")

        dataset_path = _prepare_yolo_data_yaml(
            raw_dataset_path,
            dataset_root=dataset_root,
        )

        if not dataset_path or not Path(dataset_path).exists():
            raise FileNotFoundError(f"数据集配置文件不存在: {dataset_path}")

        epochs = int(config.get("epochs", 10))
        batch_size = int(config.get("batch_size", 16))
        lr = float(config.get("lr", 0.01))
        img_size = int(config.get("img_size", 640))
        checkpoint_dir = config.get("checkpoint_dir", "./checkpoints")

        optimizer = config.get("optimizer", "auto")
        optimizer_map = {
            "auto": "auto",
            "sgd": "SGD",
            "SGD": "SGD",
            "adam": "Adam",
            "Adam": "Adam",
            "adamw": "AdamW",
            "AdamW": "AdamW",
        }
        optimizer = optimizer_map.get(optimizer, optimizer)

        scheduler = config.get("scheduler", "none")
        cos_lr = bool(config.get("cos_lr", scheduler == "cosine"))

        warmup_epochs = float(config.get("warmup_epochs", 3.0))
        warmup_momentum = float(config.get("warmup_momentum", 0.8))
        momentum = float(config.get("momentum", 0.937))
        weight_decay = float(config.get("weight_decay", 0.0005))
        patience = int(config.get("patience", 50))
        workers = int(config.get("workers", 0))

        device = config.get("device", "cpu")
        if device == "cuda":
            device = 0

        log_callback("INFO", f"加载 YOLO 模型: {model_path}")
        log_callback("INFO", f"使用 YOLO 数据配置: {dataset_path}")

        model = YOLO(str(model_path))

        def on_train_epoch_end(trainer_obj):
            epoch = trainer_obj.epoch + 1
            metrics = trainer_obj.metrics or {}

            for key, value in metrics.items():
                try:
                    metric_callback(epoch, key, float(value), epoch)
                except (TypeError, ValueError):
                    pass

            log_callback("INFO", f"Epoch {epoch}/{epochs} 完成，指标: {metrics}")

        model.add_callback("on_train_epoch_end", on_train_epoch_end)

        log_callback(
            "INFO",
            (
                f"开始 YOLO 训练: epochs={epochs}, batch={batch_size}, lr={lr}, "
                f"optimizer={optimizer}, scheduler={scheduler}, cos_lr={cos_lr}, "
                f"warmup_epochs={warmup_epochs}, device={device}"
            ),
        )

        results = model.train(
            data=dataset_path,
            epochs=epochs,
            batch=batch_size,
            lr0=lr,
            imgsz=img_size,
            project=checkpoint_dir,
            name="run",
            exist_ok=True,
            verbose=True,

            optimizer=optimizer,
            cos_lr=cos_lr,
            warmup_epochs=warmup_epochs,
            warmup_momentum=warmup_momentum,
            momentum=momentum,
            weight_decay=weight_decay,
            patience=patience,

            # Celery worker 里建议保持 0，避免 daemonic process 问题
            workers=workers,

            device=device,
        )

        final_metrics: dict = {}
        if results and hasattr(results, "results_dict"):
            for k, v in results.results_dict.items():
                try:
                    metric_callback(epochs, k, float(v), epochs)
                    final_metrics[k] = float(v)
                except (TypeError, ValueError):
                    pass

        best_model_path = Path(checkpoint_dir) / "run" / "weights" / "best.pt"

        log_callback("INFO", f"YOLO 训练完成，最优模型: {best_model_path}")

        return {
            "metrics": final_metrics,
            "best_model_path": str(best_model_path) if best_model_path.exists() else None,
        }