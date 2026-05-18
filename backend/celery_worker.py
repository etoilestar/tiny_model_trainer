"""Celery worker entry point.

Usage:
    celery -A celery_worker.celery worker --loglevel=info
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app          # noqa: E402
from app.extensions import celery   # noqa: E402

app = create_app(os.environ.get('FLASK_ENV', 'development'))
app.app_context().push()

# Import tasks so Celery discovers them
import app.tasks.training_task  # noqa: F401, E402
