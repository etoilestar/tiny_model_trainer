import json
import time
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, Response, current_app, abort, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.training_job import TrainingJob, TrainingLog
from ..models.project import Project
from ..models.dataset import Dataset
from .utils import sanitize_str, clean_response

training_bp = Blueprint('training', __name__)


def ok(data=None, message='成功'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def err(message='操作失败', status=400):
    return jsonify({'code': 1, 'message': message}), status


def _require_job(job_id: int, user_id: int) -> TrainingJob:
    job = db.session.get(TrainingJob, job_id)
    if not job:
        abort(404, '训练任务不存在')
    project = db.session.get(Project, job.project_id)
    if not project or project.user_id != user_id:
        abort(403, '无权访问该训练任务')
    return job


# ── Job CRUD ────────────────────────────────────────────────────────────────

@training_bp.route('/jobs', methods=['POST'])
@jwt_required()
def create_job():
    user_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    project_id = body.get('project_id')
    workflow_id = body.get('workflow_id')
    name = sanitize_str((body.get('name') or '').strip())
    config = body.get('config', {})

    if not project_id:
        return err('缺少 project_id 参数')
    if not name:
        return err('任务名称不能为空')

    project = db.session.get(Project, int(project_id))
    if not project:
        return err('项目不存在', 404)
    if project.user_id != user_id:
        return err('无权访问该项目', 403)

    # Validate trainer_type
    trainer_type = config.get('trainer_type', '')
    if trainer_type not in ('yolo', 'bert', 'resnet', 'unet'):
        return err('不支持的训练器类型，支持: yolo, bert, resnet, unet')

    # Validate dataset
    dataset_id = config.get('dataset_id')
    if dataset_id:
        dataset = db.session.get(Dataset, int(dataset_id))
        if not dataset or dataset.project_id != int(project_id):
            return err('数据集不存在或不属于该项目', 404)
        config['dataset_path'] = dataset.file_path

    # Inject server-side paths into config
    config['model_folder'] = current_app.config['MODEL_FOLDER']
    config['checkpoint_dir'] = current_app.config['CHECKPOINT_FOLDER']

    job = TrainingJob(
        project_id=int(project_id),
        workflow_id=int(workflow_id) if workflow_id else None,
        name=name,
        status='pending',
        config_json=json.dumps(config, ensure_ascii=False),
    )
    db.session.add(job)
    db.session.commit()

    # Dispatch Celery task
    from ..tasks.training_task import run_training_job
    task = run_training_job.delay(job.id)
    job.celery_task_id = task.id
    db.session.commit()

    return ok(clean_response(job.to_dict()), '训练任务已创建并开始'), 201


@training_bp.route('/jobs', methods=['GET'])
@jwt_required()
def list_jobs():
    user_id = int(get_jwt_identity())
    project_id = request.args.get('project_id', type=int)
    if not project_id:
        return err('缺少 project_id 参数')

    project = db.session.get(Project, project_id)
    if not project or project.user_id != user_id:
        return err('无权访问该项目', 403)

    jobs = (TrainingJob.query
            .filter_by(project_id=project_id)
            .order_by(TrainingJob.created_at.desc())
            .all())
    return ok(clean_response([j.to_dict() for j in jobs]))


@training_bp.route('/jobs/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    user_id = int(get_jwt_identity())
    job = _require_job(job_id, user_id)
    return ok(clean_response(job.to_dict()))


@training_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    user_id = int(get_jwt_identity())
    job = _require_job(job_id, user_id)

    if job.status == 'running':
        return err('运行中的任务无法删除，请先停止')

    db.session.delete(job)
    db.session.commit()
    return ok(None, '训练任务已删除')


@training_bp.route('/jobs/<int:job_id>/stop', methods=['POST'])
@jwt_required()
def stop_job(job_id):
    user_id = int(get_jwt_identity())
    job = _require_job(job_id, user_id)

    if job.status not in ('pending', 'running'):
        return err('该任务当前状态无法停止')

    # Revoke Celery task
    if job.celery_task_id:
        from ..extensions import celery
        celery.control.revoke(job.celery_task_id, terminate=True, signal='SIGTERM')

    job.status = 'stopped'
    job.finished_at = datetime.now(timezone.utc)
    db.session.commit()
    return ok(None, '训练任务已停止')


# ── Logs ────────────────────────────────────────────────────────────────────

@training_bp.route('/jobs/<int:job_id>/logs', methods=['GET'])
@jwt_required()
def get_logs(job_id):
    user_id = int(get_jwt_identity())
    _require_job(job_id, user_id)

    logs = (TrainingLog.query
            .filter_by(job_id=job_id)
            .order_by(TrainingLog.id)
            .all())
    return ok(clean_response([log.to_dict() for log in logs]))

@training_bp.route('/jobs/<int:job_id>/stream')
@training_bp.route('/jobs/<int:job_id>/logs/stream')
@jwt_required()
def stream_logs(job_id):
    """SSE endpoint – streams training logs in real time."""
    user_id = int(get_jwt_identity())
    _require_job(job_id, user_id)

    @stream_with_context
    def generate():
        last_id = 0

        # 关键：立刻输出一条消息，避免浏览器一直等、页面看起来卡住
        yield 'retry: 3000\n\n'
        yield f'data: {json.dumps({"event": "connected", "job_id": job_id}, ensure_ascii=False)}\n\n'

        try:
            while True:
                # 每轮使用新 session 状态，避免读不到 Celery worker 写入的新日志
                db.session.expire_all()

                logs = (
                    TrainingLog.query
                    .filter(
                        TrainingLog.job_id == job_id,
                        TrainingLog.id > last_id
                    )
                    .order_by(TrainingLog.id)
                    .all()
                )

                has_output = False

                for log in logs:
                    payload = json.dumps({
                        'id': log.id,
                        'time': log.timestamp.isoformat() if log.timestamp else '',
                        'level': log.level,
                        'message': log.message,
                    }, ensure_ascii=False)

                    yield f'data: {payload}\n\n'
                    last_id = log.id
                    has_output = True

                current_job = db.session.get(TrainingJob, job_id)
                status = current_job.status if current_job else 'unknown'

                if status in ('completed', 'failed', 'stopped'):
                    payload = json.dumps({
                        'event': 'done',
                        'status': status
                    }, ensure_ascii=False)

                    yield f'data: {payload}\n\n'
                    break

                # 关键：没有新日志时也发心跳，防止前端/反代认为连接没数据
                if not has_output:
                    heartbeat = json.dumps({
                        'event': 'heartbeat',
                        'job_id': job_id,
                        'status': status,
                        'last_id': last_id,
                    }, ensure_ascii=False)
                    yield f'data: {heartbeat}\n\n'

                time.sleep(2)

        finally:
            db.session.remove()

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'X-Accel-Buffering': 'no',
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
        },
    )
