"""
IP智慧解答专家系统 - 用户模型

本模块定义了用户相关的数据模型。
"""

from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(db.Model):
    """用户模型"""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    roles = db.Column(db.String(100), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    cases = db.relationship('Case', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    knowledge_documents = db.relationship('KnowledgeDocument', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', foreign_keys='Feedback.user_id', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    settings = db.relationship('UserSettings', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        """
        设置用户密码

        Args:
            password (str): 明文密码
        """
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """
        验证用户密码

        Args:
            password (str): 明文密码

        Returns:
            bool: 密码是否正确
        """
        return check_password_hash(self.password_hash, password)

    def get_roles(self):
        """
        获取用户角色列表

        Returns:
            list: 角色列表
        """
        return self.roles.split(',') if self.roles else []

    def has_role(self, role):
        """
        检查用户是否具有指定角色

        Args:
            role (str): 角色名称

        Returns:
            bool: 是否具有该角色
        """
        return role in self.get_roles()

    def to_dict(self):
        """
        将用户对象转换为字典

        Returns:
            dict: 用户信息字典
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'roles': self.get_roles(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }

    def __repr__(self):
        return f'<User {self.username}>'
