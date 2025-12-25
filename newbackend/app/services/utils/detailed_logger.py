"""
详细日志记录器
专门用于后台流程观察的完整日志记录
基于计划中的详细日志格式实现
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DetailedLogger:
    """详细日志记录器 - 专门用于后台流程观察"""

    def __init__(self):
        """初始化详细日志记录器"""
        self.enabled = settings.LOG_STRATEGY_CALLS
        self.log_performance = settings.LOG_PERFORMANCE_METRICS
        self.log_errors = settings.LOG_ERROR_DETAILS
        self.log_thread_pool = settings.LOG_THREAD_POOL_STATUS

        if self.enabled:
            logger.info("详细日志记录器初始化完成")
            logger.info(f"  策略调用日志: {self.enabled}")
            logger.info(f"  性能指标日志: {self.log_performance}")
            logger.info(f"  错误详情日志: {self.log_errors}")
            logger.info(f"  线程池状态日志: {self.log_thread_pool}")

    def log_processing_start(self, task_id: str, candidate_count: int, provider_config: Dict[str, Any]):
        """记录处理开始"""
        if not self.enabled:
            return

        logger.info("=" * 80)
        logger.info("开始多节点并发智能截图选择处理")
        logger.info("任务ID: %s", task_id)
        logger.info("候选截图总数: %d", candidate_count)
        logger.info("AI模型: %s (%s)",
                   provider_config.get('model_name', 'unknown'),
                   provider_config.get('id', 'unknown'))
        logger.info("线程池配置: 节点级=%d, 图片级=%d, 操作级=%d, OCR=%d",
                   settings.MAX_CONCURRENT_NODES,
                   settings.MAX_CONCURRENT_IMAGES,
                   settings.MAX_CONCURRENT_OPERATIONS,
                   settings.OCR_MAX_WORKERS)

        # 记录处理配置
        logger.info("处理配置:")
        logger.info("  智能截图选择: %s", settings.INTELLIGENT_SCREENSHOT_ENABLED)
        logger.info("  能力缓存TTL: %d秒", settings.CAPABILITY_CACHE_TTL)
        logger.info("  多模态超时: %d秒", settings.MULTIMODAL_TIMEOUT)
        logger.info("  OCR处理超时: %d秒", settings.OCR_PROCESSING_TIMEOUT)
        logger.info("  图像最大尺寸: %d像素", settings.IMAGE_MAX_SIZE)

    def log_node_processing_start(self, timepoint_nodes: List[Dict[str, Any]]):
        """记录多节点处理开始"""
        if not self.enabled:
            return

        logger.info("-" * 60)
        logger.info("开始多节点并发处理")
        logger.info("时间点节点数量: %d", len(timepoint_nodes))

        for i, node in enumerate(timepoint_nodes):
            node_id = node.get('node_id', f'node_{i+1}')
            image_count = len(node.get('image_paths', []))
            timestamp = node.get('timestamp', 'unknown')

            logger.info("  节点%d: %s (时间点: %s, 图片数量: %d)",
                       i+1, node_id, timestamp, image_count)

    def log_single_node_start(self, node_id: str, image_count: int, strategy: str = None):
        """记录单个节点处理开始"""
        if not self.enabled:
            return

        logger.info("开始处理节点: %s, 图片数量: %d", node_id, image_count)
        if strategy:
            logger.info("节点%s - 使用策略: %s", node_id, strategy)

        if self.log_thread_pool:
            # 记录线程池状态
            logger.info("节点%s - 线程池状态检查", node_id)

    def log_strategy_execution(self, node_id: str, strategy_name: str, start_time: float):
        """记录策略执行开始"""
        if not self.enabled:
            return

        logger.info("节点%s - 执行策略: %s", node_id, strategy_name)
        logger.info("节点%s - 策略开始时间: %s",
                   node_id,
                   time.strftime('%H:%M:%S', time.localtime(start_time)))

        if self.log_performance:
            logger.info("节点%s - 执行策略开始时间戳: %.2f", node_id, start_time)

    def log_capability_detection(self, node_id: str, provider_config: Dict[str, Any], result: Dict[str, Any]):
        """记录模型能力检测"""
        if not self.enabled:
            return

        logger.info("节点%s - 模型能力检测完成", node_id)
        logger.info("节点%s - 模型: %s", node_id, provider_config.get('model_name', 'unknown'))
        logger.info("节点%s - 能力检测结果: %s",
                   node_id,
                   str(result.get('supports_images', False)))

        if self.log_performance:
            detection_time = result.get('detection_time', 0)
            logger.info("节点%s - 检测耗时: %.2f秒", node_id, detection_time)

        if self.log_errors and 'error' in result:
            logger.error("节点%s - 检测错误: %s", node_id, result['error'])

    def log_image_encoding_progress(self, node_id: str, total_images: int, encoded_count: int, current_image: str = None):
        """记录图像编码进度"""
        if not self.enabled:
            return

        logger.info("节点%s - 图像编码进度: %d/%d", node_id, encoded_count, total_images)

        if current_image:
            logger.info("节点%s - 当前编码: %s", node_id, os.path.basename(current_image))

        if encoded_count == total_images:
            logger.info("节点%s - 所有图像编码完成", node_id)

    def log_multimodal_processing(self, node_id: str, image_count: int, api_start_time: float, api_end_time: float, api_response_length: int = None):
        """记录多模态AI处理"""
        if not self.enabled:
            return

        api_duration = api_end_time - api_start_time
        logger.info("节点%s - 多模态AI处理开始", node_id)
        logger.info("节点%s - 处理图片数量: %d", node_id, image_count)
        logger.info("节点%s - API调用耗时: %.2f秒", node_id, api_duration)
        logger.info("节点%s - API调用时间: %s -> %s",
                   node_id,
                   time.strftime('%H:%M:%S', time.localtime(api_start_time)),
                   time.strftime('%H:%M:%S', time.localtime(api_end_time)))

        if api_response_length is not None:
            logger.info("节点%s - AI响应长度: %d字符", node_id, api_response_length)

        if self.log_performance:
            # 性能指标
            throughput = image_count / api_duration if api_duration > 0 else 0
            logger.info("节点%s - 处理吞吐量: %.2f图片/秒", node_id, throughput)

    def log_ocr_fallback_start(self, node_id: str, image_count: int):
        """记录OCR降级处理开始"""
        if not self.enabled:
            return

        logger.info("节点%s - 启动OCR降级处理", node_id)
        logger.info("节点%s - OCR处理图片数量: %d", node_id, image_count)
        logger.info("节点%s - OCR线程池: 工作线程数=%d", node_id, settings.OCR_MAX_WORKERS)

    def log_ocr_progress(self, node_id: str, completed_count: int, total_count: int, current_image: str, processing_time: float = None):
        """记录OCR处理进度"""
        if not self.enabled:
            return

        progress_percent = (completed_count / total_count * 100) if total_count > 0 else 0
        logger.info("节点%s - OCR进度: %d/%d (%.1f%%), 当前处理: %s",
                   node_id,
                   completed_count,
                   total_count,
                   progress_percent,
                   os.path.basename(current_image))

        if processing_time is not None and self.log_performance:
            logger.info("节点%s - 当前图片处理时间: %.2f秒", node_id, processing_time)

    def log_single_image_result(self, node_id: str, image_path: str, strategy: str, success: bool, processing_time: float, **kwargs):
        """记录单张图片处理结果"""
        if not self.enabled:
            return

        image_name = os.path.basename(image_path)
        logger.info("节点%s - 图片处理结果: %s", node_id, image_name)
        logger.info("节点%s - 处理策略: %s", node_id, strategy)
        logger.info("节点%s - 处理状态: %s", node_id, "成功" if success else "失败")
        logger.info("节点%s - 处理耗时: %.2f秒", node_id, processing_time)

        if success:
            if strategy == "multimodal_ai":
                response_length = kwargs.get('response_length', 0)
                logger.info("节点%s - AI响应长度: %d字符", node_id, response_length)

                if response_length > 0 and self.log_performance:
                    throughput = response_length / processing_time if processing_time > 0 else 0
                    logger.info("节点%s - 处理吞吐量: %.1f字符/秒", node_id, throughput)

            elif strategy == "ocr_fallback":
                text_length = kwargs.get('text_length', 0)
                confidence = kwargs.get('confidence', 0)
                info_score = kwargs.get('info_score', 0)
                detections = kwargs.get('detections', 0)

                logger.info("节点%s - 识别文本长度: %d字符", node_id, text_length)
                logger.info("节点%s - OCR置信度: %.3f", node_id, confidence)
                logger.info("节点%s - 信息评分: %.3f", node_id, info_score)
                logger.info("节点%s - 检测区域: %d个", node_id, detections)

                if text_length > 0 and self.log_performance:
                    throughput = text_length / processing_time if processing_time > 0 else 0
                    logger.info("节点%s - OCR吞吐量: %.1f字符/秒", node_id, throughput)

        else:
            if self.log_errors:
                logger.error("节点%s - 失败原因: %s", node_id, kwargs.get('error', '未知错误'))

    def log_node_completion(self, node_id: str, best_image: str, total_processing_time: float, strategy_used: str, success: bool = True):
        """记录节点处理完成"""
        if not self.enabled:
            return

        logger.info("节点%s - 处理完成", node_id)
        logger.info("节点%s - 处理状态: %s", node_id, "成功" if success else "失败")

        if best_image:
            logger.info("节点%s - 最佳图片: %s", node_id, os.path.basename(best_image))
        else:
            logger.warning("节点%s - 无最佳图片选择", node_id)

        logger.info("节点%s - 使用策略: %s", node_id, strategy_used)
        logger.info("节点%s - 总耗时: %.2f秒", node_id, total_processing_time)

        if self.log_performance:
            logger.info("节点%s - 处理完成时间: %s",
                       node_id,
                       time.strftime('%H:%M:%S', time.localtime(time.time())))

    def log_all_nodes_completion(self, node_results: List[Dict[str, Any]]):
        """记录所有节点处理完成"""
        if not self.enabled:
            return

        logger.info("-" * 60)
        logger.info("所有节点处理完成")

        successful_nodes = [r for r in node_results if r.get('success', False)]
        failed_nodes = [r for r in node_results if not r.get('success', False)]

        logger.info("成功节点数: %d/%d", len(successful_nodes), len(node_results))
        logger.info("失败节点数: %d/%d", len(failed_nodes), len(node_results))

        if successful_nodes:
            total_time = sum(r.get('processing_time', 0) for r in successful_nodes)
            avg_time = total_time / len(successful_nodes) if successful_nodes else 0
            logger.info("平均处理时间: %.2f秒", avg_time)

        # 详细节点结果
        for i, result in enumerate(node_results):
            status = "成功" if result.get('success', False) else "失败"
            node_id = result.get('node_id', f'node_{i+1}')
            processing_time = result.get('processing_time', 0)
            strategy = result.get('strategy_used', 'unknown')

            logger.info("  节点%d %s: %s (%.2fs, %s)",
                       i+1, node_id, status, processing_time, strategy)

        if failed_nodes and self.log_errors:
            logger.warning("失败节点详情:")
            for result in failed_nodes:
                node_id = result.get('node_id', 'unknown')
                error = result.get('error', '未知错误')
                logger.warning("  节点%s - 失败原因: %s", node_id, error)

    def log_final_result(self, task_id: str, final_result: Dict[str, Any], total_time: float):
        """记录最终处理结果"""
        if not self.enabled:
            return

        logger.info("=" * 60)
        logger.info("最终处理结果")
        logger.info("任务ID: %s", task_id)
        logger.info("总处理时间: %.2f秒", total_time)

        selected_image = final_result.get('selected_image')
        if selected_image:
            logger.info("选择结果: %s", os.path.basename(selected_image))
        else:
            logger.warning("无选择结果")

        strategy_used = final_result.get('strategy_used', 'unknown')
        logger.info("处理策略: %s", strategy_used)

        success_rate = final_result.get('success_rate', 0)
        logger.info("成功率: %.1f%%", success_rate * 100)

        if self.log_performance:
            # 性能统计
            nodes_processed = final_result.get('nodes_processed', 0)
            images_processed = final_result.get('images_processed', 0)
            if total_time > 0:
                nodes_per_second = nodes_processed / total_time
                images_per_second = images_processed / total_time
                logger.info("节点处理速度: %.2f节点/秒", nodes_per_second)
                logger.info("图像处理速度: %.2f图像/秒", images_per_second)

    def log_thread_pool_status(self, pool_status: Dict[str, Any]):
        """记录线程池状态"""
        if not self.enabled or not self.log_thread_pool:
            return

        try:
            logger.info("线程池状态报告:")

            pools = pool_status.get('pools', {})
            for pool_name, status in pools.items():
                if 'error' in status:
                    logger.error("  %s线程池: 错误 - %s", pool_name, status['error'])
                else:
                    max_workers = status.get('max_workers', 0)
                    active_threads = status.get('active_threads', 0)
                    pending_tasks = status.get('pending_tasks', 0)
                    utilization = status.get('utilization', 0)

                    logger.info("  %s线程池: 活跃=%d/%d, 等待=%d, 利用率=%.1f%%",
                               pool_name, active_threads, max_workers, pending_tasks, utilization)

            overall = pool_status.get('overall', {})
            if 'overall_utilization' in overall:
                logger.info("  总体利用率: %.1f%%", overall['overall_utilization'])

            system_info = overall.get('system_info', {})
            if 'cpu' in system_info and 'memory' in system_info:
                cpu_percent = system_info['cpu'].get('percent', 0)
                memory_percent = system_info['memory'].get('percent', 0)
                logger.info("  系统资源: CPU=%d%%, 内存=%d%%", cpu_percent, memory_percent)

        except Exception as e:
            logger.error("记录线程池状态失败: %s", e)

    def log_error_with_context(self, context: str, error: Exception, additional_info: Dict[str, Any] = None):
        """记录带上下文的错误信息"""
        if not self.enabled or not self.log_errors:
            return

        logger.error("错误发生 - 上下文: %s", context)
        logger.error("错误类型: %s", type(error).__name__)
        logger.error("错误信息: %s", str(error))

        if additional_info:
            logger.error("附加信息:")
            for key, value in additional_info.items():
                logger.error("  %s: %s", key, value)

        logger.error("错误堆栈:", exc_info=True)

    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """记录性能指标"""
        if not self.enabled or not self.log_performance:
            return

        logger.info("性能指标报告:")

        for key, value in metrics.items():
            if isinstance(value, float):
                logger.info("  %s: %.2f", key, value)
            else:
                logger.info("  %s: %s", key, value)

    def log_strategy_transition(self, node_id: str, from_strategy: str, to_strategy: str, reason: str):
        """记录策略转换"""
        if not self.enabled:
            return

        logger.info("节点%s - 策略转换: %s -> %s", node_id, from_strategy, to_strategy)
        logger.info("节点%s - 转换原因: %s", node_id, reason)

    def log_cache_hit(self, cache_type: str, cache_key: str, hit: bool):
        """记录缓存命中"""
        if not self.enabled:
            return

        status = "命中" if hit else "未命中"
        logger.info("缓存访问 - %s: %s (%s)", cache_type, cache_key, status)

    def log_resource_usage(self, resource_info: Dict[str, Any]):
        """记录资源使用情况"""
        if not self.enabled or not settings.LOG_RESOURCE_USAGE:
            return

        logger.info("资源使用情况:")
        for key, value in resource_info.items():
            logger.info("  %s: %s", key, value)


def create_detailed_logger() -> DetailedLogger:
    """创建详细日志记录器实例"""
    logger_instance = DetailedLogger()
    return logger_instance