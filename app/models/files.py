"""
文件附件数据模型

定义文件和附件的数据结构。
"""

from app import db
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean
from datetime import datetime
import uuid


class UserFile(db.Model):
    """用户文件模型"""
    __tablename__ = 'user_files'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=True)  # image, topo, log, config, other
    mime_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # 用户关联
    user_id = Column(String(36), nullable=False, index=True)

    # 安全扫描结果
    security_scan_status = Column(String(20), default='pending')  # pending, clean, threat, error
    security_scan_time = Column(DateTime, nullable=True)
    security_scan_details = Column(JSON, nullable=True)

    # 访问统计
    download_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)

    # 关联案例
    associated_cases = Column(JSON, default=list)  # 存储case_id列表

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 软删除
    is_deleted = Column(Boolean, default=False)

    def to_dict(self):
        """转换为字典格式"""
        return {
            'fileId': self.id,
            'fileName': self.original_filename,
            'fileSize': self.file_size,
            'fileType': self.file_type,
            'mimeType': self.mime_type,
            'description': self.description,
            'uploadedAt': self.created_at.isoformat() + 'Z',
            'uploadedBy': self.user_id,
            'associatedCases': self.associated_cases or [],
            'downloadCount': self.download_count,
            'lastAccessed': self.last_accessed.isoformat() + 'Z' if self.last_accessed else None,
            'securityScan': {
                'status': self.security_scan_status,
                'scanTime': self.security_scan_time.isoformat() + 'Z' if self.security_scan_time else None,
                'details': self.security_scan_details
            }
        }

    def to_simple_dict(self):
        """转换为简单字典格式（用于附件列表）"""
        return {
            'type': self.file_type,
            'url': f'/api/v1/files/{self.id}',
            'name': self.original_filename
        }

    def __repr__(self):
        return f'<UserFile {self.id}: {self.original_filename}>'
