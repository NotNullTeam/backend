from app import db
from datetime import datetime

class PromptTemplate(db.Model):
    __tablename__ = 'prompt_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.String(255))
    category = db.Column(db.String(50), index=True)
    is_active = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'version': self.version,
            'description': self.description,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z'
        }

    def __repr__(self):
        return f'<PromptTemplate {self.name} v{self.version}>'
