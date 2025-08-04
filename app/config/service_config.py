"""
服务配置管理

管理各个服务的配置和依赖关系。
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class KnowledgeServiceConfig:
    """知识检索服务配置"""
    vector_db_type: str = 'mock'  # mock, weaviate, elasticsearch, pinecone
    vector_db_url: Optional[str] = None
    vector_db_api_key: Optional[str] = None
    embedding_model: str = 'text-embedding-ada-002'
    max_results: int = 20
    default_top_k: int = 5
    cache_ttl: int = 3600  # 缓存时间（秒）


@dataclass
class LogParsingServiceConfig:
    """日志解析服务配置"""
    ai_provider: str = 'mock'  # mock, openai, azure, local
    model_name: str = 'gpt-3.5-turbo'
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30


@dataclass
class VendorCommandServiceConfig:
    """厂商命令服务配置"""
    template_path: str = 'templates/commands'
    supported_vendors: list = None
    custom_templates_enabled: bool = True

    def __post_init__(self):
        if self.supported_vendors is None:
            self.supported_vendors = ['Huawei', 'Cisco', 'Juniper', 'H3C']


class ServiceConfig:
    """服务配置管理器"""

    def __init__(self):
        self.knowledge_service = KnowledgeServiceConfig()
        self.log_parsing_service = LogParsingServiceConfig()
        self.vendor_command_service = VendorCommandServiceConfig()
        self._load_from_env()

    def _load_from_env(self):
        """从环境变量加载配置"""
        # 知识检索服务配置
        self.knowledge_service.vector_db_type = os.getenv(
            'VECTOR_DB_TYPE',
            self.knowledge_service.vector_db_type
        )
        self.knowledge_service.vector_db_url = os.getenv('VECTOR_DB_URL')
        self.knowledge_service.vector_db_api_key = os.getenv('VECTOR_DB_API_KEY')
        self.knowledge_service.embedding_model = os.getenv(
            'EMBEDDING_MODEL',
            self.knowledge_service.embedding_model
        )

        # 日志解析服务配置
        self.log_parsing_service.ai_provider = os.getenv(
            'AI_PROVIDER',
            self.log_parsing_service.ai_provider
        )
        self.log_parsing_service.model_name = os.getenv(
            'AI_MODEL_NAME',
            self.log_parsing_service.model_name
        )
        self.log_parsing_service.api_key = os.getenv('AI_API_KEY')
        self.log_parsing_service.api_base = os.getenv('AI_API_BASE')

        # 从环境变量中读取数值类型配置
        try:
            self.knowledge_service.max_results = int(os.getenv(
                'KNOWLEDGE_MAX_RESULTS',
                str(self.knowledge_service.max_results)
            ))
            self.log_parsing_service.max_tokens = int(os.getenv(
                'AI_MAX_TOKENS',
                str(self.log_parsing_service.max_tokens)
            ))
            self.log_parsing_service.temperature = float(os.getenv(
                'AI_TEMPERATURE',
                str(self.log_parsing_service.temperature)
            ))
        except (ValueError, TypeError):
            # 如果环境变量格式不正确，使用默认值
            pass

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态信息"""
        return {
            'knowledge_service': {
                'enabled': self.knowledge_service.vector_db_type != 'mock',
                'type': self.knowledge_service.vector_db_type,
                'configured': self.knowledge_service.vector_db_url is not None
            },
            'log_parsing_service': {
                'enabled': self.log_parsing_service.ai_provider != 'mock',
                'provider': self.log_parsing_service.ai_provider,
                'configured': self.log_parsing_service.api_key is not None
            },
            'vendor_command_service': {
                'enabled': True,
                'supported_vendors': self.vendor_command_service.supported_vendors,
                'custom_templates': self.vendor_command_service.custom_templates_enabled
            }
        }

    def validate_config(self) -> Dict[str, list]:
        """验证配置有效性"""
        errors = {}
        warnings = {}

        # 验证知识检索服务配置
        if self.knowledge_service.vector_db_type not in ['mock', 'weaviate', 'elasticsearch', 'pinecone']:
            errors.setdefault('knowledge_service', []).append(
                f"不支持的向量数据库类型: {self.knowledge_service.vector_db_type}"
            )

        if (self.knowledge_service.vector_db_type != 'mock' and
            not self.knowledge_service.vector_db_url):
            warnings.setdefault('knowledge_service', []).append(
                "向量数据库URL未配置，将使用Mock模式"
            )

        # 验证日志解析服务配置
        if self.log_parsing_service.ai_provider not in ['mock', 'openai', 'azure', 'local']:
            errors.setdefault('log_parsing_service', []).append(
                f"不支持的AI提供商: {self.log_parsing_service.ai_provider}"
            )

        if (self.log_parsing_service.ai_provider != 'mock' and
            not self.log_parsing_service.api_key):
            warnings.setdefault('log_parsing_service', []).append(
                "AI API密钥未配置，将使用Mock模式"
            )

        return {'errors': errors, 'warnings': warnings}


# 全局配置实例
service_config = ServiceConfig()
