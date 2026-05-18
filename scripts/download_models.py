#!/usr/bin/env python3
"""
预训练模型下载脚本
将模型下载到本地后，训练平台将从本地路径加载，不需要网络访问。

使用方法：
    python scripts/download_models.py --model yolov8n        # 下载 YOLOv8n
    python scripts/download_models.py --model bert-base      # 下载 BERT-base 中文
    python scripts/download_models.py --all                  # 下载全部模型
    python scripts/download_models.py --list                 # 列出可下载的模型
"""

import os
import sys
import argparse
from pathlib import Path
from tqdm import tqdm

# 模型存放目录（与 backend/.env 中 MODEL_FOLDER 保持一致）
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "models")

# ──────────────────────────────────────────────
# 可下载模型清单
# ──────────────────────────────────────────────
YOLO_MODELS = {
    "yolov8n": {
        "description": "YOLOv8 Nano 目标检测（最小，推荐入门）",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
        "filename": "yolov8n.pt",
        "size_mb": 6,
    },
    "yolov8s": {
        "description": "YOLOv8 Small 目标检测",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt",
        "filename": "yolov8s.pt",
        "size_mb": 22,
    },
    "yolov8m": {
        "description": "YOLOv8 Medium 目标检测",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m.pt",
        "filename": "yolov8m.pt",
        "size_mb": 52,
    },
    "yolov8l": {
        "description": "YOLOv8 Large 目标检测",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8l.pt",
        "filename": "yolov8l.pt",
        "size_mb": 87,
    },
    "yolov8n-cls": {
        "description": "YOLOv8 Nano 图像分类",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n-cls.pt",
        "filename": "yolov8n-cls.pt",
        "size_mb": 5,
    },
    "yolov8n-seg": {
        "description": "YOLOv8 Nano 实例分割",
        "url": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n-seg.pt",
        "filename": "yolov8n-seg.pt",
        "size_mb": 7,
    },
}

HF_BERT_MODELS = {
    "bert-base-chinese": {
        "description": "BERT-Base 中文预训练模型（文本分类首选）",
        "hf_repo": "bert-base-chinese",
        "local_dir": "bert-base-chinese",
        "size_mb": 400,
    },
    "bert-base-uncased": {
        "description": "BERT-Base 英文预训练模型",
        "hf_repo": "bert-base-uncased",
        "local_dir": "bert-base-uncased",
        "size_mb": 440,
    },
    "distilbert-base-uncased": {
        "description": "DistilBERT 英文轻量版（速度快，适合快速验证）",
        "hf_repo": "distilbert-base-uncased",
        "local_dir": "distilbert-base-uncased",
        "size_mb": 265,
    },
    "distilbert-base-chinese": {
        "description": "DistilBERT 中文轻量版",
        "hf_repo": "distilbert-base-chinese",
        "local_dir": "distilbert-base-chinese",
        "size_mb": 265,
    },
}

ALL_MODELS = {**YOLO_MODELS, **HF_BERT_MODELS}


# ──────────────────────────────────────────────
# 下载工具函数
# ──────────────────────────────────────────────

def download_file(url: str, dest_path: Path, expected_size_mb: int = 0) -> bool:
    """带进度条地下载单个文件"""
    import requests
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        print(f"  ✓ 文件已存在，跳过: {dest_path.name}")
        return True

    print(f"  ↓ 正在下载: {url}")
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", expected_size_mb * 1024 * 1024))
        with open(dest_path, "wb") as f, tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=dest_path.name,
        ) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
        print(f"  ✓ 下载完成: {dest_path}")
        return True
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def download_hf_model(repo_id: str, local_dir: Path) -> bool:
    """
    从 Hugging Face 下载 BERT 类模型。
    优先使用 huggingface_hub.snapshot_download，如未安装则回退到 transformers。
    支持设置 HF_ENDPOINT 环境变量以使用镜像站，例如：
        export HF_ENDPOINT=https://hf-mirror.com
    """
    if local_dir.exists() and any(local_dir.iterdir()):
        print(f"  ✓ 目录已存在，跳过: {local_dir}")
        return True

    hf_endpoint = os.environ.get("HF_ENDPOINT", "")
    if hf_endpoint:
        print(f"  ℹ 使用 HF 镜像: {hf_endpoint}")

    local_dir.mkdir(parents=True, exist_ok=True)

    # 优先用 huggingface_hub
    try:
        from huggingface_hub import snapshot_download
        print(f"  ↓ 正在下载 HuggingFace 模型: {repo_id}")
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
        )
        print(f"  ✓ 下载完成: {local_dir}")
        return True
    except ImportError:
        pass

    # 回退到 transformers
    try:
        from transformers import AutoTokenizer, AutoModel
        print(f"  ↓ 正在用 transformers 下载: {repo_id}")
        AutoTokenizer.from_pretrained(repo_id, cache_dir=str(local_dir))
        AutoModel.from_pretrained(repo_id, cache_dir=str(local_dir))
        print(f"  ✓ 下载完成（缓存于）: {local_dir}")
        return True
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return False


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def list_models():
    print("\n━━━━━━━━━━━━━━━━  YOLO 目标检测/分类/分割模型  ━━━━━━━━━━━━━━━━")
    for key, info in YOLO_MODELS.items():
        print(f"  {key:<30}  {info['description']}  (≈{info['size_mb']} MB)")

    print("\n━━━━━━━━━━━━━━━━  BERT 文本分类模型  ━━━━━━━━━━━━━━━━")
    for key, info in HF_BERT_MODELS.items():
        print(f"  {key:<30}  {info['description']}  (≈{info['size_mb']} MB)")
    print()


def download_model(key: str, model_dir: Path) -> bool:
    if key not in ALL_MODELS:
        print(f"✗ 未知模型: {key}，请用 --list 查看可用模型列表")
        return False

    info = ALL_MODELS[key]
    print(f"\n>>> 正在处理: {key} — {info['description']}")

    if key in YOLO_MODELS:
        dest = model_dir / info["filename"]
        return download_file(info["url"], dest, info["size_mb"])
    else:
        local_dir = model_dir / info["local_dir"]
        return download_hf_model(info["hf_repo"], local_dir)


def main():
    parser = argparse.ArgumentParser(
        description="预训练模型下载脚本 —— 将模型保存到本地供训练平台离线加载",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--model",
        metavar="MODEL_KEY",
        help="指定要下载的模型（可多次使用，例如 --model yolov8n --model bert-base-chinese）",
        action="append",
        default=[],
    )
    parser.add_argument("--all", action="store_true", help="下载全部模型（需要大量磁盘空间）")
    parser.add_argument("--list", action="store_true", help="列出全部可下载模型")
    parser.add_argument(
        "--dir",
        default=DEFAULT_MODEL_DIR,
        help=f"模型存放目录（默认: {DEFAULT_MODEL_DIR}）",
    )
    parser.add_argument(
        "--hf-endpoint",
        default="",
        metavar="URL",
        help="HuggingFace 镜像地址，例如 https://hf-mirror.com\n（也可通过 HF_ENDPOINT 环境变量设置）",
    )

    args = parser.parse_args()

    if args.hf_endpoint:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint

    model_dir = Path(args.dir).resolve()
    print(f"模型存放目录: {model_dir}")

    if args.list:
        list_models()
        return

    if args.all:
        targets = list(ALL_MODELS.keys())
    elif args.model:
        targets = args.model
    else:
        parser.print_help()
        print("\n提示: 使用 --list 查看可下载模型，使用 --model <名称> 下载指定模型")
        sys.exit(0)

    success, failed = [], []
    for key in targets:
        ok = download_model(key, model_dir)
        (success if ok else failed).append(key)

    print("\n" + "━" * 50)
    print(f"下载完成: {len(success)} 个成功, {len(failed)} 个失败")
    if failed:
        print(f"失败的模型: {', '.join(failed)}")
    print(f"\n模型已保存到: {model_dir}")
    print("训练平台将从以上目录加载模型，无需网络访问。")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
