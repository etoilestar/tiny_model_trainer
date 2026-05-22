import os
import shutil
import uuid
import zipfile
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.dataset import Dataset, DATASET_FORMATS
from ..models.project import Project
from .utils import sanitize_str, clean_response

datasets_bp = Blueprint('datasets', __name__)

# Map validated format strings to safe file extensions (no user input used).
# 注意：yolo/coco 保持原 zip 逻辑；imagefolder/mmseg 上传 zip 后会解压成目录。
_FMT_EXT = {
    'yolo': '.zip',
    'coco': '.zip',
    'imagefolder': '.zip',
    'mmseg': '.zip',
    'csv': '.csv',
    'jsonl': '.jsonl',
}

# 只对 OpenMMLab 需要目录输入的数据格式做自动解压。
# 这样不会影响现在 YOLO 读取 zip 的逻辑。
_AUTO_EXTRACT_FORMATS = {'imagefolder', 'mmseg'}


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


def _safe_extract_zip(zip_path: str, extract_root: str) -> None:
    """
    安全解压 zip，避免 zip slip 路径穿越。
    """
    extract_root_path = Path(extract_root).resolve()
    extract_root_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            member_name = member.filename
            target_path = (extract_root_path / member_name).resolve()
            if not str(target_path).startswith(str(extract_root_path) + os.sep) and target_path != extract_root_path:
                raise ValueError(f'非法 zip 路径: {member_name}')
        zf.extractall(extract_root_path)


def _strip_single_top_level_dir(path: str) -> str:
    """
    兼容两种压缩习惯：
    1. zip 内直接是 train/images 等目录；
    2. zip 内多包了一层 dataset_name/ 目录。
    """
    root = Path(path)
    children = [p for p in root.iterdir() if not p.name.startswith('__MACOSX')]
    dirs = [p for p in children if p.is_dir()]
    files = [p for p in children if p.is_file()]

    if len(dirs) == 1 and not files:
        return str(dirs[0])
    return str(root)


def _validate_imagefolder_dataset(dataset_root: str) -> None:
    """
    ResNet/mmpretrain 最小分类数据集格式：

        root/
          train/
            class_a/*.jpg
            class_b/*.jpg
          val/
            class_a/*.jpg
            class_b/*.jpg

    val 可选；如果没有 val，openmmlab_trainer.py 会退化为用 train 做验证。
    """
    root = Path(dataset_root)
    train_dir = root / 'train'

    if not train_dir.is_dir():
        raise ValueError('imagefolder 数据集缺少 train/ 目录')

    class_dirs = [p for p in train_dir.iterdir() if p.is_dir()]
    if not class_dirs:
        raise ValueError('imagefolder 数据集 train/ 下至少需要一个类别子目录')

    has_image = False
    allowed_suffix = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    for class_dir in class_dirs:
        if any(p.is_file() and p.suffix.lower() in allowed_suffix for p in class_dir.iterdir()):
            has_image = True
            break

    if not has_image:
        raise ValueError('imagefolder 数据集 train/<class>/ 下没有找到图片文件')


def _validate_mmseg_dataset(dataset_root: str) -> None:
    """
    UNet/mmseg 最小分割数据集格式：

        root/
          images/
            train/*.jpg
            val/*.jpg
          annotations/
            train/*.png
            val/*.png

    mask 必须是单通道类别索引图：背景 0，目标 1，多类继续 2/3/...
    """
    root = Path(dataset_root)
    required_dirs = [
        root / 'images' / 'train',
        root / 'images' / 'val',
        root / 'annotations' / 'train',
        root / 'annotations' / 'val',
    ]

    missing = [str(p.relative_to(root)) for p in required_dirs if not p.is_dir()]
    if missing:
        raise ValueError(f'mmseg 数据集缺少目录: {", ".join(missing)}')

    train_images = list((root / 'images' / 'train').glob('*'))
    train_masks = list((root / 'annotations' / 'train').glob('*'))

    if not any(p.is_file() for p in train_images):
        raise ValueError('mmseg 数据集 images/train/ 下没有图片')
    if not any(p.is_file() for p in train_masks):
        raise ValueError('mmseg 数据集 annotations/train/ 下没有 mask')


def _prepare_uploaded_dataset(fmt: str, file_path: str) -> str:
    """
    返回最终写入 Dataset.file_path 的路径。

    - yolo/coco/csv/jsonl：保持原文件路径，完全不改旧逻辑。
    - imagefolder/mmseg：解压 zip 并返回解压后的目录路径。
    """
    if fmt not in _AUTO_EXTRACT_FORMATS:
        return file_path

    extract_parent = os.path.join(current_app.config['UPLOAD_FOLDER'], 'extracted')
    extract_root = os.path.join(extract_parent, uuid.uuid4().hex)

    try:
        _safe_extract_zip(file_path, extract_root)
        dataset_root = _strip_single_top_level_dir(extract_root)

        if fmt == 'imagefolder':
            _validate_imagefolder_dataset(dataset_root)
        elif fmt == 'mmseg':
            _validate_mmseg_dataset(dataset_root)

        return dataset_root

    except Exception:
        shutil.rmtree(extract_root, ignore_errors=True)
        raise


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

    try:
        final_dataset_path = _prepare_uploaded_dataset(fmt, file_path)
    except zipfile.BadZipFile:
        try:
            os.remove(file_path)
        except OSError:
            pass
        return err('数据集 zip 文件损坏或格式不正确')
    except ValueError as exc:
        try:
            os.remove(file_path)
        except OSError:
            pass
        return err(str(exc))
    except Exception as exc:
        try:
            os.remove(file_path)
        except OSError:
            pass
        return err(f'数据集处理失败: {exc}')

    dataset = Dataset(
        project_id=project_id,
        name=name,
        description=description,
        format=fmt,
        file_path=final_dataset_path,
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

    # yolo/coco/csv/jsonl 一般是文件；imagefolder/mmseg 是自动解压后的目录。
    if dataset.file_path and os.path.exists(dataset.file_path):
        try:
            if os.path.isdir(dataset.file_path):
                shutil.rmtree(dataset.file_path, ignore_errors=True)
            else:
                os.remove(dataset.file_path)
        except OSError:
            pass

    db.session.delete(dataset)
    db.session.commit()
    return ok(None, '数据集已删除')
