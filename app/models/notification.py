"""
通知数据模型

定义系统通知的数据结构。
"""

from app import db
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from datetime import datetime
import uuid


class Notification(db.Model):
    """系统通知模型"""
    __tablename__ = 'notifications'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 通知内容
    type = Column(String(50), nullable=False)  # solution, mention, system
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)

    # 接收者
    user_id = Column(String(36), nullable=False, index=True)

    # 状态
    read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # 关联数据
    related_case_id = Column(String(36), nullable=True)
    related_node_id = Column(String(36), nullable=True)

    # 额外元数据
    extra_metadata = Column(Text, nullable=True)  # JSON格式的额外信息

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'content': self.content,
            'read': self.read,
            'readAt': self.read_at.isoformat() + 'Z' if self.read_at else None,
            'relatedCaseId': self.related_case_id,
            'relatedNodeId': self.related_node_id,
            'createdAt': self.created_at.isoformat() + 'Z',
            'updatedAt': self.updated_at.isoformat() + 'Z'
        }

    @classmethod
    def create_solution_notification(cls, user_id, case_id, node_id, case_title):
        """创建解决方案生成通知"""
        notification = cls(
            type='solution',
            title='诊断案例已生成解决方案',
            content=f'您的诊断案例《{case_title}》已生成解决方案，请查看。',
            user_id=user_id,
            related_case_id=case_id,
            related_node_id=node_id
        )
        return notification

    @classmethod
    def create_mention_notification(cls, user_id, case_id, content):
        """创建提及通知"""
        notification = cls(
            type='mention',
            title='有人在案例中提及了您',
            content=content,
            user_id=user_id,
            related_case_id=case_id
        )
        return notification

    @classmethod
    def create_system_notification(cls, user_id, title, content):
        """创建系统通知"""
        notification = cls(
            type='system',
            title=title,
            content=content,
            user_id=user_id
        )
        return notification

    def mark_as_read(self):
        """标记为已读"""
        if not self.read:
            self.read = True
            self.read_at = datetime.utcnow()

    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
