"""
OCR降级处理器
基于comprehensive_test2.py的并发优化实现
多线程并行处理OCR降级方案
"""

import os
import re
import time
import threading
import logging
import warnings
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import easyocr

from app.config.settings import settings
from app.services.utils.thread_pool_manager import ThreadPoolManager

try:
    import psutil
except ImportError:
    psutil = None

# 在导入时立即过滤掉 EasyOCR 的 pin_memory 警告
warnings.filterwarnings("ignore", category=UserWarning, module="torch.utils.data.dataloader")

logger = logging.getLogger(__name__)


class OCRFallbackProcessor:
    """OCR降级处理器，基于comprehensive_test2.py成功实现"""

    def __init__(self):
        """初始化OCR降级处理器"""
        self.thread_local = threading.local()
        self.max_workers = settings.OCR_MAX_WORKERS
        self.confidence_threshold = 0.5

        # 初始化线程池管理器 - 使用专用OCR线程池
        self.thread_pool_manager = ThreadPoolManager()
        self.ocr_executor = self.thread_pool_manager.get_ocr_executor()

        # 记录CPU核心数信息
        try:
            if psutil:
                physical_cores = psutil.cpu_count(logical=False)
                logical_cores = os.cpu_count() or 4
                logger.info(f"CPU核心数 - 物理: {physical_cores}, 逻辑: {logical_cores}")
            else:
                logical_cores = os.cpu_count() or 4
                logger.info(f"CPU核心数 - 逻辑: {logical_cores} (psutil不可用)")
        except Exception as e:
            logical_cores = os.cpu_count() or 4
            logger.warning(f"获取CPU核心数失败: {e}, 使用逻辑核心数: {logical_cores}")

        logger.info("OCR降级处理器初始化完成（优化并发版本）")
        logger.info(f"工作线程数: {self.max_workers} (根据CPU核心数自动计算)")
        logger.info(f"OCR专用线程池: {settings.OCR_MAX_WORKERS} 个工作线程")
        logger.info(f"置信度阈值: {self.confidence_threshold}")

    def _get_reader(self):
        """获取线程本地的OCR读取器"""
        if not hasattr(self.thread_local, 'reader'):
            logger.debug(f"为线程 {threading.current_thread().name} 初始化OCR实例")
            start_time = time.time()

            try:
                # 直接使用CPU模式，不指定GPU参数
                self.thread_local.reader = easyocr.Reader(['ch_sim', 'en'], verbose=False)
                init_time = time.time() - start_time
                logger.debug(f"线程 {threading.current_thread().name} OCR实例初始化成功（CPU模式），耗时: {init_time:.2f}秒")
            except Exception as e:
                logger.error(f"线程 {threading.current_thread().name} OCR实例初始化失败: {e}")
                raise

        return self.thread_local.reader

    async def process_images_parallel(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        多线程并行处理OCR - 真正异步版本

        Args:
            image_paths: 图像路径列表

        Returns:
            处理结果列表
        """
        import asyncio

        start_time = time.time()
        logger.info(f"开始并行OCR处理 {len(image_paths)} 张图片")
        logger.info(f"使用专用OCR线程池: {settings.OCR_MAX_WORKERS} 个工作线程")

        # 验证图像文件存在
        valid_images = []
        for img_path in image_paths:
            if os.path.exists(img_path):
                valid_images.append(img_path)
            else:
                logger.warning(f"图像文件不存在，跳过: {img_path}")
                # 创建失败结果
                valid_images.append(img_path)  # 保持索引对应

        if not valid_images:
            logger.error("没有有效的图像文件")
            return []

        # 使用异步线程池并发处理所有图片
        loop = asyncio.get_event_loop()
        tasks = []

        for i, img_path in enumerate(valid_images):
            # 使用 run_in_executor 将同步函数放到专用OCR线程池中异步执行
            task = loop.run_in_executor(self.ocr_executor, self._process_single_image, img_path, i)
            tasks.append(task)

        # 并发等待所有任务完成
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    img_path = valid_images[i]
                    logger.error(f"OCR处理异常 {img_path}: {result}")
                    processed_results.append({
                        'image_path': img_path,
                        'success': False,
                        'error': str(result),
                        'processing_time': 0.0
                    })
                else:
                    processed_results.append(result)
                    if result['success']:
                        logger.debug(f"OCR完成 {i+1}/{len(valid_images)}: {os.path.basename(result['image_path'])}")
                    else:
                        logger.debug(f"OCR失败 {i+1}/{len(valid_images)}: {os.path.basename(result['image_path'])}")

        except Exception as e:
            logger.error(f"OCR异步处理失败: {e}")
            # 返回失败结果
            return [{
                'image_path': img_path,
                'success': False,
                'error': f"异步处理失败: {str(e)}",
                'processing_time': 0.0
            } for img_path in valid_images]

        processing_time = time.time() - start_time
        successful_count = sum(1 for r in processed_results if r['success'])

        logger.info(f"OCR并行处理完成，耗时: {processing_time:.2f}秒")
        logger.info(f"成功处理: {successful_count}/{len(processed_results)} 张图片")

        if successful_count < len(processed_results):
            logger.warning(f"失败的图片: {len(processed_results) - successful_count} 张")

        return processed_results

    def _process_single_image(self, image_path: str, index: int = 0) -> Dict[str, Any]:
        """
        处理单张图片，返回文本和评分

        Args:
            image_path: 图像文件路径
            index: 图片索引（用于日志）

        Returns:
            处理结果字典
        """
        start_time = time.time()

        try:
            if not os.path.exists(image_path):
                return {
                    'image_path': image_path,
                    'success': False,
                    'error': '文件不存在',
                    'processing_time': 0.0
                }

            logger.debug(f"开始OCR处理图片 {index + 1}: {os.path.basename(image_path)}")

            reader = self._get_reader()

            # 执行OCR识别
            ocr_start = time.time()
            results = reader.readtext(image_path)
            ocr_time = time.time() - ocr_start

            # 提取文本并计算置信度
            texts = []
            confidences = []
            bboxes = []

            for (bbox, text, confidence) in results:
                if confidence > self.confidence_threshold:
                    texts.append(text)
                    confidences.append(confidence)
                    bboxes.append(bbox)

            full_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # 计算信息评分
            info_score = self._calculate_info_score(full_text, avg_confidence)

            processing_time = time.time() - start_time

            logger.debug(f"图片 {index + 1} OCR完成:")
            logger.debug(f"  文本长度: {len(full_text)} 字符")
            logger.debug(f"  检测区域: {len(results)} 个")
            logger.debug(f"  有效区域: {len(confidences)} 个")
            logger.debug(f"  平均置信度: {avg_confidence:.3f}")
            logger.debug(f"  信息评分: {info_score:.3f}")
            logger.debug(f"  OCR耗时: {ocr_time:.2f}秒")
            logger.debug(f"  总耗时: {processing_time:.2f}秒")

            return {
                'image_path': image_path,
                'image_index': index,
                'text': full_text,
                'confidence': avg_confidence,
                'info_score': info_score,
                'detections': len(results),
                'valid_detections': len(confidences),
                'text_length': len(full_text),
                'processing_time': processing_time,
                'ocr_time': ocr_time,
                'success': True
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"OCR处理异常 {image_path} (索引 {index}): {e}")
            return {
                'image_path': image_path,
                'image_index': index,
                'text': '',
                'confidence': 0,
                'info_score': 0,
                'detections': 0,
                'valid_detections': 0,
                'text_length': 0,
                'processing_time': processing_time,
                'success': False,
                'error': str(e)
            }

    def _calculate_info_score(self, text: str, confidence: float) -> float:
        """
        计算图像信息评分
        基于comprehensive_test2.py的评分算法

        Args:
            text: 识别的文本
            confidence: 平均置信度

        Returns:
            信息评分 (0-1)
        """
        if not text:
            return 0.0

        # 文本密度 (40%) - 文本长度权重
        text_density = min(len(text) / 100, 1.0)

        # 词汇多样性 (30%) - 独特词汇比例
        words = text.split()
        unique_words = set(words)
        diversity = len(unique_words) / len(words) if words else 0

        # 复杂度 (20%) - 数字和特殊字符比例
        numbers = len(re.findall(r'\d', text))
        special_chars = len(re.findall(r'[^\w\s]', text))
        complexity = (numbers + special_chars) / len(text) if text else 0

        # 置信度 (10%)
        confidence_score = confidence

        # 综合评分
        score = (
            text_density * 0.4 +
            diversity * 0.3 +
            complexity * 0.2 +
            confidence_score * 0.1
        )

        return score

    def select_best_image(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从OCR结果中选择最佳图片

        Args:
            results: OCR处理结果列表

        Returns:
            选择结果
        """
        successful_results = [r for r in results if r['success']]

        if not successful_results:
            logger.warning("所有图片OCR处理都失败了")
            return {
                'success': False,
                'error': '所有图片OCR处理都失败了',
                'method': 'ocr_fallback',
                'all_results': results
            }

        logger.info(f"从 {len(successful_results)} 张成功OCR的图片中选择最佳图片")

        # 按信息评分排序
        best_result = max(successful_results, key=lambda x: x['info_score'])

        # 记录选择详情
        logger.info(f"OCR选择最佳图片: {os.path.basename(best_result['image_path'])}")
        logger.info(f"最佳图片信息评分: {best_result['info_score']:.3f}")
        logger.info(f"最佳图片文本长度: {best_result['text_length']} 字符")
        logger.info(f"最佳图片OCR置信度: {best_result['confidence']:.3f}")

        # 显示前3名的对比
        sorted_results = sorted(successful_results, key=lambda x: x['info_score'], reverse=True)
        logger.info("OCR评分排名:")
        for i, result in enumerate(sorted_results[:3]):
            filename = os.path.basename(result['image_path'])
            logger.info(f"  {i+1}. {filename}: {result['info_score']:.3f}")

        return {
            'success': True,
            'selected_image': best_result['image_path'],
            'info_score': best_result['info_score'],
            'text': best_result['text'],
            'confidence': best_result['confidence'],
            'method': 'ocr_fallback',
            'all_results': results,
            'best_result_details': best_result
        }

    async def batch_process_images(self, image_groups: List[List[str]]) -> List[Dict[str, Any]]:
        """
        批量处理多组图像

        Args:
            image_groups: 图像组列表

        Returns:
            处理结果列表
        """
        logger.info(f"开始批量OCR处理，组数: {len(image_groups)}")

        results = []
        total_images = sum(len(group) for group in image_groups)

        for i, image_group in enumerate(image_groups):
            logger.info(f"处理第 {i+1}/{len(image_groups)} 组: {len(image_group)} 张图片")

            try:
                group_results = await self.process_images_parallel(image_group)

                # 为每张图片添加组信息
                for result in group_results:
                    result['group_index'] = i
                    result['group_name'] = f'group_{i+1}'

                results.append({
                    'group_index': i,
                    'group_name': f'group_{i+1}',
                    'image_count': len(image_group),
                    'results': group_results,
                    'success_count': sum(1 for r in group_results if r['success'])
                })

            except Exception as e:
                logger.error(f"第 {i+1} 组处理异常: {e}")
                results.append({
                    'group_index': i,
                    'group_name': f'group_{i+1}',
                    'image_count': len(image_group),
                    'results': [],
                    'success_count': 0,
                    'error': str(e)
                })

        successful_groups = sum(1 for r in results if r.get('success_count', 0) > 0)
        total_successful = sum(r.get('success_count', 0) for r in results)

        logger.info(f"批量OCR处理完成: {successful_groups}/{len(image_groups)} 组有成功结果")
        logger.info(f"总体成功率: {total_successful}/{total_images} 张图片")

        return results

    def get_processing_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取处理统计信息

        Args:
            results: 处理结果列表

        Returns:
            统计信息
        """
        successful_results = [r for r in results if r['success']]

        if not results:
            return {
                'total_images': 0,
                'successful_images': 0,
                'success_rate': 0,
                'avg_info_score': 0,
                'avg_confidence': 0,
                'avg_processing_time': 0,
                'total_text_length': 0
            }

        total_images = len(results)
        successful_count = len(successful_results)
        success_rate = successful_count / total_images if total_images > 0 else 0

        if successful_results:
            avg_info_score = sum(r['info_score'] for r in successful_results) / len(successful_results)
            avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
            avg_processing_time = sum(r['processing_time'] for r in successful_results) / len(successful_results)
            total_text_length = sum(r['text_length'] for r in successful_results)
        else:
            avg_info_score = 0
            avg_confidence = 0
            avg_processing_time = 0
            total_text_length = 0

        return {
            'total_images': total_images,
            'successful_images': successful_count,
            'success_rate': success_rate,
            'avg_info_score': round(avg_info_score, 3),
            'avg_confidence': round(avg_confidence, 3),
            'avg_processing_time': round(avg_processing_time, 2),
            'total_text_length': total_text_length,
            'avg_text_length': round(total_text_length / max(successful_count, 1), 1)
        }

    def cleanup(self):
        """清理资源"""
        try:
            # 关闭线程池管理器
            if hasattr(self, 'thread_pool_manager'):
                logger.info("关闭OCR专用线程池...")
                self.thread_pool_manager.shutdown(wait=True, timeout=10.0)
                logger.info("OCR专用线程池已关闭")
        except Exception as e:
            logger.error(f"关闭线程池失败: {e}")
        finally:
            # 线程本地存储会随着线程结束自动清理
            logger.info("OCR处理器资源已清理（线程本地存储自动管理）")


def create_ocr_fallback_processor() -> OCRFallbackProcessor:
    """创建OCR降级处理器实例"""
    processor = OCRFallbackProcessor()
    logger.info("OCR降级处理器实例创建完成")
    return processor