from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.workflow import Workflow
from ..models.project import Project
from .utils import sanitize_str, clean_response

workflows_bp = Blueprint('workflows', __name__)


def ok(data=None, message='成功'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def err(message='操作失败', status=400):
    return jsonify({'code': 1, 'message': message}), status


def _require_project(project_id: int, user_id: int) -> Project:
    project = db.session.get(Project, project_id)
    if not project:
        abort(404, '项目不存在')
    if project.user_id != user_id:
        abort(403, '无权访问该项目')
    return project


def _require_workflow(workflow_id: int, user_id: int) -> Workflow:
    workflow = db.session.get(Workflow, workflow_id)
    if not workflow:
        abort(404, '工作流不存在')
    _require_project(workflow.project_id, user_id)
    return workflow


@workflows_bp.route('/', methods=['GET'])
@jwt_required()
def list_workflows():
    user_id = int(get_jwt_identity())
    project_id = request.args.get('project_id', type=int)
    if not project_id:
        return err('缺少 project_id 参数')

    _require_project(project_id, user_id)
    workflows = Workflow.query.filter_by(project_id=project_id).order_by(Workflow.updated_at.desc()).all()
    return ok(clean_response([w.to_dict() for w in workflows]))


@workflows_bp.route('/', methods=['POST'])
@jwt_required()
def create_workflow():
    user_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}

    project_id = body.get('project_id')
    name = sanitize_str((body.get('name') or '').strip())
    canvas_json = body.get('canvas_json', '{}')

    if not project_id:
        return err('缺少 project_id 参数')
    if not name:
        return err('工作流名称不能为空')

    _require_project(int(project_id), user_id)
    workflow = Workflow(
        project_id=int(project_id),
        name=name,
        canvas_json=canvas_json if isinstance(canvas_json, str) else str(canvas_json),
    )
    db.session.add(workflow)
    db.session.commit()
    return ok(clean_response(workflow.to_dict()), '工作流创建成功'), 201


@workflows_bp.route('/<int:workflow_id>', methods=['GET'])
@jwt_required()
def get_workflow(workflow_id):
    user_id = int(get_jwt_identity())
    workflow = _require_workflow(workflow_id, user_id)
    return ok(clean_response(workflow.to_dict()))


@workflows_bp.route('/<int:workflow_id>', methods=['PUT'])
@jwt_required()
def update_workflow(workflow_id):
    user_id = int(get_jwt_identity())
    workflow = _require_workflow(workflow_id, user_id)

    body = request.get_json(silent=True) or {}
    name = sanitize_str((body.get('name') or '').strip())
    if name:
        workflow.name = name
    if 'canvas_json' in body:
        raw = body['canvas_json']
        workflow.canvas_json = raw if isinstance(raw, str) else str(raw)
    workflow.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return ok(clean_response(workflow.to_dict()), '工作流已保存')


@workflows_bp.route('/<int:workflow_id>', methods=['DELETE'])
@jwt_required()
def delete_workflow(workflow_id):
    user_id = int(get_jwt_identity())
    workflow = _require_workflow(workflow_id, user_id)
    db.session.delete(workflow)
    db.session.commit()
    return ok(None, '工作流已删除')
