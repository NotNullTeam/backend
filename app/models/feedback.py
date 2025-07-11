"""
IP智慧解答专家系统 - 反馈模型

本模块定义了用户反馈相关的数据模型。
"""

from app import db
from datetime import datetime
import uuid


class Feedback(db.Model):
    """反馈模型"""
    
    __tablename__ = 'feedback'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    outcome = db.Column(db.Enum('solved', 'unsolved', 'partially_solved', name='feedback_outcome'), nullable=False)
    rating = db.Column(db.Integer)  # 1-5评分
    comment = db.Column(db.Text)
    corrected_solution = db.Column(db.JSON)
    
    # 知识贡献相关
    knowledge_contribution = db.Column(db.JSON)
    additional_context = db.Column(db.JSON)
    
    # 审核状态
    review_status = db.Column(db.Enum('pending', 'approved', 'rejected', name='review_status'), default='pending')
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'outcome': self.outcome,
            'rating': self.rating,
            'comment': self.comment,
            'review_status': self.review_status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }
