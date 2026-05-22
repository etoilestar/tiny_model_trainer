import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///trainer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    JWT_TOKEN_LOCATION = ['headers', 'query_string']
    JWT_QUERY_STRING_NAME = 'token'
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

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
