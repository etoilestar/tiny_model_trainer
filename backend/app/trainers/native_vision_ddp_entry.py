import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import torch
import torch.distributed as dist
import torch.nn as nn
from PIL import Image
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, Dataset, DistributedSampler
from torchvision import datasets, models, transforms
from torchvision.transforms import functional as TF

from app.trainers.device import Accelerator, resolve_accelerator


CLASSIFICATION_TASKS = {'resnet', 'mobilenet', 'efficientnet'}

SUPPORTED_RESNET = {
    'resnet18': models.resnet18,
    'resnet34': models.resnet34,
    'resnet50': models.resnet50,
    'resnet101': models.resnet101,
    'resnet152': models.resnet152,
}

SUPPORTED_MOBILENET = {
    'mobilenet_v3_small': models.mobilenet_v3_small,
    'mobilenet_v3_large': models.mobilenet_v3_large,
}

SUPPORTED_EFFICIENTNET = {
    'efficientnet_b0': models.efficientnet_b0,
    'efficientnet_b1': models.efficientnet_b1,
    'efficientnet_b2': models.efficientnet_b2,
    'efficientnet_b3': models.efficientnet_b3,
    'efficientnet_b4': models.efficientnet_b4,
    'efficientnet_b5': models.efficientnet_b5,
    'efficientnet_b6': models.efficientnet_b6,
    'efficientnet_b7': models.efficientnet_b7,
    'efficientnet_v2_s': models.efficientnet_v2_s,
    'efficientnet_v2_m': models.efficientnet_v2_m,
    'efficientnet_v2_l': models.efficientnet_v2_l,
}

TORCHVISION_WEIGHT_ENUMS = {
    'resnet18': models.ResNet18_Weights.DEFAULT,
    'resnet34': models.ResNet34_Weights.DEFAULT,
    'resnet50': models.ResNet50_Weights.DEFAULT,
    'resnet101': models.ResNet101_Weights.DEFAULT,
    'resnet152': models.ResNet152_Weights.DEFAULT,

    'mobilenet_v3_small': models.MobileNet_V3_Small_Weights.DEFAULT,
    'mobilenet_v3_large': models.MobileNet_V3_Large_Weights.DEFAULT,

    'efficientnet_b0': models.EfficientNet_B0_Weights.DEFAULT,
    'efficientnet_b1': models.EfficientNet_B1_Weights.DEFAULT,
    'efficientnet_b2': models.EfficientNet_B2_Weights.DEFAULT,
    'efficientnet_b3': models.EfficientNet_B3_Weights.DEFAULT,
    'efficientnet_b4': models.EfficientNet_B4_Weights.DEFAULT,
    'efficientnet_b5': models.EfficientNet_B5_Weights.DEFAULT,
    'efficientnet_b6': models.EfficientNet_B6_Weights.DEFAULT,
    'efficientnet_b7': models.EfficientNet_B7_Weights.DEFAULT,
    'efficientnet_v2_s': models.EfficientNet_V2_S_Weights.DEFAULT,
    'efficientnet_v2_m': models.EfficientNet_V2_M_Weights.DEFAULT,
    'efficientnet_v2_l': models.EfficientNet_V2_L_Weights.DEFAULT,
}


def emit_log(message: str, level: str = 'INFO') -> None:
    print(json.dumps({'type': 'log', 'level': level, 'message': message}, ensure_ascii=False), flush=True)


def emit_metric(epoch: int, name: str, value: float, step: int) -> None:
    print(json.dumps({
        'type': 'metric',
        'epoch': int(epoch),
        'name': str(name),
        'value': float(value),
        'step': int(step),
    }, ensure_ascii=False), flush=True)


def is_main_process() -> bool:
    return not dist.is_available() or not dist.is_initialized() or dist.get_rank() == 0


def setup_distributed(config: dict) -> Tuple[int, int, int, Accelerator]:
    if 'RANK' not in os.environ:
        accelerator = resolve_accelerator(config.get('device', 'auto'), 0)
        return 0, 1, 0, accelerator

    rank = int(os.environ.get('RANK', '0'))
    world_size = int(os.environ.get('WORLD_SIZE', '1'))
    local_rank = int(os.environ.get('LOCAL_RANK', '0'))

    accelerator = resolve_accelerator(config.get('device', 'auto'), local_rank)
    dist.init_process_group(backend=accelerator.distributed_backend, init_method='env://')
    return rank, world_size, local_rank, accelerator


def cleanup_distributed() -> None:
    if dist.is_available() and dist.is_initialized():
        dist.destroy_process_group()


def normalize_model_name(name: str) -> str:
    return str(name or '').strip().lower().replace('-', '_')


def get_model_root(model_folder: str, model_name: str) -> Path:
    # 训练运行在容器内，必须使用容器内路径；默认 /app/models。
    folder = Path(model_folder or '/app/models')
    if not folder.is_absolute():
        folder = Path('/app/models')
    return folder / model_name


def find_local_weight_file(model_folder: str, model_name: str) -> Optional[Path]:
    root = get_model_root(model_folder, model_name)
    candidates = [
        root / 'pytorch_model.bin',
        root / 'model.pth',
        root / 'model.pt',
        root / 'weights.pth',
        root / f'{model_name}.pth',
        root / f'{model_name}.pt',
    ]
    for path in candidates:
        if path.is_file():
            return path

    if root.is_file():
        return root

    return None


def download_torchvision_weight_to_models(model_folder: str, model_name: str) -> Path:
    """
    如果 /app/models/<model_name>/pytorch_model.bin 不存在，则通过 torchvision
    下载官方预训练权重并保存到该路径。

    注意：
    - 这段代码在容器内执行，所以保存路径是 /app/models。
    - 宿主机 ./models 通过 docker-compose 挂载到 /app/models，因此下载结果会落到宿主机 ./models。
    - 无外网环境下下载会失败；失败时请提前手工放入 pytorch_model.bin。
    """
    if model_name not in TORCHVISION_WEIGHT_ENUMS:
        raise ValueError(f'模型 {model_name} 没有配置 torchvision 预训练权重，无法自动下载')

    model_root = get_model_root(model_folder, model_name)
    model_root.mkdir(parents=True, exist_ok=True)

    weight_path = model_root / 'pytorch_model.bin'
    meta_path = model_root / 'meta.json'

    if weight_path.is_file():
        return weight_path

    emit_log(f'本地未找到预训练权重，开始下载: {weight_path}', 'WARNING')

    weights = TORCHVISION_WEIGHT_ENUMS[model_name]
    state_dict = weights.get_state_dict(progress=True)
    torch.save(state_dict, weight_path)

    meta = {
        'model_name': model_name,
        'source': 'torchvision',
        'weights': str(weights),
        'container_path': str(weight_path),
        'host_mapping_note': './models is mounted to /app/models',
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    emit_log(f'预训练权重下载完成并保存到: {weight_path}')
    return weight_path


def ensure_local_pretrained_weight(model_folder: str, model_name: str) -> Path:
    weight_path = find_local_weight_file(model_folder, model_name)
    if weight_path is not None:
        emit_log(f'发现本地预训练权重，直接加载: {weight_path}')
        return weight_path

    return download_torchvision_weight_to_models(model_folder, model_name)


def load_local_pretrained_weights(model: nn.Module, model_folder: str, model_name: str) -> None:
    weight_path = ensure_local_pretrained_weight(model_folder, model_name)

    obj = torch.load(weight_path, map_location='cpu')
    if isinstance(obj, dict):
        if 'state_dict' in obj and isinstance(obj['state_dict'], dict):
            state_dict = obj['state_dict']
        elif 'model' in obj and isinstance(obj['model'], dict):
            state_dict = obj['model']
        else:
            state_dict = obj
    else:
        raise ValueError(f'无法识别的权重文件格式: {weight_path}')

    model_state = model.state_dict()
    filtered = {}
    skipped = []

    for key, value in state_dict.items():
        clean_key = key[len('module.'):] if key.startswith('module.') else key
        if clean_key in model_state and tuple(model_state[clean_key].shape) == tuple(value.shape):
            filtered[clean_key] = value
        else:
            skipped.append(clean_key)

    missing, unexpected = model.load_state_dict(filtered, strict=False)

    emit_log(
        f'已从 /app/models 加载预训练权重: {weight_path} | '
        f'loaded={len(filtered)} skipped={len(skipped)} '
        f'missing={len(missing)} unexpected={len(unexpected)}'
    )


def read_selected_metrics(config: dict, task: str) -> List[str]:
    evaluation = config.get('evaluation') or {}
    raw_metrics = []
    if isinstance(evaluation, dict):
        raw_metrics = evaluation.get('metrics') or []

    normalized = []
    for item in raw_metrics:
        key = str(item).strip().lower().replace(' ', '_').replace('-', '_')
        alias = {
            'acc': 'accuracy',
            'train_loss': 'loss',
            'val_loss': 'loss',
            'pixel_accuracy': 'pixel_acc',
            'pixelacc': 'pixel_acc',
            'miou': 'mIoU',
            'map': 'mAP',
        }.get(key, key)
        normalized.append(alias)

    if task in CLASSIFICATION_TASKS:
        supported = {'loss', 'accuracy', 'precision', 'recall', 'f1'}
        defaults = ['loss', 'accuracy']
    else:
        supported = {'loss', 'mIoU', 'pixel_acc'}
        defaults = ['loss', 'mIoU', 'pixel_acc']

    filtered = []
    ignored = []
    for item in normalized:
        if item in supported:
            filtered.append(item)
        else:
            ignored.append(item)

    if is_main_process() and ignored:
        emit_log(f'当前 {task} 任务忽略不适用的评估指标: {", ".join(sorted(set(ignored)))}', 'WARNING')

    return filtered or defaults


def replace_classifier_head(model: nn.Module, model_name: str, num_classes: int) -> nn.Module:
    if model_name.startswith('resnet'):
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        return model

    if model_name.startswith('mobilenet') or model_name.startswith('efficientnet'):
        if not hasattr(model, 'classifier') or not isinstance(model.classifier, nn.Sequential):
            raise ValueError(f'模型 {model_name} 不包含可识别的 classifier')
        last = model.classifier[-1]
        if not isinstance(last, nn.Linear):
            raise ValueError(f'模型 {model_name} classifier 最后一层不是 Linear')
        model.classifier[-1] = nn.Linear(last.in_features, num_classes)
        return model

    raise ValueError(f'不支持替换分类头的模型: {model_name}')


def build_classification_model(task: str, model_name: str, num_classes: int, pretrained: bool, model_folder: str) -> nn.Module:
    model_name = normalize_model_name(model_name)

    if task == 'resnet':
        builders = SUPPORTED_RESNET
    elif task == 'mobilenet':
        builders = SUPPORTED_MOBILENET
    elif task == 'efficientnet':
        builders = SUPPORTED_EFFICIENTNET
    else:
        raise ValueError(f'不支持的分类任务: {task}')

    if model_name not in builders:
        raise ValueError(
            f'不支持的 {task} 模型: {model_name}。'
            f'支持: {", ".join(sorted(builders.keys()))}'
        )

    # 先创建无权重模型，避免 torchvision 在 build 阶段自动联网。
    model = builders[model_name](weights=None)

    # 替换分类头之前加载预训练权重，这样 head 维度仍与 ImageNet 权重匹配。
    if pretrained:
        load_local_pretrained_weights(model, model_folder, model_name)
    else:
        emit_log('pretrained=false，使用随机初始化')

    model = replace_classifier_head(model, model_name, num_classes)
    return model


def parse_aug_config(config: dict) -> dict:
    data_process = config.get('data_process') or {}
    if not isinstance(data_process, dict):
        return {'enabled': False}
    augmentation = data_process.get('augmentation') or {}
    if data_process.get('method') != 'augment':
        return {'enabled': False}
    if not isinstance(augmentation, dict):
        return {'enabled': False}
    augmentation = dict(augmentation)
    augmentation['enabled'] = True
    return augmentation


def build_classification_transforms(img_size: int, aug: dict):
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]

    train_ops = []
    aug_logs = []

    if aug.get('enabled'):
        use_random_resized_crop = bool(aug.get('randomResizedCrop', False))
        if use_random_resized_crop:
            scale_min = float(aug.get('scaleMin', 0.8))
            scale_max = float(aug.get('scaleMax', 1.0))
            train_ops.append(transforms.RandomResizedCrop(img_size, scale=(scale_min, scale_max)))
            aug_logs.append(f'RandomResizedCrop(scale=({scale_min:.2f},{scale_max:.2f}))')
        else:
            train_ops.append(transforms.Resize((img_size, img_size)))

        hflip_p = float(aug.get('horizontalFlipProb', 0.0) or 0.0)
        if hflip_p > 0:
            train_ops.append(transforms.RandomHorizontalFlip(p=hflip_p))
            aug_logs.append(f'HorizontalFlip(p={hflip_p:.2f})')

        vflip_p = float(aug.get('verticalFlipProb', 0.0) or 0.0)
        if vflip_p > 0:
            train_ops.append(transforms.RandomVerticalFlip(p=vflip_p))
            aug_logs.append(f'VerticalFlip(p={vflip_p:.2f})')

        degrees = float(aug.get('rotationDegrees', 0.0) or 0.0)
        if degrees > 0:
            train_ops.append(transforms.RandomRotation(degrees=degrees))
            aug_logs.append(f'RandomRotation(degrees={degrees:.1f})')

        brightness = float(aug.get('brightness', 0.0) or 0.0)
        contrast = float(aug.get('contrast', 0.0) or 0.0)
        saturation = float(aug.get('saturation', 0.0) or 0.0)
        hue = float(aug.get('hue', 0.0) or 0.0)
        if any(v > 0 for v in [brightness, contrast, saturation, hue]):
            train_ops.append(transforms.ColorJitter(
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
                hue=hue,
            ))
            aug_logs.append(
                f'ColorJitter(brightness={brightness:.2f}, contrast={contrast:.2f}, '
                f'saturation={saturation:.2f}, hue={hue:.2f})'
            )
    else:
        train_ops.append(transforms.Resize((img_size, img_size)))

    train_ops.extend([
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    return transforms.Compose(train_ops), val_transform, aug_logs


class SegmentationDataset(Dataset):
    def __init__(self, root: str, split: str, img_size: int, aug: dict):
        self.root = Path(root)
        self.split = split
        self.img_dir = self.root / 'images' / split
        self.mask_dir = self.root / 'annotations' / split
        self.img_size = img_size
        self.aug = aug if split == 'train' else {'enabled': False}

        if not self.img_dir.is_dir():
            raise FileNotFoundError(f'分割数据集缺少图像目录: {self.img_dir}')
        if not self.mask_dir.is_dir():
            raise FileNotFoundError(f'分割数据集缺少标注目录: {self.mask_dir}')

        allowed = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
        self.images = sorted([p for p in self.img_dir.iterdir() if p.suffix.lower() in allowed])
        if not self.images:
            raise ValueError(f'分割数据集 {self.img_dir} 下没有图片')

    def __len__(self):
        return len(self.images)

    def _mask_path_for(self, image_path: Path) -> Path:
        candidates = [
            self.mask_dir / f'{image_path.stem}.png',
            self.mask_dir / f'{image_path.stem}.jpg',
            self.mask_dir / f'{image_path.stem}.jpeg',
            self.mask_dir / image_path.name,
        ]
        for p in candidates:
            if p.exists():
                return p
        raise FileNotFoundError(f'找不到图像对应 mask: {image_path.name}')

    def __getitem__(self, idx):
        img_path = self.images[idx]
        mask_path = self._mask_path_for(img_path)

        image = Image.open(img_path).convert('RGB')
        mask = Image.open(mask_path).convert('L')

        image = TF.resize(image, [self.img_size, self.img_size], interpolation=TF.InterpolationMode.BILINEAR)
        mask = TF.resize(mask, [self.img_size, self.img_size], interpolation=TF.InterpolationMode.NEAREST)

        if self.aug.get('enabled'):
            hflip_p = float(self.aug.get('horizontalFlipProb', 0.0) or 0.0)
            if hflip_p > 0 and random.random() < hflip_p:
                image = TF.hflip(image)
                mask = TF.hflip(mask)

            vflip_p = float(self.aug.get('verticalFlipProb', 0.0) or 0.0)
            if vflip_p > 0 and random.random() < vflip_p:
                image = TF.vflip(image)
                mask = TF.vflip(mask)

            degrees = float(self.aug.get('rotationDegrees', 0.0) or 0.0)
            if degrees > 0:
                angle = random.uniform(-degrees, degrees)
                image = TF.rotate(image, angle, interpolation=TF.InterpolationMode.BILINEAR)
                mask = TF.rotate(mask, angle, interpolation=TF.InterpolationMode.NEAREST)

            brightness = float(self.aug.get('brightness', 0.0) or 0.0)
            contrast = float(self.aug.get('contrast', 0.0) or 0.0)
            saturation = float(self.aug.get('saturation', 0.0) or 0.0)
            hue = float(self.aug.get('hue', 0.0) or 0.0)
            if any(v > 0 for v in [brightness, contrast, saturation, hue]):
                jitter = transforms.ColorJitter(
                    brightness=brightness,
                    contrast=contrast,
                    saturation=saturation,
                    hue=hue,
                )
                image = jitter(image)

        image = TF.to_tensor(image)
        image = TF.normalize(image, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        mask_tensor = torch.as_tensor(torch.ByteTensor(torch.ByteStorage.from_buffer(mask.tobytes())), dtype=torch.long)
        mask_tensor = mask_tensor.view(mask.size[1], mask.size[0])

        return image, mask_tensor


class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class TinyUNet(nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()
        self.down1 = DoubleConv(3, 32)
        self.pool1 = nn.MaxPool2d(2)
        self.down2 = DoubleConv(32, 64)
        self.pool2 = nn.MaxPool2d(2)
        self.bridge = DoubleConv(64, 128)
        self.up2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.conv2 = DoubleConv(128, 64)
        self.up1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.conv1 = DoubleConv(64, 32)
        self.head = nn.Conv2d(32, num_classes, 1)

    def forward(self, x):
        d1 = self.down1(x)
        d2 = self.down2(self.pool1(d1))
        b = self.bridge(self.pool2(d2))
        u2 = self.up2(b)
        u2 = torch.cat([u2, d2], dim=1)
        u2 = self.conv2(u2)
        u1 = self.up1(u2)
        u1 = torch.cat([u1, d1], dim=1)
        u1 = self.conv1(u1)
        return self.head(u1)


def classification_metrics(y_true: Sequence[int], y_pred: Sequence[int], num_classes: int) -> Dict[str, float]:
    total = len(y_true)
    correct = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    accuracy = correct / total if total else 0.0

    precisions = []
    recalls = []
    f1s = []
    for cls in range(num_classes):
        tp = sum(1 for a, b in zip(y_true, y_pred) if a == cls and b == cls)
        fp = sum(1 for a, b in zip(y_true, y_pred) if a != cls and b == cls)
        fn = sum(1 for a, b in zip(y_true, y_pred) if a == cls and b != cls)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    return {
        'accuracy': accuracy,
        'precision': sum(precisions) / max(len(precisions), 1),
        'recall': sum(recalls) / max(len(recalls), 1),
        'f1': sum(f1s) / max(len(f1s), 1),
    }


def segmentation_metrics(logits: torch.Tensor, masks: torch.Tensor, num_classes: int) -> Tuple[float, float]:
    preds = logits.argmax(dim=1)

    pixel_acc = (preds == masks).float().mean().item()

    ious = []
    for cls in range(num_classes):
        pred_cls = preds == cls
        mask_cls = masks == cls
        inter = (pred_cls & mask_cls).sum().item()
        union = (pred_cls | mask_cls).sum().item()
        if union > 0:
            ious.append(inter / union)

    miou = sum(ious) / len(ious) if ious else 0.0
    return miou, pixel_acc


def reduce_sum(value: float, device: torch.device) -> float:
    t = torch.tensor(float(value), device=device)
    if dist.is_available() and dist.is_initialized():
        dist.all_reduce(t, op=dist.ReduceOp.SUM)
    return float(t.item())


def save_checkpoint(path: Path, model: nn.Module, metrics: dict, config: dict) -> None:
    raw_model = model.module if isinstance(model, DDP) else model
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'state_dict': raw_model.state_dict(),
        'metrics': metrics,
        'config': config,
    }, path)


def train_classification(config: dict, device: torch.device, world_size: int, local_rank: int) -> dict:
    task = str(config.get('trainer_type')).lower()
    model_name = normalize_model_name(config.get('model_name') or config.get('model_version') or task)
    model_folder = config.get('model_folder') or '/app/models'
    pretrained = bool(config.get('pretrained', True))

    dataset_path = config.get('dataset_path')
    if not dataset_path or not Path(dataset_path).exists():
        raise FileNotFoundError(f'分类数据集不存在: {dataset_path}')

    img_size = int(config.get('img_size', 224) or 224)
    batch_size = int(config.get('batch_size', 16) or 16)
    epochs = int(config.get('epochs', 1) or 1)
    lr = float(config.get('lr', config.get('learning_rate', 1e-3)) or 1e-3)
    workers = int(config.get('workers', 0) or 0)
    weight_decay = float(config.get('weight_decay', 0.0) or 0.0)
    optimizer_name = str(config.get('optimizer', 'adamw') or 'adamw').lower()
    run_dir = Path(config.get('run_dir', './native_run'))

    aug = parse_aug_config(config)
    train_tf, val_tf, aug_logs = build_classification_transforms(img_size, aug)

    train_root = Path(dataset_path) / 'train'
    val_root = Path(dataset_path) / 'val'
    if not val_root.is_dir():
        val_root = train_root
        if is_main_process():
            emit_log('分类数据集未提供 val/，将使用 train/ 作为功能测试验证集', 'WARNING')

    train_dataset = datasets.ImageFolder(str(train_root), transform=train_tf)
    val_dataset = datasets.ImageFolder(str(val_root), transform=val_tf)
    num_classes = int(config.get('num_classes') or len(train_dataset.classes))

    if is_main_process():
        emit_log(f'分类任务: task={task}, model={model_name}, num_classes={num_classes}')
        emit_log(f'容器内模型目录: {model_folder}')
        emit_log(f'模型权重目标路径: {get_model_root(model_folder, model_name) / "pytorch_model.bin"}')
        if pretrained:
            emit_log('预训练权重策略: 先查 /app/models，缺失则下载到 /app/models 后加载')
        else:
            emit_log('pretrained=false，使用随机初始化')
        if aug_logs:
            emit_log('启用数据增强: ' + ', '.join(aug_logs))
        else:
            emit_log('未启用数据增强，仅使用 Resize + Normalize')

    model = build_classification_model(task, model_name, num_classes, pretrained, model_folder)
    model.to(device)

    if dist.is_available() and dist.is_initialized():
        if device.type in {'cuda', 'npu'}:
            model = DDP(model, device_ids=[local_rank])
        else:
            model = DDP(model)

    train_sampler = DistributedSampler(train_dataset, shuffle=True) if dist.is_available() and dist.is_initialized() else None
    val_sampler = DistributedSampler(val_dataset, shuffle=False) if dist.is_available() and dist.is_initialized() else None

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=train_sampler is None,
        sampler=train_sampler,
        num_workers=workers,
        pin_memory=device.type == 'cuda',
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        sampler=val_sampler,
        num_workers=workers,
        pin_memory=device.type == 'cuda',
    )

    criterion = nn.CrossEntropyLoss()

    if optimizer_name == 'sgd':
        optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=float(config.get('momentum', 0.9) or 0.9), weight_decay=weight_decay)
    elif optimizer_name == 'adam':
        optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    selected_metrics = read_selected_metrics(config, task)

    best_score = -1.0
    best_path = run_dir / 'best.pt'
    final_path = run_dir / 'final.pt'
    global_step = 0
    final_metrics = {}

    for epoch in range(1, epochs + 1):
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)

        model.train()
        train_loss_sum = 0.0
        train_count = 0

        for images, labels in train_loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            bs = labels.size(0)
            train_loss_sum += loss.item() * bs
            train_count += bs
            global_step += 1

        train_loss_sum = reduce_sum(train_loss_sum, device)
        train_count = reduce_sum(train_count, device)
        train_loss = train_loss_sum / max(train_count, 1.0)

        model.eval()
        val_loss_sum = 0.0
        val_count = 0
        y_true = []
        y_pred = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)

                logits = model(images)
                loss = criterion(logits, labels)
                preds = logits.argmax(dim=1)

                bs = labels.size(0)
                val_loss_sum += loss.item() * bs
                val_count += bs

                y_true.extend(labels.detach().cpu().tolist())
                y_pred.extend(preds.detach().cpu().tolist())

        val_loss_sum = reduce_sum(val_loss_sum, device)
        val_count = reduce_sum(val_count, device)
        val_loss = val_loss_sum / max(val_count, 1.0)

        cls_metrics = classification_metrics(y_true, y_pred, num_classes)
        final_metrics = {
            'train_loss': train_loss,
            'val_loss': val_loss,
            **cls_metrics,
        }

        if is_main_process():
            if 'loss' in selected_metrics:
                emit_metric(epoch, 'train/loss', train_loss, global_step)
                emit_metric(epoch, 'val/loss', val_loss, global_step)
            for key in ('accuracy', 'precision', 'recall', 'f1'):
                if key in selected_metrics:
                    emit_metric(epoch, f'val/{key}', final_metrics[key], global_step)

            log_parts = []
            if 'loss' in selected_metrics:
                log_parts.extend([f'train_loss={train_loss:.6f}', f'val_loss={val_loss:.6f}'])
            for key in ('accuracy', 'precision', 'recall', 'f1'):
                if key in selected_metrics:
                    log_parts.append(f'{key}={final_metrics[key]:.6f}')
            emit_log(f'Epoch {epoch}/{epochs} 完成 — ' + ', '.join(log_parts))

            score = float(cls_metrics.get('accuracy', 0.0))
            if score >= best_score:
                best_score = score
                save_checkpoint(best_path, model, final_metrics, config)
                emit_log(f'保存最佳模型: {best_path}')

    if is_main_process():
        save_checkpoint(final_path, model, final_metrics, config)
        emit_log(f'保存最终模型: {final_path}')

    return {
        'metrics': final_metrics,
        'best_model_path': str(best_path),
        'final_model_path': str(final_path),
    }


def train_unet(config: dict, device: torch.device, world_size: int, local_rank: int) -> dict:
    dataset_path = config.get('dataset_path')
    if not dataset_path or not Path(dataset_path).exists():
        raise FileNotFoundError(f'分割数据集不存在: {dataset_path}')

    img_size = int(config.get('img_size', 256) or 256)
    batch_size = int(config.get('batch_size', 4) or 4)
    epochs = int(config.get('epochs', 1) or 1)
    lr = float(config.get('lr', config.get('learning_rate', 1e-3)) or 1e-3)
    workers = int(config.get('workers', 0) or 0)
    num_classes = int(config.get('num_classes', 2) or 2)
    run_dir = Path(config.get('run_dir', './native_run'))

    aug = parse_aug_config(config)

    train_dataset = SegmentationDataset(dataset_path, 'train', img_size, aug)
    val_dataset = SegmentationDataset(dataset_path, 'val', img_size, {'enabled': False})

    model = TinyUNet(num_classes=num_classes).to(device)

    if dist.is_available() and dist.is_initialized():
        if device.type in {'cuda', 'npu'}:
            model = DDP(model, device_ids=[local_rank])
        else:
            model = DDP(model)

    train_sampler = DistributedSampler(train_dataset, shuffle=True) if dist.is_available() and dist.is_initialized() else None
    val_sampler = DistributedSampler(val_dataset, shuffle=False) if dist.is_available() and dist.is_initialized() else None

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=train_sampler is None,
        sampler=train_sampler,
        num_workers=workers,
        pin_memory=device.type == 'cuda',
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        sampler=val_sampler,
        num_workers=workers,
        pin_memory=device.type == 'cuda',
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    selected_metrics = read_selected_metrics(config, 'unet')

    best_score = -1.0
    best_path = run_dir / 'best.pt'
    final_path = run_dir / 'final.pt'
    global_step = 0
    final_metrics = {}

    if is_main_process():
        emit_log(f'UNet 分割任务: num_classes={num_classes}, img_size={img_size}')

    for epoch in range(1, epochs + 1):
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)

        model.train()
        train_loss_sum = 0.0
        train_count = 0

        for images, masks in train_loader:
            images = images.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, masks)
            loss.backward()
            optimizer.step()

            bs = images.size(0)
            train_loss_sum += loss.item() * bs
            train_count += bs
            global_step += 1

        train_loss_sum = reduce_sum(train_loss_sum, device)
        train_count = reduce_sum(train_count, device)
        train_loss = train_loss_sum / max(train_count, 1.0)

        model.eval()
        val_loss_sum = 0.0
        val_count = 0
        miou_sum = 0.0
        pix_sum = 0.0
        batches = 0

        with torch.no_grad():
            for images, masks in val_loader:
                images = images.to(device, non_blocking=True)
                masks = masks.to(device, non_blocking=True)
                logits = model(images)
                loss = criterion(logits, masks)

                miou, pix = segmentation_metrics(logits, masks, num_classes)

                bs = images.size(0)
                val_loss_sum += loss.item() * bs
                val_count += bs
                miou_sum += miou
                pix_sum += pix
                batches += 1

        val_loss_sum = reduce_sum(val_loss_sum, device)
        val_count = reduce_sum(val_count, device)
        miou_sum = reduce_sum(miou_sum, device)
        pix_sum = reduce_sum(pix_sum, device)
        batches = reduce_sum(batches, device)

        val_loss = val_loss_sum / max(val_count, 1.0)
        miou = miou_sum / max(batches, 1.0)
        pixel_acc = pix_sum / max(batches, 1.0)

        final_metrics = {
            'train_loss': train_loss,
            'val_loss': val_loss,
            'mIoU': miou,
            'pixel_acc': pixel_acc,
        }

        if is_main_process():
            if 'loss' in selected_metrics:
                emit_metric(epoch, 'train/loss', train_loss, global_step)
                emit_metric(epoch, 'val/loss', val_loss, global_step)
            if 'mIoU' in selected_metrics:
                emit_metric(epoch, 'val/mIoU', miou, global_step)
            if 'pixel_acc' in selected_metrics:
                emit_metric(epoch, 'val/pixel_acc', pixel_acc, global_step)

            log_parts = []
            if 'loss' in selected_metrics:
                log_parts.extend([f'train_loss={train_loss:.6f}', f'val_loss={val_loss:.6f}'])
            if 'mIoU' in selected_metrics:
                log_parts.append(f'mIoU={miou:.6f}')
            if 'pixel_acc' in selected_metrics:
                log_parts.append(f'pixel_acc={pixel_acc:.6f}')
            emit_log(f'Epoch {epoch}/{epochs} 完成 — ' + ', '.join(log_parts))

            if miou >= best_score:
                best_score = miou
                save_checkpoint(best_path, model, final_metrics, config)
                emit_log(f'保存最佳模型: {best_path}')

    if is_main_process():
        save_checkpoint(final_path, model, final_metrics, config)
        emit_log(f'保存最终模型: {final_path}')

    return {
        'metrics': final_metrics,
        'best_model_path': str(best_path),
        'final_model_path': str(final_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--result', required=True)
    args = parser.parse_args()

    with open(args.config, encoding='utf-8') as f:
        config = json.load(f)

    rank, world_size, local_rank, accelerator = setup_distributed(config)

    try:
        device = accelerator.device

        if is_main_process():
            emit_log(f'DDP 初始化完成: rank={rank}, world_size={world_size}, local_rank={local_rank}, device={device}')

        task = str(config.get('trainer_type', '')).lower()

        if task in CLASSIFICATION_TASKS:
            result = train_classification(config, device, world_size, local_rank)
        elif task == 'unet':
            result = train_unet(config, device, world_size, local_rank)
        else:
            raise ValueError(f'不支持的原生视觉训练类型: {task}')

        if is_main_process():
            result_path = Path(args.result)
            result_path.parent.mkdir(parents=True, exist_ok=True)
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

    finally:
        cleanup_distributed()


if __name__ == '__main__':
    main()
