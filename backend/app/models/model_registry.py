from datetime import datetime, timezone
from ..extensions import db


class ModelRegistry(db.Model):
    __tablename__ = 'model_registry'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('training_jobs.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    version = db.Column(db.String(32), default='v1.0')
    framework = db.Column(db.String(32), default='pytorch')  # pytorch/onnx
    file_path = db.Column(db.String(512), nullable=False)
    metrics_json = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'job_id': self.job_id,
            'name': self.name,
            'version': self.version,
            'framework': self.framework,
            'file_path': self.file_path,
            'metrics_json': self.metrics_json,
            'created_at': self.created_at.isoformat(),
        }
