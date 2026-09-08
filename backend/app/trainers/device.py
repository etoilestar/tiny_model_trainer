"""Shared accelerator selection for CUDA, Ascend NPU, and CPU deployments."""

import importlib
import importlib.util
import os
from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class Accelerator:
    kind: str
    index: int | None
    device: torch.device

    @property
    def distributed_backend(self) -> str:
        return {"cuda": "nccl", "npu": "hccl"}.get(self.kind, "gloo")


def _load_torch_npu() -> bool:
    """Load torch_npu when installed; importing it registers ``torch.npu``."""
    if importlib.util.find_spec("torch_npu") is None:
        return False
    importlib.import_module("torch_npu")
    return hasattr(torch, "npu")


def npu_is_available() -> bool:
    return _load_torch_npu() and bool(torch.npu.is_available())


def _parse_device(requested: object) -> tuple[str, int | None]:
    value = str(requested or os.getenv("DEVICE_TYPE", "auto")).strip().lower()
    if value == "0":  # Backward compatibility with the old CUDA-only UI.
        return "cuda", 0
    if value in {"auto", "cpu", "cuda", "npu"}:
        return value, None
    for kind in ("cuda", "npu"):
        prefix = f"{kind}:"
        if value.startswith(prefix):
            try:
                return kind, int(value[len(prefix):])
            except ValueError as exc:
                raise ValueError(f"无效的设备编号: {value}") from exc
    raise ValueError(f"不支持的设备配置: {value}，可选 auto/cpu/cuda[:N]/npu[:N]")


def resolve_accelerator(requested: object = None, local_rank: int = 0) -> Accelerator:
    """Resolve and activate the requested accelerator without silent fallback."""
    kind, requested_index = _parse_device(requested)
    index = local_rank if requested_index is None else requested_index

    if kind == "auto":
        preferred = os.getenv("DEVICE_TYPE", "auto").strip().lower()
        if preferred == "npu" and npu_is_available():
            kind = "npu"
        elif preferred == "cuda" and torch.cuda.is_available():
            kind = "cuda"
        elif npu_is_available():
            kind = "npu"
        elif torch.cuda.is_available():
            kind = "cuda"
        else:
            kind = "cpu"

    if kind == "npu":
        if not npu_is_available():
            raise RuntimeError("请求使用 Ascend NPU，但 torch_npu 未安装或 NPU 不可用")
        torch.npu.set_device(index)
        return Accelerator("npu", index, torch.device(f"npu:{index}"))

    if kind == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("请求使用 CUDA GPU，但 CUDA 不可用")
        torch.cuda.set_device(index)
        return Accelerator("cuda", index, torch.device("cuda", index))

    return Accelerator("cpu", None, torch.device("cpu"))


def accelerator_summary() -> dict:
    """Return a serializable snapshot useful for startup logs and diagnostics."""
    return {
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
        "npu_available": npu_is_available(),
        "npu_count": int(torch.npu.device_count()) if npu_is_available() else 0,
    }
