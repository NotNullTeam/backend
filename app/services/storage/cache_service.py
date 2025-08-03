"""
缓存服务

提供Redis缓存功能，用于缓存AI模型调用结果，提高系统性能。
"""

import redis
import hashlib
import json
import logging
import os
from typing import Any, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类"""

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化缓存服务

        Args:
            redis_url: Redis连接URL，如果为None则从环境变量获取
        """
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis缓存服务连接成功")
        except Exception as e:
            logger.error(f"Redis缓存服务连接失败: {e}")
            self.redis_client = None

    def get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存结果

        Args:
            key: 缓存键

        Returns:
            缓存的结果，如果不存在则返回None
        """
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get(key)
            if cached:
                result = json.loads(cached)
                logger.debug(f"缓存命中: {key}")
                return result
            logger.debug(f"缓存未命中: {key}")
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    def cache_result(self, key: str, result: Dict[str, Any], expire_time: int = 3600) -> bool:
        """
        缓存结果

        Args:
            key: 缓存键
            result: 要缓存的结果
            expire_time: 过期时间（秒），默认1小时

        Returns:
            是否缓存成功
        """
        if not self.redis_client:
            return False

        try:
            # 添加缓存时间戳
            cache_data = {
                'data': result,
                'cached_at': datetime.now().isoformat(),
                'expires_at': expire_time
            }

            success = self.redis_client.setex(
                key,
                expire_time,
                json.dumps(cache_data, ensure_ascii=False)
            )

            if success:
                logger.debug(f"缓存设置成功: {key}, 过期时间: {expire_time}秒")
            return success
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False

    def delete_cache(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not self.redis_client:
            return False

        try:
            result = self.redis_client.delete(key)
            logger.debug(f"删除缓存: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False

    def generate_cache_key(self, prefix: str, *args) -> str:
        """
        生成缓存键

        Args:
            prefix: 缓存键前缀
            *args: 用于生成缓存键的参数

        Returns:
            生成的缓存键
        """
        try:
            # 将所有参数转换为字符串并连接
            content = f"{prefix}:{':'.join(str(arg) for arg in args)}"
            # 使用MD5生成固定长度的键
            cache_key = hashlib.md5(content.encode('utf-8')).hexdigest()
            return f"{prefix}:{cache_key}"
        except Exception as e:
            logger.error(f"生成缓存键失败: {e}")
            # 如果生成失败，返回基于时间戳的键
            return f"{prefix}:{int(datetime.now().timestamp())}"

    def clear_cache_by_pattern(self, pattern: str) -> int:
        """
        根据模式清除缓存

        Args:
            pattern: 缓存键模式，如 "llm:*"

        Returns:
            清除的缓存数量
        """
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"清除缓存: 模式={pattern}, 数量={deleted}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return 0

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存基本信息

        Returns:
            缓存基本信息
        """
        if not self.redis_client:
            return {
                'type': 'redis',
                'connected': False,
                'error': 'Redis客户端未连接'
            }

        try:
            # 测试连接
            self.redis_client.ping()
            info = self.redis_client.info()
            return {
                'type': 'redis',
                'connected': True,
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients')
            }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return {
                'type': 'redis',
                'connected': False,
                'error': str(e)
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息
        """
        if not self.redis_client:
            return {'status': 'disconnected'}

        try:
            info = self.redis_client.info()
            return {
                'status': 'connected',
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
                'hit_rate': round(
                    info.get('keyspace_hits', 0) /
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
                    2
                )
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {'status': 'error', 'error': str(e)}

    def clear_all(self) -> bool:
        """
        清空所有缓存

        Returns:
            bool: 清空成功返回True，失败返回False
        """
        if not self.redis_client:
            logger.warning("Redis客户端未连接，无法清空缓存")
            return False

        try:
            self.redis_client.flushdb()
            logger.info("所有缓存已清空")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False

    def clear_all_cache(self) -> bool:
        """
        清空所有缓存（别名方法）

        Returns:
            bool: 清空成功返回True，失败返回False
        """
        return self.clear_all()


# 全局缓存服务实例
cache_service = CacheService()


def cached_llm_call(cache_key_prefix: str, expire_time: int = 3600):
    """
    LLM调用缓存装饰器

    Args:
        cache_key_prefix: 缓存键前缀
        expire_time: 过期时间（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_service.generate_cache_key(
                cache_key_prefix,
                *args,
                *[f"{k}={v}" for k, v in sorted(kwargs.items())]
            )

            # 尝试从缓存获取结果
            cached_result = cache_service.get_cached_result(cache_key)
            if cached_result and 'data' in cached_result:
                logger.debug(f"使用缓存结果: {cache_key_prefix}")
                return cached_result['data']

            # 缓存未命中，调用原函数
            try:
                result = func(*args, **kwargs)
                # 缓存结果
                cache_service.cache_result(cache_key, result, expire_time)
                return result
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")
                raise

        return wrapper
    return decorator


def cached_retrieval_call(cache_key_prefix: str, expire_time: int = 1800):
    """
    检索调用缓存装饰器

    Args:
        cache_key_prefix: 缓存键前缀
        expire_time: 过期时间（秒），默认30分钟
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_service.generate_cache_key(
                cache_key_prefix,
                *args,
                *[f"{k}={v}" for k, v in sorted(kwargs.items())]
            )

            # 尝试从缓存获取结果
            cached_result = cache_service.get_cached_result(cache_key)
            if cached_result and 'data' in cached_result:
                logger.debug(f"使用缓存检索结果: {cache_key_prefix}")
                return cached_result['data']

            # 缓存未命中，调用原函数
            try:
                result = func(*args, **kwargs)
                # 缓存结果
                cache_service.cache_result(cache_key, result, expire_time)
                return result
            except Exception as e:
                logger.error(f"检索调用失败: {e}")
                raise

        return wrapper
    return decorator


def get_cache_service() -> CacheService:
    """
    获取缓存服务实例

    Returns:
        CacheService: 缓存服务实例
    """
    return cache_service
