"""
向量数据库配置模块
专注于 Weaviate 本地向量数据库
"""
import os
from enum import Enum

class VectorDBType(Enum):
    """向量数据库类型枚举"""
    WEAVIATE_LOCAL = "weaviate_local"    # 本地 Weaviate 实例


class VectorDBConfig:
    """向量数据库配置类"""

    def __init__(self):
        self.db_type = VectorDBType.WEAVIATE_LOCAL
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载本地 Weaviate 配置"""
        # 测试环境下固定为localhost，避免CI环境变量影响
        testing_env = os.getenv('PYTEST_CURRENT_TEST') is not None
        url_default = 'http://localhost:8080' if testing_env else os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        return {
            'url': url_default,
            'class_name': os.getenv('WEAVIATE_CLASS_NAME', 'Document'),
            'timeout_config': (5, 15),  # (连接超时, 读取超时)
        }

    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return bool(self.config.get('url'))


# 全局配置实例
vector_db_config = VectorDBConfig()
