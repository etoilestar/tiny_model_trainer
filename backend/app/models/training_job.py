from datetime import datetime, timezone
from ..extensions import db

JOB_STATUSES = ('pending', 'running', 'completed', 'failed', 'stopped')
LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR')


class TrainingJob(db.Model):
    __tablename__ = 'training_jobs'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(32), default='pending', index=True)
    config_json = db.Column(db.Text, default='{}')
    celery_task_id = db.Column(db.String(256), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    logs = db.relationship('TrainingLog', backref='job', lazy='dynamic',
                           cascade='all, delete-orphan')
    metrics = db.relationship('Metric', backref='job', lazy='dynamic',
                              cascade='all, delete-orphan')
    model_registries = db.relationship('ModelRegistry', backref='job', lazy='dynamic',
                                       cascade='all, delete-orphan')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'status': self.status,
            'config_json': self.config_json,
            'celery_task_id': self.celery_task_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'created_at': self.created_at.isoformat(),
        }


class TrainingLog(db.Model):
    __tablename__ = 'training_logs'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('training_jobs.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    level = db.Column(db.String(16), default='INFO')
    message = db.Column(db.Text, nullable=False)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'job_id': self.job_id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'message': self.message,
        }


class Metric(db.Model):
    __tablename__ = 'metrics'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('training_jobs.id'), nullable=False, index=True)
    epoch = db.Column(db.Integer, nullable=False)
    step = db.Column(db.Integer, default=0)
    metric_name = db.Column(db.String(64), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'job_id': self.job_id,
            'epoch': self.epoch,
            'step': self.step,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
        }
