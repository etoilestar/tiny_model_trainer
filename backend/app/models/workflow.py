from datetime import datetime, timezone
from ..extensions import db


class Workflow(db.Model):
    __tablename__ = 'workflows'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    canvas_json = db.Column(db.Text, default='{}')  # Vue Flow JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    training_jobs = db.relationship('TrainingJob', backref='workflow', lazy='dynamic')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'canvas_json': self.canvas_json,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
