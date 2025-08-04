"""
IP智慧解答专家系统 - 知识文档模型

本模块定义了知识文档相关的数据模型。
"""

from app import db
from datetime import datetime
import uuid


class KnowledgeDocument(db.Model):
    """知识文档模型"""

    __tablename__ = 'knowledge_documents'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))

    # 元数据
    vendor = db.Column(db.String(50))
    tags = db.Column(db.JSON)

    # 处理状态
    status = db.Column(db.Enum('QUEUED', 'PARSING', 'INDEXED', 'FAILED', name='document_status'), default='QUEUED')
    progress = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)

    # 软删除标志
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    # 时间戳
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 关系
    parsing_jobs = db.relationship('ParsingJob', backref='document', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        """转换为字典"""
        return {
            'docId': self.id,
            'fileName': self.original_filename,
            'vendor': self.vendor,
            'tags': self.tags,
            'status': self.status,
            'progress': self.progress,
            'uploadedAt': self.uploaded_at.isoformat() + 'Z' if self.uploaded_at else None,
            'processedAt': self.processed_at.isoformat() + 'Z' if self.processed_at else None
        }


class ParsingJob(db.Model):
    """解析任务模型"""

    __tablename__ = 'parsing_jobs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(db.String(36), db.ForeignKey('knowledge_documents.id'), nullable=False)
    status = db.Column(db.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='job_status'), default='PENDING')
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    result_data = db.Column(db.JSON)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'status': self.status,
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else None,
            'error_message': self.error_message
        }


class DocumentChunk(db.Model):
    """文档块模型"""

    __tablename__ = 'document_chunks'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(db.String(36), db.ForeignKey('knowledge_documents.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(500))
    page_number = db.Column(db.Integer, default=0)
    chunk_metadata = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    document = db.relationship('KnowledgeDocument', backref='chunks')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'title': self.title,
            'page_number': self.page_number,
            'metadata': self.chunk_metadata,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }
