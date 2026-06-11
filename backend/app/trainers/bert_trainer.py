import csv
import os
from typing import Callable, List, Sequence, Tuple

import torch
from torch.utils.data import DataLoader, Dataset as TorchDataset

from .base import BaseTrainer


Sample = Tuple[str, int]


def _normalize_metric_name(name: str) -> str:
    return str(name or '').strip().lower().replace(' ', '_').replace('-', '_')


def _load_csv_samples(file_path: str) -> List[Sample]:
    samples: List[Sample] = []
    with open(file_path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f'CSV 文件表头为空: {file_path}')
        fields = {name.strip() for name in reader.fieldnames}
        missing = {'text', 'label'} - fields
        if missing:
            raise ValueError(f'CSV 文件缺少列: {", ".join(sorted(missing))}')

        for row in reader:
            text = (row.get('text') or '').strip()
            if not text:
                continue
            label_raw = (row.get('label') or '').strip()
            try:
                label = int(label_raw)
            except ValueError as exc:
                raise ValueError(f'label 必须是整数，发现: {label_raw}') from exc
            samples.append((text, label))

    if not samples:
        raise ValueError(f'CSV 文件没有有效样本: {file_path}')
    return samples


def _load_textclass_dataset(dataset_path: str) -> Tuple[List[Sample], List[Sample]]:
    """
    兼容两种输入：
    1. 旧逻辑：dataset_path 是单个 CSV 文件；
    2. 新逻辑：dataset_path 是 zip 解压目录，包含 train.csv / val.csv。
    """
    if os.path.isdir(dataset_path):
        train_csv = os.path.join(dataset_path, 'train.csv')
        val_csv = os.path.join(dataset_path, 'val.csv')
        if not os.path.exists(train_csv):
            raise FileNotFoundError(f'文本分类数据集目录缺少 train.csv: {dataset_path}')
        train_samples = _load_csv_samples(train_csv)
        val_samples = _load_csv_samples(val_csv) if os.path.exists(val_csv) else []
        return train_samples, val_samples

    if os.path.isfile(dataset_path):
        train_samples = _load_csv_samples(dataset_path)
        return train_samples, []

    raise FileNotFoundError(f'数据集路径不存在: {dataset_path}')


def _infer_num_classes(samples: Sequence[Sample], configured_num_classes=None) -> int:
    if configured_num_classes:
        return int(configured_num_classes)
    max_label = max(label for _, label in samples)
    return max_label + 1


def _classification_metrics(y_true: Sequence[int], y_pred: Sequence[int], num_classes: int) -> dict:
    total = len(y_true)
    correct = sum(int(a == b) for a, b in zip(y_true, y_pred))
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


class _TextClassificationDataset(TorchDataset):
    """Simple text-classification dataset, samples are (text, label)."""

    def __init__(self, samples: Sequence[Sample], tokenizer, max_length: int = 128):
        self.samples = list(samples)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text, label = self.samples[idx]
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt',
        )
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'labels': torch.tensor(label, dtype=torch.long),
        }


class BERTTrainer(BaseTrainer):
    """BERT text-classification trainer using Hugging Face Transformers + PyTorch."""

    def train(
        self,
        config: dict,
        log_callback: Callable[[str, str], None],
        metric_callback: Callable[[int, str, float, int], None],
    ) -> dict:
        try:
            from transformers import BertTokenizer, BertForSequenceClassification
        except ImportError:
            raise RuntimeError('transformers 未安装，请执行: pip install transformers')

        model_folder = config.get('model_folder', './models')
        model_name = config.get('model_name', 'bert-base-chinese')
        model_path = model_name if os.path.isabs(str(model_name)) else os.path.join(model_folder, model_name)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f'模型目录不存在: {model_path}。'
                f'请先把 HuggingFace 格式的 BERT 模型放到 /app/models/{model_name}'
            )

        dataset_path = config.get('dataset_path')
        if not dataset_path or not os.path.exists(dataset_path):
            raise FileNotFoundError(f'数据集不存在: {dataset_path}')

        epochs = int(config.get('epochs', 3))
        batch_size = int(config.get('batch_size', 16))
        lr = float(config.get('lr', config.get('learning_rate', 2e-5)))
        max_length = int(config.get('max_length', 128))
        checkpoint_dir = config.get('checkpoint_dir', './checkpoints')
        workers = int(config.get('workers', 0) or 0)

        raw_metrics = []
        evaluation = config.get('evaluation') or {}
        if isinstance(evaluation, dict):
            raw_metrics = evaluation.get('metrics') or []
        selected_metrics = {_normalize_metric_name(item) for item in raw_metrics}
        if not selected_metrics:
            selected_metrics = {'loss', 'accuracy'}

        metric_alias = {
            'acc': 'accuracy',
            'train_loss': 'loss',
            'val_loss': 'loss',
        }
        selected_metrics = {metric_alias.get(item, item) for item in selected_metrics}

        supported_metrics = {'loss', 'accuracy', 'precision', 'recall', 'f1'}
        ignored_metrics = sorted(selected_metrics - supported_metrics)
        selected_metrics = selected_metrics & supported_metrics
        if not selected_metrics:
            selected_metrics = {'loss', 'accuracy'}

        train_samples, val_samples = _load_textclass_dataset(dataset_path)
        all_samples = train_samples + val_samples
        num_classes = _infer_num_classes(all_samples, config.get('num_classes'))

        # 如果没有 val.csv，功能测试时退化为用 train 做验证。
        has_real_val = bool(val_samples)
        if not val_samples:
            val_samples = train_samples

        device = torch.device('cuda' if torch.cuda.is_available() and str(config.get('device', 'cuda')).lower() != 'cpu' else 'cpu')
        log_callback('INFO', f'使用设备: {device}')
        log_callback('INFO', f'加载 BERT 模型: {model_path}')
        log_callback('INFO', f'文本分类类别数: {num_classes}')
        if ignored_metrics:
            log_callback('WARNING', f'BERT 文本分类忽略不适用指标: {", ".join(ignored_metrics)}')
        if not has_real_val:
            log_callback('WARNING', '数据集未提供 val.csv，将使用 train.csv 作为功能测试验证集')

        tokenizer = BertTokenizer.from_pretrained(model_path)
        model = BertForSequenceClassification.from_pretrained(model_path, num_labels=num_classes)
        model.to(device)

        train_dataset = _TextClassificationDataset(train_samples, tokenizer, max_length)
        val_dataset = _TextClassificationDataset(val_samples, tokenizer, max_length)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=workers)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=workers)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
        total_steps = len(train_loader) * epochs

        log_callback('INFO', (
            f'开始 BERT 训练: epochs={epochs}, batch_size={batch_size}, '
            f'lr={lr}, max_length={max_length}, train_samples={len(train_dataset)}, '
            f'val_samples={len(val_dataset)}, total_steps={total_steps}'
        ))

        global_step = 0
        final_metrics: dict = {}
        best_score = -1.0
        best_dir = os.path.join(checkpoint_dir, 'bert_best')
        final_dir = os.path.join(checkpoint_dir, 'bert_final')
        os.makedirs(checkpoint_dir, exist_ok=True)

        for epoch in range(1, epochs + 1):
            model.train()
            train_loss_sum = 0.0

            for batch_idx, batch in enumerate(train_loader, start=1):
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)

                optimizer.zero_grad()
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss
                loss.backward()
                optimizer.step()

                train_loss_sum += loss.item()
                global_step += 1

                if batch_idx % max(1, len(train_loader) // 5) == 0:
                    avg_loss = train_loss_sum / batch_idx
                    log_callback('INFO', (
                        f'Epoch {epoch}/{epochs} | '
                        f'Step {batch_idx}/{len(train_loader)} | '
                        f'train_loss={avg_loss:.4f}'
                    ))

            train_loss = train_loss_sum / max(len(train_loader), 1)

            model.eval()
            val_loss_sum = 0.0
            y_true: List[int] = []
            y_pred: List[int] = []

            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch['input_ids'].to(device)
                    attention_mask = batch['attention_mask'].to(device)
                    labels = batch['labels'].to(device)

                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels,
                    )
                    val_loss_sum += outputs.loss.item()
                    preds = outputs.logits.argmax(dim=-1)

                    y_true.extend(labels.detach().cpu().tolist())
                    y_pred.extend(preds.detach().cpu().tolist())

            val_loss = val_loss_sum / max(len(val_loader), 1)
            cls_metrics = _classification_metrics(y_true, y_pred, num_classes)

            epoch_metrics = {
                'train_loss': train_loss,
                'val_loss': val_loss,
                **cls_metrics,
            }

            if 'loss' in selected_metrics:
                metric_callback(epoch, 'train/loss', train_loss, global_step)
                metric_callback(epoch, 'val/loss', val_loss, global_step)
            for key in ('accuracy', 'precision', 'recall', 'f1'):
                if key in selected_metrics:
                    metric_callback(epoch, f'val/{key}', float(epoch_metrics[key]), global_step)

            log_parts = []
            if 'loss' in selected_metrics:
                log_parts.extend([f'train_loss={train_loss:.4f}', f'val_loss={val_loss:.4f}'])
            for key in ('accuracy', 'precision', 'recall', 'f1'):
                if key in selected_metrics:
                    log_parts.append(f'{key}={epoch_metrics[key]:.4f}')
            log_callback('INFO', f'Epoch {epoch}/{epochs} 完成 — ' + ', '.join(log_parts))

            final_metrics = epoch_metrics

            # 保存最优模型：优先 accuracy，其次 -val_loss。
            score = cls_metrics.get('accuracy', 0.0) if 'accuracy' in cls_metrics else -val_loss
            if score >= best_score:
                best_score = score
                model.save_pretrained(best_dir)
                tokenizer.save_pretrained(best_dir)

        model.save_pretrained(final_dir)
        tokenizer.save_pretrained(final_dir)

        log_callback('INFO', f'BERT 训练完成，最佳模型已保存至: {best_dir}')
        log_callback('INFO', f'BERT 最终模型已保存至: {final_dir}')

        return {
            'metrics': final_metrics,
            'best_model_path': best_dir,
        }
