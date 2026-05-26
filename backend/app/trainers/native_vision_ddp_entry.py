import argparse
import json
import math
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, Dataset
from torch.utils.data.distributed import DistributedSampler
from torchvision import datasets, models, transforms


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def emit(event: dict) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


def log(level: str, message: str) -> None:
    if is_rank0():
        emit({"type": "log", "level": level.upper(), "message": message})


def metric(epoch: int, name: str, value: float, step: Optional[int] = None) -> None:
    if is_rank0():
        emit({"type": "metric", "epoch": int(epoch), "step": int(step or epoch), "name": name, "value": float(value)})


def is_dist() -> bool:
    return dist.is_available() and dist.is_initialized()


def get_rank() -> int:
    return dist.get_rank() if is_dist() else 0


def get_world_size() -> int:
    return dist.get_world_size() if is_dist() else 1


def is_rank0() -> bool:
    return get_rank() == 0


def setup_distributed(device: torch.device) -> None:
    if "RANK" not in os.environ or "WORLD_SIZE" not in os.environ:
        return
    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    if world_size < 1:
        return
    backend = "nccl" if device.type == "cuda" else "gloo"
    dist.init_process_group(backend=backend, init_method="env://")


def cleanup_distributed() -> None:
    if is_dist():
        dist.barrier()
        dist.destroy_process_group()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device(config: dict) -> torch.device:
    requested = str(config.get("device", "cuda" if torch.cuda.is_available() else "cpu")).lower()
    if requested.startswith("cuda") and torch.cuda.is_available():
        local_rank = int(os.environ.get("LOCAL_RANK", "0"))
        torch.cuda.set_device(local_rank)
        return torch.device("cuda", local_rank)
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Classification: ImageFolder + torchvision ResNet
# ---------------------------------------------------------------------------


def build_resnet_model(model_name: str, num_classes: int) -> nn.Module:
    name = model_name.lower().strip()
    builders = {
        "resnet18": models.resnet18,
        "resnet34": models.resnet34,
        "resnet50": models.resnet50,
        "resnet101": models.resnet101,
        "resnet152": models.resnet152,
    }
    if name not in builders:
        raise ValueError(f"不支持的 ResNet 模型: {model_name}，支持: {', '.join(sorted(builders))}")

    # 默认不自动下载预训练权重，保证离线环境可运行。
    # 如需加载预训练权重，建议后续扩展为从 /app/models 加载本地 checkpoint。
    model = builders[name](weights=None)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def build_classification_loaders(config: dict) -> Tuple[DataLoader, DataLoader, int, List[str]]:
    dataset_root = Path(config["dataset_path"]).resolve()
    train_root = dataset_root / "train" if (dataset_root / "train").is_dir() else dataset_root
    val_root = dataset_root / "val" if (dataset_root / "val").is_dir() else train_root

    img_size = int(config.get("img_size", 224))
    batch_size = int(config.get("batch_size", 16))
    workers = int(config.get("workers", 0))

    train_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_set = datasets.ImageFolder(str(train_root), transform=train_tf)
    val_set = datasets.ImageFolder(str(val_root), transform=val_tf)

    if len(train_set.classes) < 2:
        raise ValueError("ResNet 分类数据集至少需要 2 个类别目录")

    if is_dist():
        train_sampler = DistributedSampler(train_set, shuffle=True, drop_last=False)
        val_sampler = DistributedSampler(val_set, shuffle=False, drop_last=False)
        shuffle = False
    else:
        train_sampler = None
        val_sampler = None
        shuffle = True

    train_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=shuffle,
        sampler=train_sampler,
        num_workers=workers,
        pin_memory=True,
        persistent_workers=workers > 0,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=batch_size,
        shuffle=False,
        sampler=val_sampler,
        num_workers=workers,
        pin_memory=True,
        persistent_workers=workers > 0,
    )
    return train_loader, val_loader, len(train_set.classes), list(train_set.classes)


# ---------------------------------------------------------------------------
# Segmentation: minimal UNet + image/mask dataset
# ---------------------------------------------------------------------------


class SegmentationDataset(Dataset):
    def __init__(self, image_dir: Path, mask_dir: Path, img_size: int) -> None:
        self.image_dir = image_dir
        self.mask_dir = mask_dir
        self.img_size = img_size
        self.samples = self._collect_pairs(image_dir, mask_dir)
        if not self.samples:
            raise ValueError(f"没有找到图像/mask 配对: images={image_dir}, masks={mask_dir}")

    @staticmethod
    def _collect_pairs(image_dir: Path, mask_dir: Path) -> List[Tuple[Path, Path]]:
        image_files = [p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
        mask_by_stem: Dict[str, Path] = {p.stem: p for p in mask_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png"}
        pairs = []
        for img in sorted(image_files):
            mask = mask_by_stem.get(img.stem)
            if mask:
                pairs.append((img, mask))
        return pairs

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        img_path, mask_path = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path)

        image = image.resize((self.img_size, self.img_size), Image.BILINEAR)
        mask = mask.resize((self.img_size, self.img_size), Image.NEAREST)

        image_arr = np.asarray(image, dtype=np.float32) / 255.0
        image_arr = (image_arr - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        image_tensor = torch.from_numpy(image_arr.transpose(2, 0, 1)).float()

        mask_arr = np.asarray(mask, dtype=np.int64)
        if mask_arr.ndim == 3:
            mask_arr = mask_arr[..., 0]
        mask_tensor = torch.from_numpy(mask_arr).long()
        return image_tensor, mask_tensor


class DoubleConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Down(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.MaxPool2d(2), DoubleConv(in_ch, out_ch))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Up(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.up = nn.ConvTranspose2d(in_ch, in_ch // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv(in_ch, out_ch)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        x1 = self.up(x1)
        diff_y = x2.size(2) - x1.size(2)
        diff_x = x2.size(3) - x1.size(3)
        x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
        return self.conv(torch.cat([x2, x1], dim=1))


class TinyUNet(nn.Module):
    def __init__(self, in_channels: int = 3, num_classes: int = 2, base_channels: int = 32) -> None:
        super().__init__()
        c = base_channels
        self.inc = DoubleConv(in_channels, c)
        self.down1 = Down(c, c * 2)
        self.down2 = Down(c * 2, c * 4)
        self.down3 = Down(c * 4, c * 8)
        self.up1 = Up(c * 8, c * 4)
        self.up2 = Up(c * 4, c * 2)
        self.up3 = Up(c * 2, c)
        self.outc = nn.Conv2d(c, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x = self.up1(x4, x3)
        x = self.up2(x, x2)
        x = self.up3(x, x1)
        return self.outc(x)


def build_segmentation_loaders(config: dict) -> Tuple[DataLoader, DataLoader, int, List[str]]:
    dataset_root = Path(config["dataset_path"]).resolve()
    img_dir = str(config.get("img_dir", "images"))
    ann_dir = str(config.get("ann_dir", "annotations"))
    train_img = dataset_root / img_dir / "train"
    val_img = dataset_root / img_dir / "val"
    train_mask = dataset_root / ann_dir / "train"
    val_mask = dataset_root / ann_dir / "val"

    for p in [train_img, train_mask]:
        if not p.is_dir():
            raise ValueError(f"UNet 数据集缺少目录: {p}")
    if not val_img.is_dir() or not val_mask.is_dir():
        val_img, val_mask = train_img, train_mask

    img_size = int(config.get("img_size", 256))
    batch_size = int(config.get("batch_size", 4))
    workers = int(config.get("workers", 0))
    num_classes = int(config.get("num_classes", 2))
    class_names = [f"class_{i}" for i in range(num_classes)]

    train_set = SegmentationDataset(train_img, train_mask, img_size)
    val_set = SegmentationDataset(val_img, val_mask, img_size)

    if is_dist():
        train_sampler = DistributedSampler(train_set, shuffle=True, drop_last=False)
        val_sampler = DistributedSampler(val_set, shuffle=False, drop_last=False)
        shuffle = False
    else:
        train_sampler = None
        val_sampler = None
        shuffle = True

    train_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=shuffle,
        sampler=train_sampler,
        num_workers=workers,
        pin_memory=True,
        persistent_workers=workers > 0,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=batch_size,
        shuffle=False,
        sampler=val_sampler,
        num_workers=workers,
        pin_memory=True,
        persistent_workers=workers > 0,
    )
    return train_loader, val_loader, num_classes, class_names


# ---------------------------------------------------------------------------
# Common train / val utilities
# ---------------------------------------------------------------------------


def build_optimizer(config: dict, model: nn.Module) -> torch.optim.Optimizer:
    lr = float(config.get("lr", config.get("learning_rate", 1e-3)))
    weight_decay = float(config.get("weight_decay", 1e-4))
    optimizer = str(config.get("optimizer", "adamw")).lower()

    params = [p for p in model.parameters() if p.requires_grad]
    if optimizer == "sgd":
        momentum = float(config.get("momentum", 0.9))
        return torch.optim.SGD(params, lr=lr, momentum=momentum, weight_decay=weight_decay)
    return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)


def reduce_tensor(t: torch.Tensor) -> torch.Tensor:
    if is_dist():
        dist.all_reduce(t, op=dist.ReduceOp.SUM)
    return t


def train_one_epoch(model: nn.Module, loader: DataLoader, optimizer, criterion, device, epoch: int, task: str) -> float:
    model.train()
    total_loss = torch.tensor(0.0, device=device)
    total_count = torch.tensor(0.0, device=device)

    sampler = getattr(loader, "sampler", None)
    if isinstance(sampler, DistributedSampler):
        sampler.set_epoch(epoch)

    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        logits = model(images)
        loss = criterion(logits, targets)
        loss.backward()
        optimizer.step()

        bs = images.size(0)
        total_loss += loss.detach() * bs
        total_count += bs

    reduce_tensor(total_loss)
    reduce_tensor(total_count)
    return float((total_loss / total_count.clamp_min(1.0)).item())


@torch.no_grad()
def validate_classification(model: nn.Module, loader: DataLoader, criterion, device) -> Tuple[float, float]:
    model.eval()
    total_loss = torch.tensor(0.0, device=device)
    total_correct = torch.tensor(0.0, device=device)
    total_count = torch.tensor(0.0, device=device)

    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        logits = model(images)
        loss = criterion(logits, targets)
        pred = logits.argmax(dim=1)

        bs = images.size(0)
        total_loss += loss * bs
        total_correct += (pred == targets).sum()
        total_count += bs

    reduce_tensor(total_loss)
    reduce_tensor(total_correct)
    reduce_tensor(total_count)
    avg_loss = float((total_loss / total_count.clamp_min(1.0)).item())
    acc = float((total_correct / total_count.clamp_min(1.0)).item())
    return avg_loss, acc


@torch.no_grad()
def validate_segmentation(model: nn.Module, loader: DataLoader, criterion, device, num_classes: int) -> Tuple[float, float, float]:
    model.eval()
    total_loss = torch.tensor(0.0, device=device)
    total_pixels = torch.tensor(0.0, device=device)
    total_correct = torch.tensor(0.0, device=device)
    intersection = torch.zeros(num_classes, device=device)
    union = torch.zeros(num_classes, device=device)

    for images, masks in loader:
        images = images.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)
        logits = model(images)
        loss = criterion(logits, masks)
        pred = logits.argmax(dim=1)

        bs = images.size(0)
        total_loss += loss * bs
        total_pixels += masks.numel()
        total_correct += (pred == masks).sum()

        for cls in range(num_classes):
            pred_c = pred == cls
            mask_c = masks == cls
            intersection[cls] += (pred_c & mask_c).sum()
            union[cls] += (pred_c | mask_c).sum()

    reduce_tensor(total_loss)
    reduce_tensor(total_pixels)
    reduce_tensor(total_correct)
    reduce_tensor(intersection)
    reduce_tensor(union)

    valid = union > 0
    iou = torch.zeros_like(intersection)
    iou[valid] = intersection[valid] / union[valid].clamp_min(1.0)
    miou = float(iou[valid].mean().item()) if bool(valid.any().item()) else 0.0
    pixel_acc = float((total_correct / total_pixels.clamp_min(1.0)).item())
    avg_loss = float((total_loss / torch.tensor(max(1, len(loader.dataset)), device=device)).item())
    return avg_loss, miou, pixel_acc


def save_checkpoint(path: Path, model: nn.Module, config: dict, metrics_dict: dict, class_names: List[str]) -> None:
    real_model = model.module if isinstance(model, DDP) else model
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": real_model.state_dict(),
            "config": config,
            "metrics": metrics_dict,
            "classes": class_names,
        },
        path,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    seed_everything(int(config.get("seed", 42)))
    device = get_device(config)
    setup_distributed(device)

    try:
        task = str(config.get("trainer_type", "")).lower()
        run_dir = Path(config.get("run_dir") or config.get("checkpoint_dir") or "./checkpoints").resolve()
        run_dir.mkdir(parents=True, exist_ok=True)

        if task == "resnet":
            train_loader, val_loader, num_classes, class_names = build_classification_loaders(config)
            model_name = str(config.get("model_name") or config.get("model_version") or "resnet18")
            model = build_resnet_model(model_name, num_classes)
            criterion = nn.CrossEntropyLoss()
            best_metric_name = "accuracy"
            log("INFO", f"ResNet 分类任务: model={model_name}, num_classes={num_classes}, classes={class_names}")

        elif task == "unet":
            train_loader, val_loader, num_classes, class_names = build_segmentation_loaders(config)
            base_channels = int(config.get("base_channels", 32))
            model = TinyUNet(num_classes=num_classes, base_channels=base_channels)
            criterion = nn.CrossEntropyLoss()
            best_metric_name = "mIoU"
            log("INFO", f"UNet 分割任务: num_classes={num_classes}, base_channels={base_channels}")

        else:
            raise ValueError(f"不支持的 trainer_type: {task}")

        model = model.to(device)
        if is_dist():
            if device.type == "cuda":
                model = DDP(model, device_ids=[device.index], output_device=device.index)
            else:
                model = DDP(model)

        optimizer = build_optimizer(config, model)
        epochs = int(config.get("epochs", 10))
        best_score = -math.inf
        best_path = run_dir / "best.pt"
        last_path = run_dir / "last.pt"
        final_metrics: dict = {}

        log("INFO", f"DDP 初始化完成: rank={get_rank()}, world_size={get_world_size()}, device={device}")
        log("INFO", f"训练集样本数: {len(train_loader.dataset)}, 验证集样本数: {len(val_loader.dataset)}")

        for epoch in range(1, epochs + 1):
            train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device, epoch, task)

            if task == "resnet":
                val_loss, acc = validate_classification(model, val_loader, criterion, device)
                score = acc
                final_metrics = {"train_loss": train_loss, "val_loss": val_loss, "accuracy": acc}
                metric(epoch, "train_loss", train_loss)
                metric(epoch, "val_loss", val_loss)
                metric(epoch, "accuracy", acc)
                log("INFO", f"Epoch {epoch}/{epochs}: train_loss={train_loss:.6f}, val_loss={val_loss:.6f}, accuracy={acc:.6f}")
            else:
                val_loss, miou, pixel_acc = validate_segmentation(model, val_loader, criterion, device, num_classes)
                score = miou
                final_metrics = {"train_loss": train_loss, "val_loss": val_loss, "mIoU": miou, "pixel_acc": pixel_acc}
                metric(epoch, "train_loss", train_loss)
                metric(epoch, "val_loss", val_loss)
                metric(epoch, "mIoU", miou)
                metric(epoch, "pixel_acc", pixel_acc)
                log("INFO", f"Epoch {epoch}/{epochs}: train_loss={train_loss:.6f}, val_loss={val_loss:.6f}, mIoU={miou:.6f}, pixel_acc={pixel_acc:.6f}")

            if is_rank0():
                save_checkpoint(last_path, model, config, final_metrics, class_names)
                if score > best_score:
                    best_score = score
                    save_checkpoint(best_path, model, config, final_metrics, class_names)
                    log("INFO", f"更新最优模型: {best_metric_name}={best_score:.6f}, path={best_path}")

        if is_dist():
            dist.barrier()

        if is_rank0():
            result = {
                "metrics": final_metrics,
                "best_model_path": str(best_path if best_path.exists() else last_path),
                "last_model_path": str(last_path),
                "run_dir": str(run_dir),
                "classes": class_names,
            }
            with open(args.result, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            emit({"type": "result", **result})

    finally:
        cleanup_distributed()


if __name__ == "__main__":
    main()
