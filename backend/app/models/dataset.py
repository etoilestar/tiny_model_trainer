from datetime import datetime, timezone
from ..extensions import db

DATASET_FORMATS = ('yolo', 'coco', 'imagefolder', 'csv', 'jsonl')
DATASET_STATUSES = ('uploading', 'ready', 'error')


class Dataset(db.Model):
    __tablename__ = 'datasets'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    format = db.Column(db.String(32), nullable=False)  # yolo/coco/imagefolder/csv/jsonl
    file_path = db.Column(db.String(512), nullable=False)
    size = db.Column(db.BigInteger, default=0)  # bytes
    status = db.Column(db.String(32), default='ready')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'format': self.format,
            'file_path': self.file_path,
            'size': self.size,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
        }
