"""
IP智慧解答专家系统 - 任务监控器

本模块提供任务监控和重试机制，确保异步任务的可靠执行。
"""

import logging
import traceback
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional
from rq import get_current_job, Retry
from flask import current_app

logger = logging.getLogger(__name__)


class TaskMonitor:
    """任务监控器"""

    @staticmethod
    def monitor_task_progress(func: Callable) -> Callable:
        """
        任务进度监控装饰器

        Args:
            func: 要监控的任务函数

        Returns:
            Callable: 包装后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            job = get_current_job()
            task_name = func.__name__

            if job:
                job.meta['status'] = 'running'
                job.meta['started_at'] = str(job.started_at) if job.started_at else None
                job.meta['function_name'] = task_name
                job.save_meta()
                logger.info(f"任务开始执行: {task_name} (Job ID: {job.id})")

            try:
                # 执行原始函数
                result = func(*args, **kwargs)

                if job:
                    job.meta['status'] = 'completed'
                    job.meta['completed_at'] = str(job.ended_at) if job.ended_at else None
                    job.save_meta()

                logger.info(f"任务执行成功: {task_name} (Job ID: {job.id if job else 'N/A'})")
                return result

            except Exception as e:
                if job:
                    job.meta['status'] = 'failed'
                    job.meta['error'] = str(e)
                    job.meta['error_traceback'] = traceback.format_exc()
                    job.save_meta()

                logger.error(f"任务执行失败: {task_name} - {str(e)}")
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                raise

        return wrapper

    @staticmethod
    def retry_on_failure(max_retries: int = 3, retry_intervals: list = None) -> Callable:
        """
        失败重试装饰器

        Args:
            max_retries: 最大重试次数
            retry_intervals: 重试间隔时间列表（秒）

        Returns:
            Callable: 装饰器函数
        """
        if retry_intervals is None:
            retry_intervals = [10, 30, 60]  # 默认重试间隔

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                job = get_current_job()

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if job:
                        # 获取当前重试次数
                        current_retry = getattr(job, 'retries_left', None)
                        if current_retry is None:
                            current_retry = max_retries
                        retry_count = max_retries - current_retry

                        if retry_count < max_retries:
                            # 计算重试间隔
                            interval_index = min(retry_count, len(retry_intervals) - 1)
                            retry_interval = retry_intervals[interval_index]

                            logger.warning(
                                f"任务执行失败，将在 {retry_interval} 秒后重试 "
                                f"(第 {retry_count + 1}/{max_retries} 次重试): {str(e)}"
                            )

                            # 更新任务元数据
                            job.meta['retry_count'] = retry_count + 1
                            job.meta['last_error'] = str(e)
                            job.save_meta()

                            # 抛出RQ重试异常
                            raise Retry()

                    # 最终失败，不再重试
                    logger.error(f"任务最终失败，已达到最大重试次数: {str(e)}")
                    raise

            return wrapper
        return decorator

    @staticmethod
    def get_task_status(job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            job_id: 任务ID

        Returns:
            Dict: 任务状态信息
        """
        try:
            from app.services import get_redis_connection
            from rq.job import Job

            redis_conn = get_redis_connection()
            job = Job.fetch(job_id, connection=redis_conn)

            if not job:
                return None

            status_info = {
                'id': job.id,
                'status': job.get_status(),
                'created_at': str(job.created_at) if job.created_at else None,
                'started_at': str(job.started_at) if job.started_at else None,
                'ended_at': str(job.ended_at) if job.ended_at else None,
                'result': job.result,
                'exc_info': job.exc_info,
                'meta': job.meta
            }

            return status_info

        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}")
            return None

    @staticmethod
    def cancel_task(job_id: str) -> bool:
        """
        取消任务

        Args:
            job_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        try:
            from app.services import get_redis_connection
            from rq.job import Job

            redis_conn = get_redis_connection()
            job = Job.fetch(job_id, connection=redis_conn)

            if job and job.get_status() in ['queued', 'started']:
                job.cancel()
                logger.info(f"任务已取消: {job_id}")
                return True
            else:
                logger.warning(f"无法取消任务，任务不存在或已完成: {job_id}")
                return False

        except Exception as e:
            logger.error(f"取消任务失败: {str(e)}")
            return False

    @staticmethod
    def get_queue_stats() -> Dict[str, Any]:
        """
        获取队列统计信息

        Returns:
            Dict: 队列统计信息
        """
        try:
            from app.services import get_task_queue, get_redis_connection
            from rq import Worker

            queue = get_task_queue()
            redis_conn = get_redis_connection()
            workers = Worker.all(connection=redis_conn)

            stats = {
                'queue_length': len(queue),
                'workers_count': len(workers),
                'workers': [],
                'failed_jobs_count': queue.failed_job_registry.count,
                'scheduled_jobs_count': queue.scheduled_job_registry.count,
                'started_jobs_count': queue.started_job_registry.count,
                'deferred_jobs_count': queue.deferred_job_registry.count
            }

            # 获取worker详细信息
            for worker in workers:
                worker_info = {
                    'name': worker.name,
                    'state': worker.get_state(),
                    'current_job': worker.get_current_job_id(),
                    'successful_jobs': worker.successful_job_count,
                    'failed_jobs': worker.failed_job_count,
                    'total_working_time': worker.total_working_time
                }
                stats['workers'].append(worker_info)

            return stats

        except Exception as e:
            logger.error(f"获取队列统计信息失败: {str(e)}")
            return {
                'error': str(e),
                'queue_length': 0,
                'workers_count': 0,
                'workers': []
            }

    @staticmethod
    def cleanup_failed_jobs(max_age_hours: int = 24) -> int:
        """
        清理失败的任务

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            int: 清理的任务数量
        """
        try:
            from app.services import get_task_queue
            from datetime import datetime, timedelta

            queue = get_task_queue()
            failed_registry = queue.failed_job_registry

            # 获取所有失败任务
            failed_job_ids = failed_registry.get_job_ids()
            cleaned_count = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            for job_id in failed_job_ids:
                try:
                    from rq.job import Job
                    job = Job.fetch(job_id, connection=queue.connection)

                    if job and job.ended_at and job.ended_at < cutoff_time:
                        failed_registry.remove(job_id)
                        cleaned_count += 1

                except Exception as e:
                    logger.warning(f"清理失败任务时出错 {job_id}: {str(e)}")
                    continue

            logger.info(f"清理了 {cleaned_count} 个过期的失败任务")
            return cleaned_count

        except Exception as e:
            logger.error(f"清理失败任务时出错: {str(e)}")
            return 0


# 便捷的装饰器函数
def monitor_progress(func):
    """进度监控装饰器（便捷函数）"""
    return TaskMonitor.monitor_task_progress(func)


def retry_on_failure(max_retries: int = 3, retry_intervals: list = None):
    """重试装饰器（便捷函数）"""
    return TaskMonitor.retry_on_failure(max_retries, retry_intervals)


def with_monitoring_and_retry(max_retries: int = 3, retry_intervals: list = None):
    """
    组合装饰器：同时添加监控和重试功能

    Args:
        max_retries: 最大重试次数
        retry_intervals: 重试间隔时间列表

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        # 先应用重试装饰器，再应用监控装饰器
        func = retry_on_failure(max_retries, retry_intervals)(func)
        func = monitor_progress(func)
        return func
    return decorator
