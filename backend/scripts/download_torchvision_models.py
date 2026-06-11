#!/usr/bin/env python3
"""
Download torchvision pretrained weights into /app/models by default.

This script is intended to run inside the container:

  docker compose exec -T worker python backend/scripts/download_torchvision_models.py --model efficientnet_b0

Because docker-compose maps host ./models to container /app/models:

  host:      ./models/efficientnet_b0/pytorch_model.bin
  container: /app/models/efficientnet_b0/pytorch_model.bin

If the target file already exists, the script skips downloading.
"""

import argparse
import json
from pathlib import Path

import torch
from torchvision import models


WEIGHT_ENUMS = {
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


def download_one(model_name: str, output_root: Path, force: bool = False) -> None:
    if model_name not in WEIGHT_ENUMS:
        raise ValueError(f'不支持的模型: {model_name}. 支持: {", ".join(sorted(WEIGHT_ENUMS))}')

    out_dir = output_root / model_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'pytorch_model.bin'
    meta_file = out_dir / 'meta.json'

    if out_file.is_file() and not force:
        print(f'[skip] found existing weight: {out_file}')
        return

    weights = WEIGHT_ENUMS[model_name]
    print(f'[download] {model_name} -> {out_file}')
    state_dict = weights.get_state_dict(progress=True)
    torch.save(state_dict, out_file)

    meta = {
        'model_name': model_name,
        'source': 'torchvision',
        'weights': str(weights),
        'container_path': str(out_file),
        'host_mapping_note': './models is mounted to /app/models',
    }
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[ok] saved {model_name}: {out_file}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', action='append', default=[], help='model name, e.g. efficientnet_b0')
    parser.add_argument('--all', action='store_true', help='download all supported torchvision weights')
    parser.add_argument('--all-efficientnet', action='store_true', help='download all EfficientNet weights')
    parser.add_argument('--output-root', default='/app/models', help='default: /app/models')
    parser.add_argument('--force', action='store_true', help='re-download even if pytorch_model.bin already exists')
    args = parser.parse_args()

    output_root = Path(args.output_root)

    models_to_download = list(args.model)
    if args.all:
        models_to_download.extend(sorted(WEIGHT_ENUMS))
    if args.all_efficientnet:
        models_to_download.extend([name for name in sorted(WEIGHT_ENUMS) if name.startswith('efficientnet')])

    models_to_download = sorted(set(models_to_download))
    if not models_to_download:
        raise SystemExit('请指定 --model，或使用 --all / --all-efficientnet')

    for model_name in models_to_download:
        download_one(model_name, output_root, force=args.force)


if __name__ == '__main__':
    main()
