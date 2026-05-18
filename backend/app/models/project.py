from datetime import datetime, timezone
from ..extensions import db


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    datasets = db.relationship('Dataset', backref='project', lazy='dynamic',
                               cascade='all, delete-orphan')
    workflows = db.relationship('Workflow', backref='project', lazy='dynamic',
                                cascade='all, delete-orphan')
    training_jobs = db.relationship('TrainingJob', backref='project', lazy='dynamic',
                                    cascade='all, delete-orphan')
    model_versions = db.relationship('ModelRegistry', backref='project', lazy='dynamic',
                                     cascade='all, delete-orphan')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
