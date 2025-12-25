"""
Screenshot Analytics Service - 截图分析服务
基于转写结果分析重要时间点，使用AI选择最佳截图
集成智能截图选择器和OCR降级策略
"""

import json
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.dto.screenshot_dto import (
    TimepointSuggestion, ScreenshotAnalysisRequest,
    ScreenshotSelectionRequest, ScreenshotSelectionResult,
    ScreenshotCandidate
)
from app.infrastructure.llm.provider import generate_markdown_via_llm, _load_provider
from app.infrastructure.llm.screenshot_prompts import (
    CONTENT_ANALYSIS_PROMPT
)
from app.config.settings import settings
# 集成新的智能截图选择器和OCR降级处理器
from app.services.intelligent_screenshot_selector import create_intelligent_screenshot_selector
from app.services.model_capability_detector import ModelCapabilityDetector
from app.services.multimodal_ai_processor import create_multimodal_processor
from app.services.ocr_fallback_processor import create_ocr_fallback_processor

logger = logging.getLogger(__name__)

class ScreenshotAnalyticsService:
    """截图分析服务 - 集成智能截图选择器"""

    def __init__(self):
        """初始化截图分析服务"""
        self.service_name = "ScreenshotAnalytics"

        # 初始化智能截图选择器
        try:
            self.intelligent_selector = create_intelligent_screenshot_selector()
            logger.info(f"[{self.service_name}] 智能截图选择器初始化成功")
        except Exception as e:
            logger.error(f"[{self.service_name}] 智能截图选择器初始化失败: {e}")
            self.intelligent_selector = None

        # 初始化模型能力检测器
        try:
            self.capability_detector = ModelCapabilityDetector()
            logger.info(f"[{self.service_name}] 模型能力检测器初始化成功")
        except Exception as e:
            logger.error(f"[{self.service_name}] 模型能力检测器初始化失败: {e}")
            self.capability_detector = None

        # 初始化OCR降级处理器
        try:
            self.ocr_processor = create_ocr_fallback_processor()
            logger.info(f"[{self.service_name}] OCR降级处理器初始化成功")
        except Exception as e:
            logger.error(f"[{self.service_name}] OCR降级处理器初始化失败: {e}")
            self.ocr_processor = None

        logger.info(f"[{self.service_name}] 截图分析服务初始化完成（含OCR降级）")

    async def analyze_transcript_for_keypoints(
        self,
        transcript_segments: List[Dict[str, Any]],
        video_type_hint: Optional[str] = None,
        provider_id: str = "",
        model_name: str = ""
    ) -> tuple[str, List[TimepointSuggestion]]:
        """
        基于转写结果分析重要时间点

        Args:
            transcript_segments: 转写片段列表
            video_type_hint: 视频类型提示
            provider_id: AI服务提供商ID
            model_name: AI模型名称

        Returns:
            tuple[str, List[TimepointSuggestion]]: (视频类型, 时间点建议列表)

        Raises:
            ValueError: 分析失败
        """
        try:
            logger.info(f"[{self.service_name}] 开始分析转写内容，片段数量: {len(transcript_segments)}")

            # 构建转写文本
            transcript_text = self._build_transcript_text(transcript_segments)

            # 添加视频类型提示
            if video_type_hint:
                transcript_text = f"视频类型提示: {video_type_hint}\n\n转写内容:\n{transcript_text}"

            # 构建AI提示
            prompt = CONTENT_ANALYSIS_PROMPT.format(transcript_text=transcript_text)

            logger.info(f"[{self.service_name}] 调用AI分析转写内容，使用模型: {model_name}")

            # 调用AI分析
            try:
                ai_response = await self._call_ai_analysis(
                    prompt, provider_id, model_name, "content_analysis"
                )
                analysis_result = self._parse_timepoint_analysis(ai_response)

                logger.info(f"[{self.service_name}] AI分析成功，识别视频类型: {analysis_result[0]}, "
                           f"时间点数量: {len(analysis_result[1])}")
                return analysis_result

            except Exception as ai_error:
                logger.error(f"[{self.service_name}] AI主分析失败: {ai_error}")
                logger.error(f"[{self.service_name}] 错误类型: {type(ai_error).__name__}")
                import traceback
                logger.error(f"[{self.service_name}] 完整错误堆栈: {traceback.format_exc()}")
                raise ValueError(f"AI主分析失败: {ai_error}")

        except Exception as e:
            logger.error(f"[{self.service_name}] 转写内容分析失败: {e}")
            logger.error(f"[{self.service_name}] 错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"[{self.service_name}] 完整错误堆栈: {traceback.format_exc()}")
            raise ValueError(f"转写内容分析失败: {e}")


    async def select_best_screenshots_batch(
        self,
        timepoint_groups: Dict[str, List[str]],  # {timepoint_timestamp: [image_paths]}
        timepoint_contexts: Dict[str, str],      # {timepoint_timestamp: context}
        video_type: str,
        provider_id: str = "",
        model_name: str = ""
    ) -> Dict[str, Any]:
        """
        批量选择多个时间点的最佳截图 - 带OCR降级支持

        Args:
            timepoint_groups: 时间点分组字典，格式为 {"时间戳": [图片路径列表]}
            timepoint_contexts: 时间点上下文信息字典，格式为 {"时间戳": "上下文描述"}
            video_type: 视频类型
            provider_id: AI服务提供商ID
            model_name: AI模型名称

        Returns:
            Dict[str, Any]: 批量选择结果
        """
        try:
            logger.info(f"[{self.service_name}] 开始批量选择 {len(timepoint_groups)} 个时间点的截图")

            # 获取Provider配置
            provider_config = self._get_provider_config(provider_id, model_name)
            if not provider_config:
                raise ValueError(f"无法获取Provider配置: {provider_id}")

            # 步骤1: 检测模型是否支持图像处理
            logger.info(f"[{self.service_name}] 检测模型 {model_name} 的视觉能力...")

            if not settings.OCR_FALLBACK_ENABLED:
                logger.info(f"[{self.service_name}] OCR降级已禁用，强制使用AI处理")
                supports_images = True
            else:
                # 使用模型能力检测器
                capability_result = await self.capability_detector._detect_single_capability_cached(provider_config)
                supports_images = capability_result.get('supports_images', False)

                if supports_images:
                    logger.info(f"[{self.service_name}] 模型 {model_name} 支持图像处理，使用AI批量处理")
                else:
                    logger.warning(f"[{self.service_name}] 模型 {model_name} 不支持图像处理，切换到OCR降级处理")

            # 步骤2: 根据能力检测结果选择处理方式
            if supports_images:
                # 使用多模态AI处理
                return await self._process_with_multimodal_ai(
                    timepoint_groups, timepoint_contexts, video_type, provider_config
                )
            else:
                # 使用OCR降级处理
                return await self._process_with_ocr_fallback(
                    timepoint_groups, timepoint_contexts, video_type
                )

        except Exception as e:
            logger.error(f"[{self.service_name}] 批量截图选择失败: {e}")
            raise ValueError(f"批量截图选择失败: {e}")

    async def _process_with_multimodal_ai(
        self,
        timepoint_groups: Dict[str, List[str]],
        timepoint_contexts: Dict[str, str],
        video_type: str,
        provider_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用多模态AI进行批量处理"""
        try:
            # 构建全局上下文
            global_context = f"视频类型: {video_type}\n"
            global_context += f"时间点数量: {len(timepoint_groups)}\n"
            global_context += f"总图片数量: {sum(len(imgs) for imgs in timepoint_groups.values())}"

            logger.info(f"[{self.service_name}] 使用多模态AI进行批量处理")

            # 创建多模态处理器
            multimodal_processor = create_multimodal_processor(provider_config)

            # 调用批量选择
            batch_result = await multimodal_processor.select_best_screenshots_batch(
                timepoint_groups, timepoint_contexts, global_context
            )

            if batch_result.get('success', False):
                logger.info(f"[{self.service_name}] 批量截图选择成功，处理了 {len(batch_result['selections'])} 个时间点")
                logger.info(f"API耗时: {batch_result.get('api_time', 0):.2f}秒，总处理时间: {batch_result.get('processing_time', 0):.2f}秒")
            else:
                error_msg = batch_result.get('error', '批量选择失败')
                logger.error(f"[{self.service_name}] 批量截图选择失败: {error_msg}")
                raise ValueError(f"批量截图选择失败: {error_msg}")

            return batch_result

        except Exception as e:
            logger.error(f"[{self.service_name}] 多模态AI处理失败: {e}")
            raise

    async def _process_with_ocr_fallback(
        self,
        timepoint_groups: Dict[str, List[str]],
        timepoint_contexts: Dict[str, str],
        video_type: str
    ) -> Dict[str, Any]:
        """使用OCR降级进行批量处理 - 并发优化版本"""
        try:
            logger.info(f"[{self.service_name}] 使用OCR降级并发处理 {len(timepoint_groups)} 个时间点")
            start_time = time.time()

            # 启动所有时间点的OCR任务（不等待）
            ocr_tasks = []
            for timepoint_timestamp, image_paths in timepoint_groups.items():
                task = self.ocr_processor.process_images_parallel(image_paths)
                ocr_tasks.append((timepoint_timestamp, task))

            # 使用 asyncio.gather() 并发等待所有时间点完成
            ocr_results = {}
            try:
                # 提取所有任务
                tasks = [task for _, task in ocr_tasks]
                # 并发执行所有任务
                results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                for (timepoint_timestamp, _), result in zip(ocr_tasks, results_with_exceptions):
                    if isinstance(result, Exception):
                        logger.error(f"[{self.service_name}] 时间点 {timepoint_timestamp} OCR失败: {result}")
                        ocr_results[timepoint_timestamp] = []
                    else:
                        ocr_results[timepoint_timestamp] = result
                        logger.debug(f"[{self.service_name}] 时间点 {timepoint_timestamp} OCR完成")

            except Exception as e:
                logger.error(f"[{self.service_name}] OCR并发处理失败: {e}")
                raise

            # 并发选择最佳截图
            selection_tasks = []
            for timepoint_timestamp, results in ocr_results.items():
                # 使用线程池执行最佳图片选择（CPU密集型任务）
                loop = asyncio.get_event_loop()
                task = loop.run_in_executor(None, self.ocr_processor.select_best_image, results)
                selection_tasks.append((timepoint_timestamp, task))

            # 并发等待所有选择任务完成
            selections = []
            try:
                selection_results = await asyncio.gather(*[task for _, task in selection_tasks], return_exceptions=True)

                for (timepoint_timestamp, _), result in zip(selection_tasks, selection_results):
                    if isinstance(result, Exception):
                        logger.error(f"[{self.service_name}] 时间点 {timepoint_timestamp} 最佳图片选择失败: {result}")
                        # 选择失败，使用默认第一张图片
                        first_image = timepoint_groups.get(timepoint_timestamp, [None])[0]
                        if first_image:
                            selections.append({
                                'timepoint': timepoint_timestamp,
                                'selected_image': first_image,
                                'reason': "最佳图片选择失败，默认选择第一张图片",
                                'method': 'ocr_fallback_default'
                            })
                    elif result.get('success', False):
                        selections.append({
                            'timepoint': timepoint_timestamp,
                            'selected_image': result['selected_image'],
                            'reason': f"OCR选择最佳截图，信息评分: {result.get('info_score', 0):.3f}",
                            'method': 'ocr_fallback',
                            'info_score': result.get('info_score', 0.0)  # 添加 info_score
                        })
                    else:
                        # OCR失败，选择第一张图片
                        first_image = timepoint_groups.get(timepoint_timestamp, [None])[0]
                        if first_image:
                            selections.append({
                                'timepoint': timepoint_timestamp,
                                'selected_image': first_image,
                                'reason': "OCR处理失败，默认选择第一张图片",
                                'method': 'ocr_fallback_default'
                            })

            except Exception as e:
                logger.error(f"[{self.service_name}] 最佳图片选择并发处理失败: {e}")
                raise

            processing_time = time.time() - start_time

            logger.info(f"[{self.service_name}] OCR降级并发处理完成")
            logger.info(f"[{self.service_name}] 处理时间点数: {len(timepoint_groups)}")
            logger.info(f"[{self.service_name}] 成功选择截图数: {len(selections)}")
            logger.info(f"[{self.service_name}] 总处理时间: {processing_time:.2f}秒")

            return {
                'success': True,
                'selections': selections,
                'processing_time': processing_time,
                'method': 'ocr_fallback_concurrent',
                'timepoint_count': len(timepoint_groups),
                'successful_selections': len(selections),
                'fallback_reason': '模型不支持图像处理，启用并发OCR处理'
            }

        except Exception as e:
            logger.error(f"[{self.service_name}] OCR降级并发处理失败: {e}")
            raise

    def _build_transcript_text(self, segments: List[Dict[str, Any]]) -> str:
        """构建转写文本"""
        text_parts = []
        for segment in segments:
            start_time = segment.get('start', 0)
            text = segment.get('text', '').strip()
            if text:
                timestamp = self._format_timestamp(start_time)
                text_parts.append(f"[{timestamp}] {text}")

        return '\n'.join(text_parts)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:05.2f}"

    def _get_provider_config(self, provider_id: str, model_name: str) -> Optional[Dict[str, Any]]:
        """
        获取Provider配置 - 使用与连接测试相同的配置获取方式

        Args:
            provider_id: Provider ID
            model_name: 模型名称

        Returns:
            Provider配置字典或None
        """
        try:
            # 使用与连接测试相同的函数来获取provider配置
            provider_config = _load_provider(provider_id)

            if provider_config:
                # 如果成功获取到provider配置，使用指定的模型名或默认模型名
                final_config = {
                    'id': provider_id,
                    'api_key': provider_config.get('api_key', ''),
                    'base_url': provider_config.get('base_url', ''),
                    'model_name': model_name or provider_config.get('model_name', 'gpt-4o')
                }
                logger.info(f"[{self.service_name}] 使用数据库中的AI配置，Provider: {final_config['id']}")
                return final_config
            else:
                # 如果没有找到provider配置，记录警告并返回None
                logger.warning(f"[{self.service_name}] 未找到Provider配置: {provider_id}")
                return None

        except Exception as e:
            logger.error(f"[{self.service_name}] 获取Provider配置失败: {e}")
            return None

    async def _call_ai_analysis(self, prompt: str, provider_id: str, model_name: str, analysis_type: str) -> str:
        """
        调用AI进行分析 - 使用OpenAI API直接调用以控制输出格式

        Args:
            prompt: AI提示词
            provider_id: Provider ID
            model_name: 模型名称
            analysis_type: 分析类型

        Returns:
            str: AI响应结果
        """
        try:
            logger.info(f"[{self.service_name}] 调用AI分析，provider_id: {provider_id}, 模型: {model_name}")

            # 使用与连接测试相同的配置获取方式
            provider_config = _load_provider(provider_id)

            if not provider_config:
                raise ValueError(f"无法获取Provider配置: {provider_id}")

            # 使用OpenAI API直接调用以控制输出格式
            from openai import OpenAI
            client = OpenAI(
                api_key=provider_config.get('api_key', ''),
                base_url=provider_config.get('base_url', '')
            )

            response = client.chat.completions.create(
                model=model_name or provider_config.get('model_name', 'gpt-4o'),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1
            )

            ai_response = response.choices[0].message.content

            if not ai_response:
                raise ValueError("AI响应为空")

            logger.info(f"[{self.service_name}] AI分析响应成功，长度: {len(ai_response)} 字符")
            return ai_response

        except Exception as e:
            logger.error(f"[{self.service_name}] AI分析调用失败: {e}")
            raise ValueError(f"AI分析调用失败: {e}")

    def _parse_timepoint_analysis(self, ai_response: str) -> tuple:
        """
        解析AI时间点分析结果

        Args:
            ai_response: AI响应文本

        Returns:
            tuple: (video_type, timepoints)
        """
        try:
            import json

            # 尝试解析JSON格式
            try:
                cleaned_response = ai_response.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()

                result = json.loads(cleaned_response)

                video_type = result.get('video_type', 'education')
                timepoints_data = result.get('timepoints', [])

                # 转换为TimepointSuggestion对象
                timepoints = []
                for i, tp in enumerate(timepoints_data):
                    timepoint = TimepointSuggestion(
                        timestamp=tp.get('timestamp', f"{i+1}:00"),
                        reason=tp.get('reason', f"重要时间点{i+1}"),
                        importance=tp.get('importance', 'medium'),
                        category=tp.get('category', '知识传递')
                    )
                    timepoints.append(timepoint)

                return video_type, timepoints

            except json.JSONDecodeError:
                # 如果JSON解析失败，使用简单文本解析
                lines = ai_response.strip().split('\n')
                video_type = 'education'  # 默认类型

                # 简单的时间点提取逻辑
                timepoints = []
                for i, line in enumerate(lines):
                    if ':' in line and ('重要' in line or '关键' in line):
                        timestamp = line.split(':')[0].strip()
                        reason = line.strip()
                        timepoint = TimepointSuggestion(
                            timestamp=timestamp,
                            reason=reason,
                            importance='medium',
                            category='知识传递'
                        )
                        timepoints.append(timepoint)

                return video_type, timepoints

        except Exception as e:
            logger.error(f"[{self.service_name}] 解析AI响应失败: {e}")
            # 返回默认结果
            default_timepoint = TimepointSuggestion(
                timestamp="1:00",
                reason="默认时间点",
                importance="medium",
                category="知识传递"
            )
            return 'education', [default_timepoint]