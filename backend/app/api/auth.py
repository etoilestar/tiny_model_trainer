from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from ..extensions import db
from ..models.user import User
from .utils import clean_response

auth_bp = Blueprint('auth', __name__)


def ok(data=None, message='成功'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def err(message='操作失败', status=400):
    return jsonify({'code': 1, 'message': message}), status


@auth_bp.route('/register', methods=['POST'])
def register():
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip()
    password = (body.get('password') or '').strip()
    email = (body.get('email') or '').strip()

    if not username or not password or not email:
        return err('用户名、密码和邮箱不能为空')

    if len(username) < 3 or len(username) > 80:
        return err('用户名长度应在 3-80 个字符之间')

    if len(password) < 6:
        return err('密码长度不能少于 6 位')

    if User.query.filter_by(username=username).first():
        return err('用户名已存在')

    if User.query.filter_by(email=email).first():
        return err('该邮箱已被注册')

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return ok({'access_token': token, 'user': clean_response(user.to_dict())}, '注册成功'), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip()
    password = (body.get('password') or '').strip()

    if not username or not password:
        return err('用户名和密码不能为空')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return err('用户名或密码错误', 401)

    token = create_access_token(identity=str(user.id))
    return ok({'access_token': token, 'user': clean_response(user.to_dict())}, '登录成功')


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return err('用户不存在', 404)
    return ok(clean_response(user.to_dict()))
