import os
from flask import Flask
from .config import config_map
from .extensions import db, jwt, migrate, cors, celery


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    # Load config
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # Ensure required folders exist
    for folder_key in ('UPLOAD_FOLDER', 'MODEL_FOLDER', 'CHECKPOINT_FOLDER'):
        folder = app.config[folder_key]
        os.makedirs(folder, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS']}},
                  supports_credentials=True)

    # Configure Celery
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='Asia/Shanghai',
        enable_utc=True,
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # Import models so Flask-Migrate picks them up
    from .models import user, project, dataset, workflow, training_job, model_registry  # noqa: F401

    # Register blueprints
    from .api.auth import auth_bp
    from .api.projects import projects_bp
    from .api.datasets import datasets_bp
    from .api.workflows import workflows_bp
    from .api.training import training_bp
    from .api.metrics import metrics_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(datasets_bp, url_prefix='/api/datasets')
    app.register_blueprint(workflows_bp, url_prefix='/api/workflows')
    app.register_blueprint(training_bp, url_prefix='/api/training')
    app.register_blueprint(metrics_bp, url_prefix='/api/metrics')

    # Register JSON error handler so abort() produces our standard format
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        return jsonify({'code': 1, 'message': exc.description}), exc.code

    # Auto-create tables for SQLite development
    with app.app_context():
        db.create_all()

    return app
