import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

from .base import BaseTrainer


class NativeVisionTrainer(BaseTrainer):
    """
    Native PyTorch vision trainer launcher.

    This class intentionally does not run the training loop in the Celery
    process. It launches a separate torchrun process instead, so a low-level
    CUDA/C++ crash cannot kill the Celery worker process.

    Supported trainer_type values:
      - resnet: ImageFolder classification
      - unet: image/mask semantic segmentation

    The subprocess writes JSONL events to stdout. This launcher forwards those
    events to tiny_trainer's log and metric callbacks.
    """

    def train(
        self,
        config: dict,
        log_callback: Callable[[str, str], None],
        metric_callback: Callable[[int, str, float, int], None],
    ) -> dict:
        trainer_type = str(config.get("trainer_type", "")).lower().strip()
        if trainer_type not in {"resnet", "unet"}:
            raise ValueError(f"NativeVisionTrainer 不支持的 trainer_type: {trainer_type}")

        dataset_path = config.get("dataset_path")
        if not dataset_path:
            raise ValueError("缺少 dataset_path，请先选择数据集或传入 dataset_path")
        if not os.path.exists(str(dataset_path)):
            raise FileNotFoundError(f"dataset_path 不存在: {dataset_path}")

        checkpoint_dir = Path(config.get("checkpoint_dir") or "./checkpoints")
        run_id = f"native_{trainer_type}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        run_dir = checkpoint_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Make the run directory explicit so the subprocess and registry agree
        # on checkpoint locations.
        config = dict(config)
        config["run_dir"] = str(run_dir)
        config["checkpoint_dir"] = str(checkpoint_dir)

        config_path = run_dir / "config.json"
        result_path = run_dir / "result.json"
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        entry_path = Path(__file__).resolve().parent / "native_vision_ddp_entry.py"
        if not entry_path.exists():
            raise FileNotFoundError(f"训练入口脚本不存在: {entry_path}")

        nproc_per_node = int(
            config.get("nproc_per_node")
            or config.get("ddp_world_size")
            or config.get("world_size")
            or 1
        )
        if nproc_per_node < 1:
            nproc_per_node = 1

        cmd = [
            sys.executable,
            "-m",
            "torch.distributed.run",
            "--standalone",
            f"--nproc_per_node={nproc_per_node}",
            str(entry_path),
            "--config",
            str(config_path),
            "--result",
            str(result_path),
        ]

        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("OMP_NUM_THREADS", str(config.get("omp_num_threads", 1)))
        env.setdefault("MKL_NUM_THREADS", str(config.get("mkl_num_threads", 1)))
        env.setdefault("TOKENIZERS_PARALLELISM", "false")

        cuda_visible_devices = config.get("cuda_visible_devices")
        if cuda_visible_devices not in (None, ""):
            env["CUDA_VISIBLE_DEVICES"] = str(cuda_visible_devices)

        log_callback("INFO", f"启动原生 PyTorch [{trainer_type.upper()}] DDP 训练子进程")
        log_callback("INFO", f"运行目录: {run_dir}")
        log_callback("INFO", "启动命令: " + " ".join(cmd))

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            bufsize=1,
        )

        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            self._handle_subprocess_line(line, log_callback, metric_callback)

        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                f"原生 PyTorch [{trainer_type.upper()}] 训练子进程异常退出，returncode={return_code}。"
                f"请查看日志，运行目录: {run_dir}"
            )

        if not result_path.exists():
            raise RuntimeError(f"训练子进程未生成结果文件: {result_path}")

        with result_path.open("r", encoding="utf-8") as f:
            result = json.load(f)

        best_model_path: Optional[str] = result.get("best_model_path")
        if best_model_path and not os.path.exists(best_model_path):
            log_callback("WARNING", f"结果中的 best_model_path 不存在: {best_model_path}")

        log_callback("INFO", f"原生 PyTorch [{trainer_type.upper()}] 训练完成，最优模型: {best_model_path}")
        return result

    @staticmethod
    def _handle_subprocess_line(
        line: str,
        log_callback: Callable[[str, str], None],
        metric_callback: Callable[[int, str, float, int], None],
    ) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            log_callback("INFO", line)
            return

        event_type = event.get("type")
        if event_type == "log":
            level = str(event.get("level") or "INFO").upper()
            message = str(event.get("message") or "")
            log_callback(level, message)
            return

        if event_type == "metric":
            try:
                epoch = int(event.get("epoch", 0))
                step = int(event.get("step", epoch))
                name = str(event.get("name"))
                value = float(event.get("value"))
                metric_callback(epoch, name, value, step)
            except Exception as exc:
                log_callback("WARNING", f"指标事件解析失败: {event}，错误: {exc}")
            return

        if event_type == "result":
            log_callback("INFO", f"训练结果: {json.dumps(event, ensure_ascii=False)}")
            return

        log_callback("INFO", line)
