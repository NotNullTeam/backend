"""
IP智慧解答专家系统 - 案例模型

本模块定义了诊断案例相关的数据模型。
"""

from app import db
from datetime import datetime
import uuid


class Case(db.Model):
    """诊断案例模型"""

    __tablename__ = 'cases'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Enum('open', 'solved', 'closed', name='case_status'), default='open')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    nodes = db.relationship('Node', backref='case', lazy='dynamic', cascade='all, delete-orphan')
    edges = db.relationship('Edge', backref='case', lazy='dynamic', cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', backref='case', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        """转换为字典"""
        return {
            'caseId': self.id,
            'title': self.title,
            'status': self.status,
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }


class Node(db.Model):
    """节点模型"""

    __tablename__ = 'nodes'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    type = db.Column(db.Enum('USER_QUERY', 'AI_ANALYSIS', 'AI_CLARIFICATION', 'USER_RESPONSE', 'SOLUTION', name='node_type'))
    title = db.Column(db.String(200))
    status = db.Column(db.Enum('COMPLETED', 'AWAITING_USER_INPUT', 'PROCESSING', name='node_status'), default='PROCESSING')
    content = db.Column(db.JSON)
    node_metadata = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'status': self.status,
            'content': self.content,
            'metadata': self.node_metadata
        }


class Edge(db.Model):
    """边模型"""

    __tablename__ = 'edges'

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    source = db.Column(db.String(36), nullable=False)
    target = db.Column(db.String(36), nullable=False)

    def to_dict(self):
        """转换为字典"""
        return {
            'source': self.source,
            'target': self.target
        }
