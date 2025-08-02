"""
性能监控工具

本模块实现了LLM服务的性能监控和指标收集。
"""

import time
import logging
import functools
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, max_records: int = 1000):
        """
        初始化性能监控器

        Args:
            max_records: 最大记录数量
        """
        self.max_records = max_records
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.errors = deque(maxlen=100)  # 保留最近100个错误
        self.lock = Lock()

        logger.info("性能监控器初始化完成")

    def record_operation(self, operation: str, duration: float,
                        success: bool = True, metadata: Dict = None):
        """
        记录操作性能

        Args:
            operation: 操作名称
            duration: 持续时间（秒）
            success: 是否成功
            metadata: 附加元数据
        """
        with self.lock:
            record = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "duration": duration,
                "success": success,
                "metadata": metadata or {}
            }

            # 记录指标
            self.metrics[operation].append(record)

            # 限制记录数量
            if len(self.metrics[operation]) > self.max_records:
                self.metrics[operation].pop(0)

            # 更新计数器
            self.counters[f"{operation}_total"] += 1
            if success:
                self.counters[f"{operation}_success"] += 1
            else:
                self.counters[f"{operation}_error"] += 1

    def record_error(self, operation: str, error: str, metadata: Dict = None):
        """
        记录错误信息

        Args:
            operation: 操作名称
            error: 错误信息
            metadata: 附加元数据
        """
        with self.lock:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "error": error,
                "metadata": metadata or {}
            }
            self.errors.append(error_record)

    def get_operation_stats(self, operation: str,
                           time_window: int = 3600) -> Dict[str, Any]:
        """
        获取操作统计信息

        Args:
            operation: 操作名称
            time_window: 时间窗口（秒）

        Returns:
            统计信息
        """
        with self.lock:
            records = self.metrics.get(operation, [])

            if not records:
                return {
                    "operation": operation,
                    "total_count": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "success_rate": 0.0,
                    "avg_duration": 0.0,
                    "min_duration": 0.0,
                    "max_duration": 0.0,
                    "p95_duration": 0.0
                }

            # 过滤时间窗口内的记录
            cutoff_time = datetime.now() - timedelta(seconds=time_window)
            filtered_records = [
                r for r in records
                if datetime.fromisoformat(r["timestamp"]) > cutoff_time
            ]

            if not filtered_records:
                return self.get_operation_stats(operation, time_window * 2)

            # 计算统计信息
            total_count = len(filtered_records)
            success_count = sum(1 for r in filtered_records if r["success"])
            error_count = total_count - success_count
            success_rate = success_count / total_count if total_count > 0 else 0.0

            durations = [r["duration"] for r in filtered_records]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            min_duration = min(durations) if durations else 0.0
            max_duration = max(durations) if durations else 0.0

            # 计算P95
            sorted_durations = sorted(durations)
            p95_index = int(len(sorted_durations) * 0.95)
            p95_duration = sorted_durations[p95_index] if sorted_durations else 0.0

            return {
                "operation": operation,
                "time_window": time_window,
                "total_count": total_count,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": round(success_rate, 4),
                "avg_duration": round(avg_duration, 4),
                "min_duration": round(min_duration, 4),
                "max_duration": round(max_duration, 4),
                "p95_duration": round(p95_duration, 4)
            }

    def get_all_stats(self, time_window: int = 3600) -> Dict[str, Any]:
        """
        获取所有操作的统计信息

        Args:
            time_window: 时间窗口（秒）

        Returns:
            所有统计信息
        """
        with self.lock:
            operations = list(self.metrics.keys())
            stats = {}

            for operation in operations:
                stats[operation] = self.get_operation_stats(operation, time_window)

            # 获取最近的错误
            recent_errors = list(self.errors)[-10:]  # 最近10个错误

            return {
                "timestamp": datetime.now().isoformat(),
                "time_window": time_window,
                "operations": stats,
                "recent_errors": recent_errors,
                "total_operations": len(operations)
            }

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取健康状态

        Returns:
            健康状态信息
        """
        with self.lock:
            stats = self.get_all_stats(300)  # 5分钟窗口

            # 计算整体健康分数
            total_success_rate = 0.0
            total_operations = 0
            high_error_operations = []
            slow_operations = []

            for op_name, op_stats in stats["operations"].items():
                if op_stats["total_count"] > 0:
                    total_success_rate += op_stats["success_rate"]
                    total_operations += 1

                    # 检查错误率
                    if op_stats["success_rate"] < 0.9:  # 成功率低于90%
                        high_error_operations.append({
                            "operation": op_name,
                            "success_rate": op_stats["success_rate"],
                            "error_count": op_stats["error_count"]
                        })

                    # 检查响应时间
                    if op_stats["avg_duration"] > 10.0:  # 平均响应时间超过10秒
                        slow_operations.append({
                            "operation": op_name,
                            "avg_duration": op_stats["avg_duration"],
                            "p95_duration": op_stats["p95_duration"]
                        })

            overall_success_rate = total_success_rate / total_operations if total_operations > 0 else 1.0

            # 确定健康状态
            if overall_success_rate >= 0.95 and not slow_operations:
                health_status = "healthy"
            elif overall_success_rate >= 0.8:
                health_status = "warning"
            else:
                health_status = "critical"

            return {
                "status": health_status,
                "overall_success_rate": round(overall_success_rate, 4),
                "total_operations": total_operations,
                "high_error_operations": high_error_operations,
                "slow_operations": slow_operations,
                "recent_error_count": len(self.errors),
                "timestamp": datetime.now().isoformat()
            }


# 全局监控器实例
_monitor = None

def get_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def monitor_performance(operation_name: str, include_args: bool = False):
    """
    性能监控装饰器

    Args:
        operation_name: 操作名称
        include_args: 是否在元数据中包含参数信息
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            start_time = time.time()
            success = True
            error_msg = None
            metadata = {}

            try:
                # 记录参数信息（如果需要）
                if include_args:
                    metadata["args_count"] = len(args)
                    metadata["kwargs_keys"] = list(kwargs.keys())

                result = func(*args, **kwargs)

                # 检查结果中是否有错误
                if isinstance(result, dict) and "error" in result:
                    success = False
                    error_msg = result.get("error", "Unknown error")

                return result

            except Exception as e:
                success = False
                error_msg = str(e)
                logger.error(f"{operation_name} 执行失败: {error_msg}")
                raise

            finally:
                duration = time.time() - start_time

                # 记录性能指标
                monitor.record_operation(
                    operation=operation_name,
                    duration=duration,
                    success=success,
                    metadata=metadata
                )

                # 记录错误
                if not success and error_msg:
                    monitor.record_error(
                        operation=operation_name,
                        error=error_msg,
                        metadata=metadata
                    )

                # 记录日志
                if success:
                    logger.info(f"{operation_name} 执行成功，耗时: {duration:.2f}秒")
                else:
                    logger.error(f"{operation_name} 执行失败，耗时: {duration:.2f}秒，错误: {error_msg}")

        return wrapper
    return decorator


def log_slow_queries(threshold: float = 5.0):
    """
    慢查询日志装饰器

    Args:
        threshold: 慢查询阈值（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            if duration > threshold:
                logger.warning(
                    f"慢操作检测: {func.__name__} 耗时 {duration:.2f}秒 "
                    f"(阈值: {threshold}秒)"
                )

            return result
        return wrapper
    return decorator
