"""
用户设置数据模型

定义用户个性化配置的数据结构。
"""

from app import db
from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime


class UserSettings(db.Model):
    """用户设置模型"""
    __tablename__ = 'user_settings'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)

    # 主题设置
    theme = Column(String(20), default='system')  # light, dark, system

    # 通知偏好设置
    notifications = Column(JSON, default=lambda: {
        'solution': True,    # 解决方案生成通知
        'mention': False,    # 提及通知
        'system': True       # 系统通知
    })

    # 其他个性化配置
    preferences = Column(JSON, default=lambda: {
        'language': 'zh-cn',
        'autoSave': True,
        'showHints': True
    })

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship('User', back_populates='settings')

    def to_dict(self):
        """转换为字典格式"""
        return {
            'theme': self.theme,
            'notifications': self.notifications or {
                'solution': True,
                'mention': False,
                'system': True
            },
            'preferences': self.preferences or {
                'language': 'zh-cn',
                'autoSave': True,
                'showHints': True
            },
            'updatedAt': self.updated_at.isoformat() + 'Z'
        }

    @classmethod
    def get_or_create_for_user(cls, user_id):
        """获取或创建用户设置"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = cls(user_id=user_id)
            db.session.add(settings)
            db.session.commit()
        return settings

    def __repr__(self):
        return f'<UserSettings {self.user_id}>'
