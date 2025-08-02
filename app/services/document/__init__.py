"""
文档处理服务模块

包含所有文档处理相关的服务：
- 文档服务：文档解析和处理
- IDP服务：阿里云文档智能服务
- 语义分割：文档内容智能分割
- 任务处理器：文档处理任务管理
"""

from .document_service import parse_document
from .idp_service import IDPService
from .semantic_splitter import SemanticSplitter
from .idp_task_processor import (
    parse_document_with_idp,
    reprocess_document,
    batch_process_documents,
    get_processing_statistics
)

__all__ = [
    'parse_document',
    'IDPService',
    'SemanticSplitter',
    'parse_document_with_idp',
    'reprocess_document',
    'batch_process_documents',
    'get_processing_statistics'
]
