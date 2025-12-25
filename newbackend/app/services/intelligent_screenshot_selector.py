"""
智能截图选择器
主入口，整合所有并发处理和多节点功能
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config.settings import settings
from app.services.utils.thread_pool_manager import ThreadPoolManager
from app.services.utils.detailed_logger import DetailedLogger
from app.services.model_capability_detector import ModelCapabilityDetector
from app.services.multimodal_ai_processor import MultimodalAIProcessor
from app.services.ocr_fallback_processor import OCRFallbackProcessor
from app.services.utils.image_encoder import ImageEncoder

logger = logging.getLogger(__name__)


class IntelligentScreenshotSelector:
    """智能截图选择器 - 主入口"""

    def __init__(self):
        """初始化智能截图选择器"""
        if not settings.INTELLIGENT_SCREENSHOT_ENABLED:
            logger.warning("智能截图选择功能已禁用")
            self.enabled = False
            return

        self.enabled = True
        self.thread_pool_manager = ThreadPoolManager()
        self.detailed_logger = DetailedLogger()
        self.capability_detector = ModelCapabilityDetector()
        self.image_encoder = ImageEncoder()

        logger.info("智能截图选择器初始化完成")
        logger.info(f"功能状态: {self.enabled}")

    def _extract_image_paths(self, candidates: List[Any]) -> List[str]:
        """从候选对象中提取图片路径"""
        image_paths = []

        for candidate in candidates:
            if isinstance(candidate, str):
                # 字符串路径
                image_paths.append(candidate)
            else:
                # 对象类型，提取文件路径
                path = getattr(candidate, 'file_path', getattr(candidate, 'url', ''))
                if path:
                    image_paths.append(path)
                else:
                    logger.warning(f"候选截图缺少路径信息: {candidate}")

        return image_paths

    async def select_with_intelligent_strategy(self, request: Any, candidates: List[Any], provider_config: Dict[str, Any]) -> Dict[str, Any]:
        """智能策略选择入口 - 优化版"""
        task_id = getattr(request, 'task_id', f"task_{int(time.time())}")

        if not self.enabled:
            return {
                'success': False,
                'error': '智能截图选择功能已禁用',
                'method': 'disabled',
                'task_id': task_id
            }

        start_time = time.time()

        # 开始详细日志记录
        self.detailed_logger.log_processing_start(task_id, len(candidates), provider_config)

        try:
            # 步骤1: 请求级能力检测（只检测一次）
            logger.info(f"[{task_id}] 开始请求级模型能力检测...")
            capability_result = await self._detect_model_capability_once(provider_config, task_id)

            # 步骤2: 根据能力检测结果确定处理策略
            processing_strategy = "multimodal_ai" if capability_result['supports_images'] else "ocr_fallback"
            logger.info(f"[{task_id}] 确定处理策略: {processing_strategy} (能力置信度: {capability_result.get('confidence', 0):.2f})")

            # 步骤3: 提取图片路径（跳过分组）
            image_paths = self._extract_image_paths(candidates)

            if not image_paths:
                raise ValueError("没有有效的图片路径")

            logger.info(f"[{task_id}] 使用策略 {processing_strategy} 处理 {len(image_paths)} 张候选截图")

            # 步骤4: 直接处理候选截图
            if processing_strategy == "multimodal_ai":
                result = await self._process_with_multimodal_ai_direct(image_paths, provider_config, task_id)
            else:
                result = await self._process_with_ocr_direct(image_paths, provider_config, task_id)

            # 步骤5: 构建兼容的结果格式
            processing_time = time.time() - start_time
            final_result = self._build_compatible_result(result, task_id, processing_time, processing_strategy, capability_result, len(candidates))

            # 记录处理完成
            self.detailed_logger.log_final_result(task_id, final_result, processing_time)

            return final_result

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"智能选择处理失败: {str(e)}"
            logger.error(error_msg, exc_info=True)

            self.detailed_logger.log_error_with_context("智能选择处理", e, {
                'task_id': task_id,
                'candidate_count': len(candidates),
                'processing_time': processing_time
            })

            return {
                'success': False,
                'error': error_msg,
                'task_id': task_id,
                'processing_time': processing_time,
                'total_time': processing_time,
                'method': 'intelligent_selection',
                'strategy_used': 'failed',
                'capability_result': None
            }

    async def _detect_model_capability_once(self, provider_config: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        请求级模型能力检测（只检测一次）

        Args:
            provider_config: Provider配置
            task_id: 任务ID

        Returns:
            能力检测结果
        """
        try:
            logger.info(f"[{task_id}] 执行请求级模型能力检测...")
            start_time = time.time()

            capability_result = await self.capability_detector._detect_single_capability_cached(provider_config)

            detection_time = time.time() - start_time
            logger.info(f"[{task_id}] 能力检测完成，耗时: {detection_time:.2f}s, 结果: {capability_result['supports_images']}")

            return capability_result

        except Exception as e:
            logger.error(f"[{task_id}] 能力检测失败: {e}")
            # 默认使用OCR降级策略
            return {
                'supports_images': False,
                'confidence': 0.0,
                'error': str(e),
                'reason': '能力检测异常，降级到OCR'
            }

    # DEPRECATED: 这个方法已不再使用，被直接处理逻辑替代
    # async def _process_multiple_nodes_with_strategy(
    #     self,
    #     timepoint_nodes: List[Dict[str, Any]],
    #     provider_config: Dict[str, Any],
    #     task_id: str,
    #     processing_strategy: str,
    #     capability_result: Dict[str, Any]
    # ) -> List[Dict[str, Any]]:
    #     """
    #     使用确定策略进行多节点并发处理（不再重复检测）
    #
    #     DEPRECATED: 不再需要多节点并发处理，直接处理所有候选图片
    #     """
    #     pass  # 保留作为参考，实际不再使用

    # DEPRECATED: 这个方法已不再使用，被直接处理逻辑替代
    # async def _process_single_node_with_strategy(...) 和相关降级方法已废弃
    # 详情请参考 _process_with_multimodal_ai_direct 和 _process_with_ocr_direct
    pass

    # DEPRECATED: 这个方法已不再使用，被直接处理逻辑替代
    # async def _process_multiple_nodes_concurrent(...) 和相关方法已废弃
    # 不再需要节点级并发处理，所有候选图片直接批量处理
    pass

    # DEPRECATED: 这个方法已不再使用，被直接处理逻辑替代
    # async def _process_single_node_intelligent(...) 已废弃
    # 详情请参考 _process_with_multimodal_ai_direct 和 _process_with_ocr_direct
    pass

    async def _process_with_multimodal_ai(self, image_paths: List[str], provider_config: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """使用多模态AI处理图像"""
        try:
            # 创建多模态处理器
            multimodal_processor = MultimodalAIProcessor(
                provider_config['api_key'],
                provider_config['base_url'],
                provider_config['model_name']
            )

            # 构建上下文信息
            context = f"时间点: {node_id} 的截图选择"

            # 处理图像选择
            result = await multimodal_processor.select_best_image(image_paths, context)

            return result

        except Exception as e:
            logger.error(f"多模态AI处理失败 {node_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'multimodal_ai'
            }

    async def _process_with_multimodal_ai_direct(self, image_paths: List[str], provider_config: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """直接使用多模态AI处理图像"""
        try:
            # 创建多模态处理器
            multimodal_processor = MultimodalAIProcessor(
                provider_config['api_key'],
                provider_config['base_url'],
                provider_config['model_name']
            )

            # 构建上下文信息
            context = f"任务ID: {task_id} 的截图选择，请从{len(image_paths)}张候选截图中选择最佳一张"

            # 处理图像选择（AI将同时看到所有图片）
            result = await multimodal_processor.select_best_image(image_paths, context)

            logger.info(f"[{task_id}] 多模态AI选择完成，处理了 {len(image_paths)} 张图片")
            return result

        except Exception as e:
            logger.error(f"[{task_id}] 多模态AI处理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'multimodal_ai'
            }

    async def _process_with_ocr_direct(self, image_paths: List[str], provider_config: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """直接使用OCR处理图像"""
        try:
            # 创建OCR处理器
            ocr_processor = OCRFallbackProcessor()

            # 并行OCR处理
            ocr_results = await ocr_processor.process_images_parallel(image_paths)

            # 选择最佳图片
            selection_result = ocr_processor.select_best_image(ocr_results)

            logger.info(f"[{task_id}] OCR选择完成，处理了 {len(image_paths)} 张图片")
            return selection_result

        except Exception as e:
            logger.error(f"[{task_id}] OCR处理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'ocr_fallback'
            }

    def _build_compatible_result(self, result: Dict[str, Any], task_id: str, processing_time: float, strategy: str, capability_result: Dict[str, Any], candidate_count: int) -> Dict[str, Any]:
        """构建与现有接口兼容的结果格式"""
        if result.get('success'):
            return {
                'success': True,
                'task_id': task_id,
                'total_time': processing_time,
                'selected_image': result.get('selected_image'),
                'processing_method': strategy,
                'success_rate': 1.0,
                'nodes_processed': 1,  # 简化为单节点
                'images_processed': candidate_count,
                'successful_nodes': 1,
                'failed_nodes': 0,
                'node_results': [{
                    'node_id': 'direct_processing',
                    'success': True,
                    'best_image': result.get('selected_image'),
                    'processing_method': strategy,
                    'processing_time': processing_time
                }],
                'timestamp': datetime.now().isoformat(),
                'strategy_used': strategy,
                'capability_result': capability_result,
                'candidate_count': candidate_count
            }
        else:
            return {
                'success': False,
                'task_id': task_id,
                'total_time': processing_time,
                'error': result.get('error', '处理失败'),
                'processing_method': strategy,
                'success_rate': 0.0,
                'nodes_processed': 1,
                'images_processed': candidate_count,
                'successful_nodes': 0,
                'failed_nodes': 1,
                'node_results': [],
                'timestamp': datetime.now().isoformat(),
                'strategy_used': strategy,
                'capability_result': capability_result
            }

    async def _fallback_to_ocr(self, node_data: Dict[str, Any], provider_config: Dict[str, Any], task_id: str, start_time: float) -> Dict[str, Any]:
        """降级到OCR处理"""
        node_id = node_data['node_id']
        image_paths = node_data['image_paths']
        timestamp = node_data['timestamp']

        self.detailed_logger.log_ocr_fallback_start(node_id, len(image_paths))

        try:
            # 创建OCR处理器
            ocr_processor = OCRFallbackProcessor()

            # 并行OCR处理
            ocr_results = await ocr_processor.process_images_parallel(image_paths)

            # 选择最佳图片
            selection_result = ocr_processor.select_best_image(ocr_results)

            node_time = time.time() - start_time

            if selection_result['success']:
                self.detailed_logger.log_node_completion(
                    node_id, selection_result['selected_image'],
                    node_time, "ocr_fallback", True
                )

                return {
                    'node_id': node_id,
                    'timestamp': timestamp,
                    'success': True,
                    'best_image': selection_result['selected_image'],
                    'processing_method': 'ocr_fallback',
                    'processing_time': node_time,
                    'details': {
                        'capability_result': {'supports_images': False, 'reason': '模型不支持图像'},
                        'ocr_results': ocr_results,
                        'selection_result': selection_result
                    }
                }
            else:
                return {
                    'node_id': node_id,
                    'timestamp': timestamp,
                    'success': False,
                    'error': selection_result.get('error', 'OCR选择失败'),
                    'processing_method': 'ocr_fallback',
                    'processing_time': node_time
                }

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"OCR降级处理失败 {node_id}: {str(e)}"
            logger.error(f"{node_id} - {error_msg}")

            return {
                'node_id': node_id,
                'timestamp': timestamp,
                'success': False,
                'error': error_msg,
                'processing_method': 'ocr_fallback',
                'processing_time': processing_time
            }

    def _build_final_result(self, node_results: List[Dict[str, Any]], task_id: str, start_time: float) -> Dict[str, Any]:
        """
        构建最终结果

        Args:
            node_results: 节点处理结果
            task_id: 任务ID
            start_time: 开始时间

        Returns:
            最终处理结果
        """
        total_time = time.time() - start_time
        successful_nodes = [r for r in node_results if r.get('success', False)]

        # 选择所有成功节点中的最佳图片
        best_images = []
        for result in successful_nodes:
            if result.get('best_image'):
                best_images.append(result['best_image'])

        if best_images:
            # 这里可以添加进一步的选择逻辑，比如选择评分最高的
            selected_image = best_images[0]  # 简化：选择第一个最佳图片
            method = "intelligent_selection"
        else:
            selected_image = None
            method = "all_failed"

        total_nodes = len(node_results)
        success_rate = len(successful_nodes) / total_nodes if total_nodes > 0 else 0

        # 统计信息
        nodes_processed = len(node_results)
        images_processed = sum(len(result.get('details', {}).get('ocr_results', []))
                             if 'details' in result and 'ocr_results' in result['details']
                             else 0 for result in node_results)

        return {
            'success': len(successful_nodes) > 0,
            'task_id': task_id,
            'total_time': total_time,
            'selected_image': selected_image,
            'processing_method': method,
            'success_rate': success_rate,
            'nodes_processed': nodes_processed,
            'images_processed': images_processed,
            'successful_nodes': len(successful_nodes),
            'failed_nodes': len(node_results) - len(successful_nodes),
            'node_results': node_results,
            'timestamp': datetime.now().isoformat()
        }

    def get_status(self) -> Dict[str, Any]:
        """获取选择器状态"""
        return {
            'enabled': self.enabled,
            'thread_pool_status': self.thread_pool_manager.get_pool_status(),
            'capability_cache_info': self.capability_detector.get_cache_info()
        }


def create_intelligent_screenshot_selector() -> IntelligentScreenshotSelector:
    """创建智能截图选择器实例"""
    selector = IntelligentScreenshotSelector()
    logger.info("智能截图选择器实例创建完成")
    return selector