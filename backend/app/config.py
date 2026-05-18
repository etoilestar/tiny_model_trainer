import os
from datetime import timedelta


def _build_redis_url() -> str:
    """从环境变量中的各字段组装 Redis URL，优先使用 REDIS_URL（若已设置）。"""
    explicit = os.environ.get('REDIS_URL')
    if explicit:
        return explicit
    host = os.environ.get('REDIS_HOST', '127.0.0.1')
    port = os.environ.get('REDIS_PORT', '6379')
    password = os.environ.get('REDIS_PASSWORD', '')
    db = os.environ.get('REDIS_DB', '0')
    auth = f':{password}@' if password else ''
    return f'redis://{auth}{host}:{port}/{db}'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///trainer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    CELERY_BROKER_URL = _build_redis_url()
    CELERY_RESULT_BACKEND = _build_redis_url()

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
    MODEL_FOLDER = os.environ.get('MODEL_FOLDER', './models')
    CHECKPOINT_FOLDER = os.environ.get('CHECKPOINT_FOLDER', './checkpoints')

    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

    CORS_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
