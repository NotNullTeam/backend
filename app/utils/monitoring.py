"""
性能监控工具

提供性能监控装饰器和工具函数，用于监控API响应时间、数据库查询、AI模型调用等性能指标。
"""

import time
import logging
import traceback
from functools import wraps
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self, max_records: int = 1000):
        """
        初始化性能指标收集器

        Args:
            max_records: 最大记录数量
        """
        self.max_records = max_records
        self.metrics = defaultdict(lambda: deque(maxlen=max_records))
        self.counters = defaultdict(int)
        self.lock = threading.Lock()

    def record_metric(self, operation: str, duration: float, success: bool = True,
                     metadata: Optional[Dict[str, Any]] = None):
        """
        记录性能指标

        Args:
            operation: 操作名称
            duration: 执行时间（秒）
            success: 是否成功
            metadata: 附加元数据
        """
        with self.lock:
            timestamp = datetime.now()
            record = {
                'timestamp': timestamp,
                'duration': duration,
                'success': success,
                'metadata': metadata or {}
            }

            self.metrics[operation].append(record)

            # 更新计数器
            self.counters[f"{operation}_total"] += 1
            if success:
                self.counters[f"{operation}_success"] += 1
            else:
                self.counters[f"{operation}_failure"] += 1

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        获取性能统计信息

        Args:
            operation: 特定操作名称，如果为None则返回所有统计

        Returns:
            性能统计信息
        """
        with self.lock:
            if operation:
                return self._calculate_operation_stats(operation)
            else:
                return self._calculate_all_stats()

    def _calculate_operation_stats(self, operation: str) -> Dict[str, Any]:
        """计算特定操作的统计信息"""
        records = list(self.metrics[operation])
        if not records:
            return {
                'operation': operation,
                'total_calls': 0,
                'success_rate': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'p95_duration': 0,
                'p99_duration': 0
            }

        durations = [r['duration'] for r in records]
        successes = [r for r in records if r['success']]

        # 计算百分位数
        sorted_durations = sorted(durations)
        p95_index = int(len(sorted_durations) * 0.95)
        p99_index = int(len(sorted_durations) * 0.99)

        return {
            'operation': operation,
            'total_calls': len(records),
            'success_calls': len(successes),
            'success_rate': len(successes) / len(records) * 100,
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'p95_duration': sorted_durations[p95_index] if p95_index < len(sorted_durations) else 0,
            'p99_duration': sorted_durations[p99_index] if p99_index < len(sorted_durations) else 0,
            'recent_records': records[-10:]  # 最近10条记录
        }

    def _calculate_all_stats(self) -> Dict[str, Any]:
        """计算所有操作的统计信息"""
        stats = {}
        for operation in self.metrics.keys():
            stats[operation] = self._calculate_operation_stats(operation)
        return stats

    def get_all_stats(self, time_window: Optional[int] = None) -> Dict[str, Any]:
        """
        获取所有操作的性能统计信息

        Args:
            time_window: 时间窗口（秒），如果指定则只计算该时间内的数据

        Returns:
            所有操作的统计信息
        """
        with self.lock:
            if time_window:
                # 过滤时间窗口内的数据
                cutoff_time = datetime.now() - timedelta(seconds=time_window)
                filtered_metrics = {}

                for operation, records in self.metrics.items():
                    filtered_records = [
                        record for record in records
                        if record['timestamp'] >= cutoff_time
                    ]
                    if filtered_records:
                        filtered_metrics[operation] = filtered_records

                # 临时替换metrics计算统计
                original_metrics = self.metrics.copy()
                self.metrics = defaultdict(lambda: deque(), filtered_metrics)
                try:
                    stats = self._calculate_all_stats()
                    # 添加总体统计
                    stats['total_operations'] = len(filtered_metrics)
                    stats['time_window'] = time_window
                    return stats
                finally:
                    self.metrics = original_metrics
            else:
                stats = self._calculate_all_stats()
                stats['total_operations'] = len(self.metrics)
                return stats

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取系统健康状态

        Returns:
            系统健康状态信息
        """
        with self.lock:
            all_stats = self._calculate_all_stats()

            total_calls = 0
            total_successes = 0
            unhealthy_operations = []

            for operation, stats in all_stats.items():
                total_calls += stats['total_calls']
                total_successes += stats['success_calls']

                # 检查不健康的操作（成功率低于90%或平均响应时间过长）
                if stats['total_calls'] > 0:
                    if (stats['success_rate'] < 90 or
                        stats['avg_duration'] > 10):  # 10秒阈值
                        unhealthy_operations.append({
                            'operation': operation,
                            'success_rate': stats['success_rate'],
                            'avg_duration': stats['avg_duration']
                        })

            # 计算整体成功率
            overall_success_rate = (total_successes / total_calls * 100) if total_calls > 0 else 100

            # 确定健康状态
            if not unhealthy_operations and overall_success_rate >= 95:
                status = 'healthy'
            elif overall_success_rate >= 80:
                status = 'warning'
            else:
                status = 'critical'

            return {
                'status': status,
                'overall_success_rate': overall_success_rate,
                'total_operations': len(all_stats),
                'total_calls': total_calls,
                'unhealthy_operations': unhealthy_operations,
                'timestamp': datetime.now().isoformat()
            }


# 全局性能指标收集器
performance_metrics = PerformanceMetrics()


def monitor_performance(operation_name: str, include_args: bool = False,
                       log_slow_calls: bool = True, slow_threshold: float = 5.0):
    """
    性能监控装饰器

    Args:
        operation_name: 操作名称
        include_args: 是否在日志中包含函数参数
        log_slow_calls: 是否记录慢调用
        slow_threshold: 慢调用阈值（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = e
                raise
            finally:
                duration = time.time() - start_time

                # 准备元数据
                metadata = {
                    'function': func.__name__,
                    'module': func.__module__
                }

                if include_args and args:
                    metadata['args_count'] = len(args)
                if include_args and kwargs:
                    metadata['kwargs_keys'] = list(kwargs.keys())

                if error:
                    metadata['error'] = str(error)
                    metadata['error_type'] = type(error).__name__

                # 记录性能指标
                performance_metrics.record_metric(
                    operation_name,
                    duration,
                    success,
                    metadata
                )

                # 日志记录
                if success:
                    if log_slow_calls and duration > slow_threshold:
                        logger.warning(f"{operation_name} 慢调用: {duration:.2f}s (阈值: {slow_threshold}s)")
                    else:
                        logger.info(f"{operation_name} 成功: {duration:.2f}s")
                else:
                    logger.error(f"{operation_name} 失败: {duration:.2f}s, 错误: {error}")

        return wrapper
    return decorator


class PerformanceContext:
    """性能监控上下文管理器"""

    def __init__(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        初始化性能监控上下文

        Args:
            operation_name: 操作名称
            metadata: 附加元数据
        """
        self.operation_name = operation_name
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type is not None:
            self.success = False
            self.metadata['error'] = str(exc_val)
            self.metadata['error_type'] = exc_type.__name__
            self.metadata['traceback'] = traceback.format_exc()

        performance_metrics.record_metric(
            self.operation_name,
            duration,
            self.success,
            self.metadata
        )

        if self.success:
            logger.info(f"{self.operation_name} 上下文成功: {duration:.2f}s")
        else:
            logger.error(f"{self.operation_name} 上下文失败: {duration:.2f}s")


def get_performance_report(operation: Optional[str] = None) -> Dict[str, Any]:
    """
    获取性能报告

    Args:
        operation: 特定操作名称

    Returns:
        性能报告
    """
    return performance_metrics.get_stats(operation)


def reset_metrics():
    """重置性能指标"""
    global performance_metrics
    performance_metrics = PerformanceMetrics()
    logger.info("性能指标已重置")


def get_monitor():
    """获取监控实例"""
    return performance_metrics
