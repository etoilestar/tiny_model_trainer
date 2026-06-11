from flask import Blueprint, request, jsonify

from ..extensions import db
from ..models.training_job import Metric
from ..models.project import Project
from ..models.training_job import TrainingJob
from .utils import clean_response

metrics_bp = Blueprint('metrics', __name__)


def ok(data=None, message='成功'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def err(message='操作失败', status=400):
    return jsonify({'code': 1, 'message': message}), status


@metrics_bp.route('/', methods=['GET'])
def get_metrics():
    job_id = request.args.get('job_id', type=int)
    if not job_id:
        return err('缺少 job_id 参数')

    job = db.session.get(TrainingJob, job_id)
    if not job:
        return err('训练任务不存在', 404)

    project = db.session.get(Project, job.project_id)
    if not project:
        return err('项目不存在', 404)

    metric_name = request.args.get('metric_name')
    query = Metric.query.filter_by(job_id=job_id)
    if metric_name:
        query = query.filter_by(metric_name=metric_name)

    metrics = query.order_by(Metric.epoch, Metric.step).all()
    return ok(clean_response([m.to_dict() for m in metrics]))
