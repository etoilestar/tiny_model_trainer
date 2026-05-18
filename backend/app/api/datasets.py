import os
import uuid

from flask import Blueprint, request, jsonify, current_app, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.dataset import Dataset, DATASET_FORMATS
from ..models.project import Project
from .utils import sanitize_str, clean_response

datasets_bp = Blueprint('datasets', __name__)

# Map validated format strings to safe file extensions (no user input used).
_FMT_EXT = {'yolo': '.zip', 'coco': '.zip', 'imagefolder': '.zip',
             'csv': '.csv', 'jsonl': '.jsonl'}


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


@datasets_bp.route('/', methods=['GET'])
@jwt_required()
def list_datasets():
    user_id = int(get_jwt_identity())
    project_id = request.args.get('project_id', type=int)
    if not project_id:
        return err('缺少 project_id 参数')

    _require_project(project_id, user_id)

    datasets = Dataset.query.filter_by(project_id=project_id).order_by(Dataset.created_at.desc()).all()
    return ok(clean_response([d.to_dict() for d in datasets]))


@datasets_bp.route('/', methods=['POST'])
@jwt_required()
def upload_dataset():
    user_id = int(get_jwt_identity())

    project_id = request.form.get('project_id', type=int)
    name = sanitize_str((request.form.get('name') or '').strip())
    description = sanitize_str((request.form.get('description') or '').strip())
    fmt = sanitize_str((request.form.get('format') or '').strip())

    if not project_id:
        return err('缺少 project_id 参数')
    if not name:
        return err('数据集名称不能为空')
    if fmt not in DATASET_FORMATS:
        return err(f'不支持的数据集格式，支持: {", ".join(DATASET_FORMATS)}')

    _require_project(project_id, user_id)

    if 'file' not in request.files:
        return err('请上传数据集文件')

    file = request.files['file']
    if file.filename == '':
        return err('文件名不能为空')

    # Extension from validated format constant only — no user filename used.
    ext = _FMT_EXT.get(fmt, '.bin')
    safe_filename = f'{uuid.uuid4().hex}{ext}'

    # Flat directory from server config only — no user-derived path components.
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)
    file.save(file_path)
    file_size = os.path.getsize(file_path)

    dataset = Dataset(
        project_id=project_id,
        name=name,
        description=description,
        format=fmt,
        file_path=file_path,
        size=file_size,
        status='ready',
    )
    db.session.add(dataset)
    db.session.commit()
    return ok(clean_response(dataset.to_dict()), '数据集上传成功'), 201


@datasets_bp.route('/<int:dataset_id>', methods=['GET'])
@jwt_required()
def get_dataset(dataset_id):
    user_id = int(get_jwt_identity())
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return err('数据集不存在', 404)

    _require_project(dataset.project_id, user_id)
    return ok(clean_response(dataset.to_dict()))


@datasets_bp.route('/<int:dataset_id>', methods=['DELETE'])
@jwt_required()
def delete_dataset(dataset_id):
    user_id = int(get_jwt_identity())
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset:
        return err('数据集不存在', 404)

    _require_project(dataset.project_id, user_id)

    if dataset.file_path and os.path.exists(dataset.file_path):
        try:
            os.remove(dataset.file_path)
        except OSError:
            pass

    db.session.delete(dataset)
    db.session.commit()
    return ok(None, '数据集已删除')
