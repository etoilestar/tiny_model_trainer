import json
import traceback
from datetime import datetime, timezone

from ..extensions import celery, db
from ..models.training_job import TrainingJob, TrainingLog, Metric
from ..models.model_registry import ModelRegistry


def _write_log(job_id: int, level: str, message: str) -> None:
    """Persist a log entry immediately. Called from within the Celery task."""
    log = TrainingLog(job_id=job_id, level=level.upper(), message=message)
    db.session.add(log)
    db.session.commit()


def _write_metric(job_id: int, epoch: int, metric_name: str, value: float, step: int) -> None:
    metric = Metric(
        job_id=job_id,
        epoch=epoch,
        metric_name=metric_name,
        metric_value=value,
        step=step,
    )
    db.session.add(metric)
    db.session.commit()


@celery.task(bind=True, name='tasks.run_training_job', max_retries=0)
def run_training_job(self, job_id: int) -> dict:
    """Celery task: execute a training job end-to-end."""
    job = db.session.get(TrainingJob, job_id)
    if not job:
        return {'error': f'训练任务 {job_id} 不存在'}

    job.status = 'running'
    job.started_at = datetime.now(timezone.utc)
    db.session.commit()

    _write_log(job_id, 'INFO', f'训练任务 [{job.name}] 开始执行')

    config: dict = {}
    try:
        config = json.loads(job.config_json or '{}')
    except json.JSONDecodeError:
        _write_log(job_id, 'ERROR', '配置解析失败，config_json 格式无效')
        job.status = 'failed'
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        return {'error': '配置解析失败'}

    trainer_type = config.get('trainer_type', '').lower()

    try:
        _write_log(job_id, 'INFO', f'训练器类型: {trainer_type}')

        if trainer_type == 'yolo':
            from ..trainers.yolo_trainer import YOLOTrainer
            trainer = YOLOTrainer()
        elif trainer_type == 'bert':
            from ..trainers.bert_trainer import BERTTrainer
            trainer = BERTTrainer()
        elif trainer_type in ('resnet', 'mobilenet', 'efficientnet', 'unet'):
            # NativeVisionTrainer launches torchrun as a subprocess. This keeps
            # Celery alive even if a low-level CUDA/C++ extension crashes.
            from ..trainers.native_vision_trainer import NativeVisionTrainer
            trainer = NativeVisionTrainer()
        else:
            raise ValueError(f'不支持的训练器类型: {trainer_type}')

        def log_cb(level: str, message: str) -> None:
            _write_log(job_id, level, message)

        def metric_cb(epoch: int, metric_name: str, value: float, step: int) -> None:
            _write_metric(job_id, epoch, metric_name, value, step)

        result = trainer.train(config, log_cb, metric_cb)

        best_model_path = result.get('best_model_path')
        if best_model_path:
            registry_entry = ModelRegistry(
                project_id=job.project_id,
                job_id=job.id,
                name=f'{job.name}-output',
                version='v1.0',
                framework='pytorch',
                file_path=str(best_model_path),
                metrics_json=json.dumps(result.get('metrics', {}), ensure_ascii=False),
            )
            db.session.add(registry_entry)

        job.status = 'completed'
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()

        _write_log(job_id, 'INFO', f'训练任务 [{job.name}] 执行完成')
        return {'status': 'completed', 'result': result}

    except Exception as exc:
        error_detail = traceback.format_exc()
        _write_log(job_id, 'ERROR', f'训练过程发生异常: {exc}')
        _write_log(job_id, 'ERROR', f'详细错误:\n{error_detail}')

        db.session.expire(job)
        job = db.session.get(TrainingJob, job_id)
        if job and job.status not in ('stopped',):
            job.status = 'failed'
            job.finished_at = datetime.now(timezone.utc)
            db.session.commit()

        return {'status': 'failed', 'error': str(exc)}
