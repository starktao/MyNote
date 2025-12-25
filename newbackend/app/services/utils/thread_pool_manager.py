"""
线程池管理器
负责管理多节点多层并发处理的线程池资源
"""

import threading
import time
import psutil
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
import logging
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ThreadPoolManager:
    """线程池管理器，负责管理四级线程池"""

    def __init__(self):
        """初始化线程池管理器"""
        # 节点级线程池：处理多个时间点节点
        self.node_executor = ThreadPoolExecutor(
            max_workers=settings.MAX_CONCURRENT_NODES,
            thread_name_prefix="NodeProcessor"
        )

        # 图片级线程池：并发处理单节点的多张图片
        self.image_executor = ThreadPoolExecutor(
            max_workers=settings.MAX_CONCURRENT_IMAGES,
            thread_name_prefix="ImageProcessor"
        )

        # 操作级线程池：具体操作并发（OCR、编码等）
        self.operation_executor = ThreadPoolExecutor(
            max_workers=settings.MAX_CONCURRENT_OPERATIONS,
            thread_name_prefix="OperationProcessor"
        )

        # OCR专用线程池：OCR操作可能有不同需求
        self.ocr_executor = ThreadPoolExecutor(
            max_workers=settings.OCR_MAX_WORKERS,
            thread_name_prefix="OCRProcessor"
        )

        # 统计信息
        self.stats = {
            'node_tasks': 0,
            'image_tasks': 0,
            'operation_tasks': 0,
            'ocr_tasks': 0,
            'total_submitted': 0,
            'total_completed': 0,
            'start_time': time.time()
        }

        # 线程池状态跟踪
        self._pool_status = {}
        self._lock = threading.Lock()

        logger.info("线程池管理器初始化完成")
        logger.info(f"  节点级线程池: {settings.MAX_CONCURRENT_NODES} 个工作线程")
        logger.info(f"  图片级线程池: {settings.MAX_CONCURRENT_IMAGES} 个工作线程")
        logger.info(f"  操作级线程池: {settings.MAX_CONCURRENT_OPERATIONS} 个工作线程")
        logger.info(f"  OCR线程池: {settings.OCR_MAX_WORKERS} 个工作线程")

    def get_node_executor(self) -> ThreadPoolExecutor:
        """获取节点级线程池"""
        with self._lock:
            self.stats['node_tasks'] += 1
            self.stats['total_submitted'] += 1
        return self.node_executor

    def get_image_executor(self) -> ThreadPoolExecutor:
        """获取图片级线程池"""
        with self._lock:
            self.stats['image_tasks'] += 1
            self.stats['total_submitted'] += 1
        return self.image_executor

    def get_operation_executor(self) -> ThreadPoolExecutor:
        """获取操作级线程池"""
        with self._lock:
            self.stats['operation_tasks'] += 1
            self.stats['total_submitted'] += 1
        return self.operation_executor

    def get_ocr_executor(self) -> ThreadPoolExecutor:
        """获取OCR专用线程池"""
        with self._lock:
            self.stats['ocr_tasks'] += 1
            self.stats['total_submitted'] += 1
        return self.ocr_executor

    def get_pool_status(self) -> Dict[str, Any]:
        """获取所有线程池的状态信息"""
        try:
            pools = [
                ('node', self.node_executor, settings.MAX_CONCURRENT_NODES),
                ('image', self.image_executor, settings.MAX_CONCURRENT_IMAGES),
                ('operation', self.operation_executor, settings.MAX_CONCURRENT_OPERATIONS),
                ('ocr', self.ocr_executor, settings.OCR_MAX_WORKERS)
            ]

            status = {}
            total_threads = 0
            total_active = 0

            for pool_name, executor, max_workers in pools:
                try:
                    # 获取线程池状态
                    active_threads = len([t for t in threading.enumerate()
                                         if t.name and executor._thread_name_prefix in t.name and t.is_alive()])

                    # 估算队列中的任务数（简化计算）
                    pending_tasks = max(0, max_workers - active_threads)

                    pool_status = {
                        'name': pool_name,
                        'max_workers': max_workers,
                        'active_threads': active_threads,
                        'pending_tasks': pending_tasks,
                        'utilization': round(active_threads / max_workers * 100, 1) if max_workers > 0 else 0
                    }

                    status[pool_name] = pool_status
                    total_threads += max_workers
                    total_active += active_threads

                except Exception as e:
                    logger.error(f"获取线程池状态失败 {pool_name}: {e}")
                    status[pool_name] = {
                        'name': pool_name,
                        'error': str(e),
                        'max_workers': max_workers
                    }

            # 系统资源信息
            system_info = self._get_system_info()

            # 总体统计
            overall_stats = {
                'total_threads': total_threads,
                'total_active': total_active,
                'overall_utilization': round(total_active / total_threads * 100, 1) if total_threads > 0 else 0,
                'system_info': system_info,
                'task_stats': self._get_task_stats()
            }

            return {
                'pools': status,
                'overall': overall_stats,
                'timestamp': time.time()
            }

        except Exception as e:
            logger.error(f"获取线程池状态失败: {e}")
            return {'error': str(e), 'timestamp': time.time()}

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统资源信息"""
        try:
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)

            # 内存信息
            memory = psutil.virtual_memory()
            memory_used_mb = round(memory.used / 1024 / 1024, 2)
            memory_total_mb = round(memory.total / 1024 / 1024, 2)
            memory_percent = memory.percent

            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count_physical': cpu_count,
                    'count_logical': cpu_count_logical
                },
                'memory': {
                    'used_mb': memory_used_mb,
                    'total_mb': memory_total_mb,
                    'percent': memory_percent
                }
            }

        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {'error': str(e)}

    def _get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        with self._lock:
            current_time = time.time()
            runtime = current_time - self.stats['start_time']

            completion_rate = 0
            if self.stats['total_submitted'] > 0:
                completion_rate = self.stats['total_completed'] / self.stats['total_submitted'] * 100

            throughput = 0
            if runtime > 0:
                throughput = self.stats['total_completed'] / runtime

            return {
                'total_submitted': self.stats['total_submitted'],
                'total_completed': self.stats['total_completed'],
                'completion_rate': round(completion_rate, 1),
                'throughput_per_second': round(throughput, 2),
                'runtime_seconds': round(runtime, 1),
                'node_tasks': self.stats['node_tasks'],
                'image_tasks': self.stats['image_tasks'],
                'operation_tasks': self.stats['operation_tasks'],
                'ocr_tasks': self.stats['ocr_tasks']
            }

    def mark_task_completed(self):
        """标记任务完成"""
        with self._lock:
            self.stats['total_completed'] += 1

    def submit_node_task(self, fn, *args, **kwargs):
        """提交节点级任务"""
        future = self.get_node_executor().submit(fn, *args, **kwargs)
        logger.debug(f"提交节点级任务: {fn.__name__}")
        return future

    def submit_image_task(self, fn, *args, **kwargs):
        """提交图片级任务"""
        future = self.get_image_executor().submit(fn, *args, **kwargs)
        logger.debug(f"提交图片级任务: {fn.__name__}")
        return future

    def submit_operation_task(self, fn, *args, **kwargs):
        """提交操作级任务"""
        future = self.get_operation_executor().submit(fn, *args, **kwargs)
        logger.debug(f"提交操作级任务: {fn.__name__}")
        return future

    def submit_ocr_task(self, fn, *args, **kwargs):
        """提交OCR任务"""
        future = self.get_ocr_executor().submit(fn, *args, **kwargs)
        logger.debug(f"提交OCR任务: {fn.__name__}")
        return future

    def shutdown(self, wait: bool = True, timeout: float = 30.0):
        """关闭所有线程池"""
        logger.info("开始关闭线程池管理器")

        try:
            # 优雅关闭各个线程池
            pools = [
                ('node', self.node_executor),
                ('image', self.image_executor),
                ('operation', self.operation_executor),
                ('ocr', self.ocr_executor)
            ]

            for pool_name, executor in pools:
                try:
                    logger.info(f"关闭 {pool_name} 线程池...")
                    # 兼容性处理：某些Python版本不支持timeout参数
                    if hasattr(executor, 'shutdown') and timeout:
                        try:
                            executor.shutdown(wait=wait, timeout=timeout)
                        except TypeError:
                            # 如果不支持timeout参数，则使用默认值
                            executor.shutdown(wait=wait)
                    else:
                        executor.shutdown(wait=wait)
                    logger.info(f"{pool_name} 线程池关闭完成")
                except Exception as e:
                    logger.error(f"关闭 {pool_name} 线程池失败: {e}")

            logger.info("线程池管理器关闭完成")

        except Exception as e:
            logger.error(f"关闭线程池管理器失败: {e}")

    def optimize_pool_sizes(self):
        """根据系统资源动态优化线程池大小"""
        try:
            system_info = self._get_system_info()
            if 'error' in system_info:
                logger.warning("无法获取系统信息，跳过优化")
                return

            cpu_percent = system_info['cpu']['percent']
            memory_percent = system_info['memory']['percent']

            current_status = self.get_pool_status()
            overall_util = current_status.get('overall', {}).get('overall_utilization', 0)

            # 基于CPU和内存使用率调整
            if cpu_percent > 80 or memory_percent > 80:
                # 高负载时减少并发
                logger.info(f"系统负载较高(CPU:{cpu_percent}%, 内存:{memory_percent}%), 考虑减少并发")
            elif overall_util < 50 and cpu_percent < 50:
                # 低负载时可以考虑增加并发
                logger.info(f"系统负载较低(CPU:{cpu_percent}%, 利用率:{overall_util}%), 可以考虑增加并发")

        except Exception as e:
            logger.error(f"优化线程池大小失败: {e}")

    def get_recommendations(self) -> Dict[str, Any]:
        """获取性能优化建议"""
        try:
            status = self.get_pool_status()
            system_info = status.get('overall', {}).get('system_info', {})
            overall = status.get('overall', {})

            recommendations = []

            # CPU使用率建议
            cpu_percent = system_info.get('cpu', {}).get('percent', 0)
            if cpu_percent > 80:
                recommendations.append("CPU使用率过高，建议减少并发线程数")
            elif cpu_percent < 30:
                recommendations.append("CPU使用率较低，可以适当增加并发线程数")

            # 内存使用率建议
            memory_percent = system_info.get('memory', {}).get('percent', 0)
            if memory_percent > 80:
                recommendations.append("内存使用率过高，建议减少OCR线程池大小")
            elif memory_percent < 50:
                recommendations.append("内存使用率较低，可以适当增加并发线程数")

            # 线程池利用率建议
            overall_util = overall.get('overall_utilization', 0)
            if overall_util > 90:
                recommendations.append("线程池利用率过高，建议增加线程池大小")
            elif overall_util < 30:
                recommendations.append("线程池利用率较低，可以考虑减少线程池大小")

            # 任务完成率建议
            completion_rate = overall.get('task_stats', {}).get('completion_rate', 0)
            if completion_rate < 80:
                recommendations.append("任务完成率较低，可能存在超时或错误")

            return {
                'recommendations': recommendations,
                'priority': len(recommendations),
                'status': '需要优化' if len(recommendations) > 2 else '正常',
                'current_status': status
            }

        except Exception as e:
            logger.error(f"获取性能建议失败: {e}")
            return {'error': str(e)}


def create_thread_pool_manager() -> ThreadPoolManager:
    """创建线程池管理器实例"""
    manager = ThreadPoolManager()
    logger.info("线程池管理器实例创建完成")
    return manager