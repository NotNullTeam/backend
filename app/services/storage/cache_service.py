"""
缓存服务

本模块实现了LLM服务的缓存机制，提高响应性能。
"""

import os
import redis
import hashlib
import json
import logging
from typing import Any, Dict, Optional
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类"""

    def __init__(self):
        """初始化缓存服务"""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)

            # 测试连接
            self.redis_client.ping()
            logger.info("缓存服务初始化成功")

        except Exception as e:
            logger.error(f"缓存服务初始化失败: {str(e)}")
            # 使用内存缓存作为备选
            self.redis_client = None
            self._memory_cache = {}

    def get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存结果

        Args:
            key: 缓存键

        Returns:
            缓存的结果或None
        """
        try:
            if self.redis_client:
                cached = self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            else:
                # 使用内存缓存
                return self._memory_cache.get(key)
        except Exception as e:
            logger.error(f"获取缓存失败: {str(e)}")

        return None

    def cache_result(self, key: str, result: Dict[str, Any],
                    expire_time: int = 3600) -> bool:
        """
        缓存结果

        Args:
            key: 缓存键
            result: 要缓存的结果
            expire_time: 过期时间（秒）

        Returns:
            是否缓存成功
        """
        try:
            if self.redis_client:
                return self.redis_client.setex(
                    key, expire_time, json.dumps(result, ensure_ascii=False)
                )
            else:
                # 使用内存缓存（简单实现，不考虑过期）
                self._memory_cache[key] = result
                return True
        except Exception as e:
            logger.error(f"缓存结果失败: {str(e)}")
            return False

    def generate_cache_key(self, prefix: str, *args) -> str:
        """
        生成缓存键

        Args:
            prefix: 键前缀
            *args: 用于生成键的参数

        Returns:
            生成的缓存键
        """
        content = f"{prefix}:{':'.join(map(str, args))}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def delete_cache(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                self._memory_cache.pop(key, None)
                return True
        except Exception as e:
            logger.error(f"删除缓存失败: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的缓存

        Args:
            pattern: 匹配模式（如 "llm:analysis:*"）

        Returns:
            删除的键数量
        """
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # 内存缓存简单匹配
                keys_to_delete = [k for k in self._memory_cache.keys()
                                if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                return len(keys_to_delete)
        except Exception as e:
            logger.error(f"清除模式缓存失败: {str(e)}")
            return 0

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            缓存统计信息
        """
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    "type": "redis",
                    "connected": True,
                    "used_memory": info.get('used_memory_human', 'N/A'),
                    "connected_clients": info.get('connected_clients', 0),
                    "keyspace": info.get('keyspace', {}),
                    "uptime": info.get('uptime_in_seconds', 0)
                }
            else:
                return {
                    "type": "memory",
                    "connected": True,
                    "cached_keys": len(self._memory_cache),
                    "memory_usage": "N/A"
                }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {str(e)}")
            return {
                "type": "unknown",
                "connected": False,
                "error": str(e)
            }


# 缓存装饰器
def cached_llm_result(expire_time: int = 3600, cache_prefix: str = "llm"):
    """
    LLM结果缓存装饰器

    Args:
        expire_time: 缓存过期时间（秒）
        cache_prefix: 缓存键前缀
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 初始化缓存服务
            cache_service = CacheService()

            # 生成缓存键
            cache_key = cache_service.generate_cache_key(
                cache_prefix, func.__name__, *args,
                *[f"{k}:{v}" for k, v in sorted(kwargs.items())]
            )

            # 尝试从缓存获取结果
            cached_result = cache_service.get_cached_result(cache_key)
            if cached_result:
                logger.info(f"从缓存获取结果: {func.__name__}")
                return cached_result

            # 执行原函数
            result = func(*args, **kwargs)

            # 缓存结果（如果没有错误）
            if isinstance(result, dict) and 'error' not in result:
                cache_service.cache_result(cache_key, result, expire_time)
                logger.info(f"缓存结果: {func.__name__}")

            return result

        return wrapper
    return decorator


# 全局缓存服务实例
_cache_service = None

def get_cache_service() -> CacheService:
    """获取缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
