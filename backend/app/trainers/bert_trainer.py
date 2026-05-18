import os
from typing import Callable

import torch
from torch.utils.data import DataLoader, Dataset as TorchDataset

from .base import BaseTrainer


class _CSVTextDataset(TorchDataset):
    """Simple CSV dataset: expects columns 'text' and 'label'."""

    def __init__(self, file_path: str, tokenizer, max_length: int = 128):
        import csv
        self.samples = []
        with open(file_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get('text', '')
                label = int(row.get('label', 0))
                self.samples.append((text, label))
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
        model_path = os.path.join(model_folder, model_name)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f'模型目录不存在: {model_path}')

        dataset_path = config.get('dataset_path')
        if not dataset_path or not os.path.exists(dataset_path):
            raise FileNotFoundError(f'数据集文件不存在: {dataset_path}')

        epochs = int(config.get('epochs', 3))
        batch_size = int(config.get('batch_size', 16))
        lr = float(config.get('lr', 2e-5))
        num_classes = int(config.get('num_classes', 2))
        max_length = int(config.get('max_length', 128))
        checkpoint_dir = config.get('checkpoint_dir', './checkpoints')

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        log_callback('INFO', f'使用设备: {device}')
        log_callback('INFO', f'加载 BERT 模型: {model_path}')

        tokenizer = BertTokenizer.from_pretrained(model_path)
        model = BertForSequenceClassification.from_pretrained(model_path, num_labels=num_classes)
        model.to(device)

        train_dataset = _CSVTextDataset(dataset_path, tokenizer, max_length)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
        total_steps = len(train_loader) * epochs

        log_callback('INFO', (
            f'开始 BERT 训练: epochs={epochs}, batch_size={batch_size}, '
            f'lr={lr}, 样本数={len(train_dataset)}, 总步数={total_steps}'
        ))

        global_step = 0
        final_metrics: dict = {}

        for epoch in range(1, epochs + 1):
            model.train()
            total_loss = 0.0
            correct = 0
            total = 0

            for batch_idx, batch in enumerate(train_loader, start=1):
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)

                optimizer.zero_grad()
                outputs = model(input_ids=input_ids,
                                attention_mask=attention_mask,
                                labels=labels)
                loss = outputs.loss
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                preds = outputs.logits.argmax(dim=-1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
                global_step += 1

                if batch_idx % max(1, len(train_loader) // 5) == 0:
                    avg_loss = total_loss / batch_idx
                    acc = correct / total if total > 0 else 0.0
                    log_callback('INFO', (
                        f'Epoch {epoch}/{epochs} | '
                        f'Step {batch_idx}/{len(train_loader)} | '
                        f'loss={avg_loss:.4f} | acc={acc:.4f}'
                    ))

            epoch_loss = total_loss / max(len(train_loader), 1)
            epoch_acc = correct / max(total, 1)

            metric_callback(epoch, 'train/loss', epoch_loss, global_step)
            metric_callback(epoch, 'train/accuracy', epoch_acc, global_step)
            log_callback('INFO', (
                f'Epoch {epoch}/{epochs} 完成 — '
                f'loss={epoch_loss:.4f}, accuracy={epoch_acc:.4f}'
            ))

            final_metrics = {'train/loss': epoch_loss, 'train/accuracy': epoch_acc}

        # Save final checkpoint
        os.makedirs(checkpoint_dir, exist_ok=True)
        save_path = os.path.join(checkpoint_dir, 'bert_final')
        model.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
        log_callback('INFO', f'BERT 训练完成，模型已保存至: {save_path}')

        return {
            'metrics': final_metrics,
            'best_model_path': save_path,
        }
