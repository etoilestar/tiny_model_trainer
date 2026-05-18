from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.project import Project
from .utils import sanitize_str, clean_response

projects_bp = Blueprint('projects', __name__)


def ok(data=None, message='成功'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def err(message='操作失败', status=400):
    return jsonify({'code': 1, 'message': message}), status


def _require_project(project_id: int, user_id: int) -> Project:
    """Return the project or abort with the appropriate HTTP error."""
    project = db.session.get(Project, project_id)
    if not project:
        abort(404, '项目不存在')
    if project.user_id != user_id:
        abort(403, '无权访问该项目')
    return project


@projects_bp.route('/', methods=['GET'])
@jwt_required()
def list_projects():
    user_id = int(get_jwt_identity())
    projects = Project.query.filter_by(user_id=user_id).order_by(Project.created_at.desc()).all()
    return ok(clean_response([p.to_dict() for p in projects]))


@projects_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    user_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}
    name = sanitize_str((body.get('name') or '').strip())
    if not name:
        return err('项目名称不能为空')

    project = Project(
        name=name,
        description=sanitize_str((body.get('description') or '').strip()),
        user_id=user_id,
    )
    db.session.add(project)
    db.session.commit()
    return ok(clean_response(project.to_dict()), '项目创建成功'), 201


@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    user_id = int(get_jwt_identity())
    project = _require_project(project_id, user_id)
    return ok(clean_response(project.to_dict()))


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    user_id = int(get_jwt_identity())
    project = _require_project(project_id, user_id)

    body = request.get_json(silent=True) or {}
    name = sanitize_str((body.get('name') or '').strip())
    if name:
        project.name = name
    if 'description' in body:
        project.description = sanitize_str((body['description'] or '').strip())
    project.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return ok(clean_response(project.to_dict()), '项目更新成功')


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    user_id = int(get_jwt_identity())
    project = _require_project(project_id, user_id)
    db.session.delete(project)
    db.session.commit()
    return ok(None, '项目已删除')
