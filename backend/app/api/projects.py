from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, abort

from ..extensions import db
from ..models.project import Project
from .utils import sanitize_str, clean_response

projects_bp = Blueprint('projects', __name__)


def ok(data=None, message='成功'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def err(message='操作失败', status=400):
    return jsonify({'code': 1, 'message': message}), status


def _require_project(project_id: int) -> Project:
    """Return the project or abort with the appropriate HTTP error."""
    project = db.session.get(Project, project_id)
    if not project:
        abort(404, '项目不存在')
    return project


@projects_bp.route('/', methods=['GET'])
def list_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return ok(clean_response([p.to_dict() for p in projects]))


@projects_bp.route('/', methods=['POST'])
def create_project():
    body = request.get_json(silent=True) or {}
    name = sanitize_str((body.get('name') or '').strip())
    if not name:
        return err('项目名称不能为空')

    project = Project(
        name=name,
        description=sanitize_str((body.get('description') or '').strip()),
    )
    db.session.add(project)
    db.session.commit()
    return ok(clean_response(project.to_dict()), '项目创建成功'), 201


@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = _require_project(project_id)
    return ok(clean_response(project.to_dict()))


@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = _require_project(project_id)

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
def delete_project(project_id):
    project = _require_project(project_id)
    db.session.delete(project)
    db.session.commit()
    return ok(None, '项目已删除')
