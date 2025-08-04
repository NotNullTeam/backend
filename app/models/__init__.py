"""
数据模型模块

包含所有数据库模型定义。
"""

# 导入所有模型，确保它们被注册到SQLAlchemy
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback
from app.models.files import UserFile
from app.models.user_settings import UserSettings
from app.models.notification import Notification
from app.models.prompt import PromptTemplate

__all__ = [
    'User',
    'Case', 'Node', 'Edge',
    'KnowledgeDocument', 'ParsingJob',
    'Feedback',
    'UserFile',
    'UserSettings',
    'Notification',
    'PromptTemplate'
]
