"""
Screenshot Generation Service - 截图生成服务
负责生成候选截图、管理截图文件、协调AI截图选择
"""

import os
import asyncio
import shutil
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from app.models.dto.screenshot_dto import (
    ScreenshotAnalysisRequest, ScreenshotProcessResult,
    ScreenshotGenerationConfig, TimepointSuggestion,
    ScreenshotSelectionResult, ScreenshotCandidate
)
from app.services.screenshot_analytics_service import ScreenshotAnalyticsService
from app.services.utils.screenshot_deduplicator import ScreenshotDeduplicator
from app.utils.video_helper import VideoHelper
from app.config.settings import settings

logger = logging.getLogger(__name__)

class ScreenshotService:
    """截图生成服务"""

    def __init__(self):
        """初始化截图生成服务"""
        self.analytics_service = ScreenshotAnalyticsService()
        # 初始化去重器，使用配置中的阈值
        self.deduplicator = ScreenshotDeduplicator(
            hash_threshold=settings.SCREENSHOT_DEDUP_HASH_THRESHOLD
        )
        self.service_name = "ScreenshotService"
        self.temp_dir = os.path.join(settings.BASE_DIR, "temp_screenshots")
        self.output_dir = os.path.join(settings.BASE_DIR, "static", "screenshots")

        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"[{self.service_name}] 截图生成服务初始化完成")
        logger.info(f"[{self.service_name}] 临时目录: {self.temp_dir}")
        logger.info(f"[{self.service_name}] 输出目录: {self.output_dir}")
        logger.info(f"[{self.service_name}] 去重功能: {'启用' if settings.SCREENSHOT_DEDUP_ENABLED else '禁用'}, 哈希阈值: {settings.SCREENSHOT_DEDUP_HASH_THRESHOLD}")

    async def process_screenshots(
        self,
        request: ScreenshotAnalysisRequest,
        provider_id: str = "",
        model_name: str = ""
    ) -> ScreenshotProcessResult:
        """
        处理截图生成和选择的完整流程

        Args:
            request: 截图分析请求
            provider_id: AI服务提供商ID
            model_name: AI模型名称

        Returns:
            ScreenshotProcessResult: 截图处理结果

        Raises:
            ValueError: 处理失败
        """
        start_time = datetime.now()

        try:
            logger.info(f"[{self.service_name}] 开始处理截图，任务ID: {request.task_id}")

            if not request.screenshot_enabled:
                logger.info(f"[{self.service_name}] 截图功能已禁用，跳过处理")
                return self._create_empty_result(request.task_id, start_time)

            # 验证视频文件
            VideoHelper.validate_video_file(request.video_path)

            # 步骤1: AI分析重要时间点
            video_type, timepoints = await self.analytics_service.analyze_transcript_for_keypoints(
                request.transcript_segments,
                request.video_type_hint,
                provider_id,
                model_name
            )

            logger.info(f"[{self.service_name}] 识别出 {len(timepoints)} 个重要时间点")

            # 步骤2: 使用批量优化处理所有时间点
            selected_screenshots, deduplicated_count = await self._process_batch_timepoints_flow(
                timepoints, request, video_type, provider_id, model_name
            )
            successful_screenshots = sum(len(result.selected) for result in selected_screenshots)

            # 步骤3: 创建处理结果
            processing_time = (datetime.now() - start_time).total_seconds()

            process_result = ScreenshotProcessResult(
                task_id=request.task_id,
                video_type=video_type,
                total_timepoints=len(timepoints),
                successful_screenshots=successful_screenshots,
                selected_screenshots=selected_screenshots,
                processing_time=processing_time,
                deduplicated_count=deduplicated_count if deduplicated_count > 0 else None
            )

            logger.info(f"[{self.service_name}] 截图处理完成: {successful_screenshots} 张截图, "
                       f"去重删除: {deduplicated_count} 张, 耗时: {processing_time:.2f}秒")

            return process_result

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{self.service_name}] 截图处理失败: {e}, 耗时: {processing_time:.2f}秒")
            raise ValueError(f"截图处理失败: {e}")

    async def _generate_candidates_for_timepoint(
        self,
        video_path: str,
        timepoint: TimepointSuggestion,
        window: float,
        candidate_count: int
    ) -> List[str]:
        """为时间点生成候选截图"""
        try:
            # 创建临时输出目录
            temp_output_dir = os.path.join(
                self.temp_dir,
                f"tp_{timepoint.timestamp.replace(':', '_')}"
            )
            os.makedirs(temp_output_dir, exist_ok=True)

            # 生成配置
            config = ScreenshotGenerationConfig(
                quality=2,  # 高质量
                resolution="1280x720",
                format="jpg"
            )

            # 生成候选截图
            candidates = VideoHelper.generate_candidate_screenshots(
                video_path=video_path,
                base_timestamp=timepoint.timestamp,
                window=window,
                candidate_count=candidate_count,
                output_dir=temp_output_dir,
                config=config
            )

            # 返回ScreenshotCandidate对象列表
            return candidates

        except Exception as e:
            logger.error(f"[{self.service_name}] 生成候选截图失败: {e}")
            raise ValueError(f"生成候选截图失败: {e}")

    def _build_timepoint_context(
        self,
        timepoint: TimepointSuggestion,
        segments: List[Dict[str, Any]]
    ) -> str:
        """构建时间点上下文信息"""
        try:
            # 将时间点转换为秒数
            time_seconds = timepoint.to_seconds()

            # 查找时间点附近的转写片段
            context_segments = []
            for segment in segments:
                seg_start = segment.get('start', 0)
                seg_text = segment.get('text', '').strip()

                # 选择时间点前后30秒内的片段
                if abs(seg_start - time_seconds) <= 30:
                    timestamp = self._format_segment_timestamp(seg_start)
                    context_segments.append(f"[{timestamp}] {seg_text}")

            return '\n'.join(context_segments[:10])  # 最多10个片段

        except Exception as e:
            logger.warning(f"[{self.service_name}] 构建上下文失败: {e}")
            return "上下文信息获取失败"

    def _format_segment_timestamp(self, seconds: float) -> str:
        """格式化片段时间戳"""
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:05.2f}"

    async def _move_selected_screenshots(self, selected_paths: List[str]) -> List[str]:
        """将选中的截图移动到输出目录"""
        try:
            final_paths = []

            for old_path in selected_paths:
                if os.path.exists(old_path):
                    # 生成新的文件名
                    filename = f"selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(old_path)}"
                    new_path = os.path.join(self.output_dir, filename)

                    # 移动文件
                    shutil.move(old_path, new_path)
                    final_paths.append(new_path)

                    logger.info(f"[{self.service_name}] 截图已移动: {old_path} -> {new_path}")
                else:
                    logger.warning(f"[{self.service_name}] 选中的截图文件不存在: {old_path}")

            return final_paths

        except Exception as e:
            logger.error(f"[{self.service_name}] 移动截图文件失败: {e}")
            raise ValueError(f"移动截图文件失败: {e}")

    def _create_empty_result(self, task_id: str, start_time: datetime) -> ScreenshotProcessResult:
        """创建空的处理结果（当截图功能禁用时）"""
        processing_time = (datetime.now() - start_time).total_seconds()

        return ScreenshotProcessResult(
            task_id=task_id,
            video_type="未识别",
            total_timepoints=0,
            successful_screenshots=0,
            selected_screenshots=[],
            processing_time=processing_time
        )

    def cleanup_temp_files(self, task_id: str = None):
        """清理临时文件"""
        try:
            logger.info(f"[{self.service_name}] 开始清理临时文件")

            if task_id:
                # 清理特定任务的临时文件
                task_temp_dir = os.path.join(self.temp_dir, f"task_{task_id}")
                if os.path.exists(task_temp_dir):
                    shutil.rmtree(task_temp_dir)
                    logger.info(f"[{self.service_name}] 已清理任务 {task_id} 的临时文件")
            else:
                # 清理所有临时文件
                if os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
                    os.makedirs(self.temp_dir, exist_ok=True)
                    logger.info(f"[{self.service_name}] 已清理所有临时文件")

        except Exception as e:
            logger.warning(f"[{self.service_name}] 清理临时文件失败: {e}")

    def get_screenshot_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取截图处理信息"""
        try:
            # 这里可以从数据库或文件中读取处理结果
            # 目前返回基本信息的示例
            return {
                "task_id": task_id,
                "output_dir": self.output_dir,
                "temp_dir": self.temp_dir,
                "screenshot_count": len([f for f in os.listdir(self.output_dir) if f.startswith(f"selected_{task_id}")])
            }
        except Exception as e:
            logger.error(f"[{self.service_name}] 获取截图信息失败: {e}")
            return None

    def save_process_result(self, result: ScreenshotProcessResult):
        """保存处理结果到文件"""
        try:
            output_file = os.path.join(
                self.output_dir,
                f"{result.task_id}_screenshot_result.json"
            )

            result_data = {
                "task_id": result.task_id,
                "video_type": result.video_type,
                "total_timepoints": result.total_timepoints,
                "successful_screenshots": result.successful_screenshots,
                "selected_screenshots": [
                    {
                        "timepoint": sr.timepoint,
                        "selected": sr.selected,
                        "reasons": sr.reasons,
                        "representativeness": sr.content_representativeness
                    }
                    for sr in result.selected_screenshots
                ],
                "processing_time": result.processing_time,
                "created_at": result.created_at.isoformat()
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)

            logger.info(f"[{self.service_name}] 处理结果已保存: {output_file}")

        except Exception as e:
            logger.error(f"[{self.service_name}] 保存处理结果失败: {e}")

    async def cleanup_on_task_complete(self, task_id: str, keep_screenshots: bool = True):
        """任务完成后的清理工作"""
        try:
            logger.info(f"[{self.service_name}] 任务 {task_id} 完成，开始清理")

            if not keep_screenshots:
                # 如果不保留截图，清理输出目录中的相关文件
                output_files = [f for f in os.listdir(self.output_dir) if f.startswith(f"selected_{task_id}")]
                for file in output_files:
                    file_path = os.path.join(self.output_dir, file)
                    os.remove(file_path)
                    logger.info(f"[{self.service_name}] 已删除输出截图: {file_path}")

            # 清理临时文件
            self.cleanup_temp_files(task_id)

        except Exception as e:
            logger.warning(f"[{self.service_name}] 任务完成清理失败: {e}")

    async def _process_batch_timepoints_flow(
        self,
        timepoints: List[TimepointSuggestion],
        request: ScreenshotAnalysisRequest,
        video_type: str,
        provider_id: str,
        model_name: str
    ) -> Tuple[List[ScreenshotSelectionResult], int]:
        """
        批量处理时间点的优化流程 - 统一使用单次API调用处理所有时间点

        Args:
            timepoints: 时间点列表
            request: 截图分析请求
            video_type: 视频类型
            provider_id: AI服务提供商ID
            model_name: AI模型名称

        Returns:
            Tuple: (截图选择结果列表, 去重删除的数量)
        """
        try:
            logger.info(f"[{self.service_name}] 开始批量处理 {len(timepoints)} 个时间点")

            # 步骤1：为所有时间点生成候选截图（可并发）
            all_candidates = await self._generate_all_candidates_concurrent(timepoints, request)

            if not all_candidates:
                raise ValueError("所有时间点都没有生成候选截图")

            logger.info(f"[{self.service_name}] 候选截图生成完成，总时间点数: {len(all_candidates)}")

            # 步骤2：准备批量处理数据
            timepoint_groups = {}
            timepoint_contexts = {}

            for timepoint in timepoints:
                if timepoint.timestamp in all_candidates:
                    # 提取候选截图的文件路径
                    candidate_files = []
                    for candidate in all_candidates[timepoint.timestamp]:
                        if hasattr(candidate, 'url') and candidate.url:
                            candidate_files.append(candidate.url)
                        elif hasattr(candidate, 'file_path') and candidate.file_path:
                            candidate_files.append(candidate.file_path)

                    if candidate_files:
                        timepoint_groups[timepoint.timestamp] = candidate_files
                        timepoint_contexts[timepoint.timestamp] = self._build_timepoint_context(
                            timepoint, request.transcript_segments
                        )

            if not timepoint_groups:
                raise ValueError("没有有效的时间点候选截图数据")

            logger.info(f"[{self.service_name}] 准备批量处理 {len(timepoint_groups)} 个时间点，总图片数: {sum(len(imgs) for imgs in timepoint_groups.values())}")

            # 步骤3：调用批量AI选择（单次API调用）
            batch_result = await self.analytics_service.select_best_screenshots_batch(
                timepoint_groups, timepoint_contexts, video_type, provider_id, model_name
            )

            if not batch_result.get('success', False):
                error_msg = batch_result.get('error', '批量AI选择失败')
                raise ValueError(f"批量截图选择失败: {error_msg}")

            logger.info(f"[{self.service_name}] 批量AI选择完成，成功选择: {len(batch_result['selections'])} 个时间点")

            # 步骤4：处理批量结果并转换为标准格式
            return await self._process_batch_selection_result(batch_result, all_candidates, timepoints)

        except Exception as e:
            logger.error(f"[{self.service_name}] 批量处理时间点失败: {e}")
            raise ValueError(f"批量处理时间点失败: {e}")

    async def _generate_all_candidates_concurrent(
        self,
        timepoints: List[TimepointSuggestion],
        request: ScreenshotAnalysisRequest
    ) -> Dict[str, List[ScreenshotCandidate]]:
        """
        并发生成所有时间点的候选截图

        Args:
            timepoints: 时间点列表
            request: 截图分析请求

        Returns:
            Dict[str, List[ScreenshotCandidate]]: 时间点到候选截图的映射
        """
        try:
            logger.info(f"[{self.service_name}] 开始并发生成 {len(timepoints)} 个时间点的候选截图")

            async def generate_candidates_for_timepoint(timepoint: TimepointSuggestion) -> tuple[str, List[ScreenshotCandidate]]:
                """为单个时间点生成候选截图"""
                try:
                    candidates = await self._generate_candidates_for_timepoint(
                        request.video_path, timepoint, request.screenshot_window,
                        request.screenshot_candidates
                    )
                    return timepoint.timestamp, candidates
                except Exception as e:
                    logger.error(f"[{self.service_name}] 生成时间点 {timepoint.timestamp} 的候选截图失败: {e}")
                    return timepoint.timestamp, []

            # 使用信号量控制并发，避免同时生成太多截图
            semaphore = asyncio.Semaphore(3)  # 最多同时生成3个时间点的截图

            async def controlled_generation(timepoint: TimepointSuggestion) -> tuple[str, List[ScreenshotCandidate]]:
                async with semaphore:
                    return await generate_candidates_for_timepoint(timepoint)

            # 并发生成所有时间点的候选截图
            tasks = [controlled_generation(tp) for tp in timepoints]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            all_candidates = {}
            total_candidates = 0

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"[{self.service_name}] 候选截图生成异常: {result}")
                elif result and isinstance(result, tuple):
                    timestamp, candidates = result
                    if candidates:
                        all_candidates[timestamp] = candidates
                        total_candidates += len(candidates)
                        logger.info(f"[{self.service_name}] 时间点 {timestamp} 生成 {len(candidates)} 张候选截图")
                    else:
                        logger.warning(f"[{self.service_name}] 时间点 {timestamp} 未生成候选截图")

            logger.info(f"[{self.service_name}] 候选截图并发生成完成: {total_candidates} 张截图来自 {len(all_candidates)} 个时间点")
            return all_candidates

        except Exception as e:
            logger.error(f"[{self.service_name}] 并发生成候选截图失败: {e}")
            raise ValueError(f"并发生成候选截图失败: {e}")

    async def _process_batch_selection_result(
        self,
        batch_result: Dict[str, Any],
        all_candidates: Dict[str, List[ScreenshotCandidate]],
        timepoints: List[TimepointSuggestion]
    ) -> Tuple[List[ScreenshotSelectionResult], int]:
        """
        处理批量选择结果并转换为标准格式

        Args:
            batch_result: 批量AI选择结果
            all_candidates: 所有候选截图
            timepoints: 时间点列表

        Returns:
            Tuple: (截图选择结果列表, 去重删除的数量)
        """
        try:
            logger.info(f"[{self.service_name}] 开始处理批量选择结果")

            selections = batch_result.get('selections', [])
            processed_results = []

            # 创建时间点映射
            timepoint_map = {tp.timestamp: tp for tp in timepoints}

            for selection in selections:
                timepoint_timestamp = selection.get('timepoint')
                selected_image_path = selection.get('selected_image')
                reason = selection.get('reason', '批量选择结果')
                info_score = selection.get('info_score', None)  # 获取 info_score（如果有）

                # 如果没有 info_score，使用默认值 0.5（多模态AI路径）
                if info_score is None:
                    info_score = 0.5
                    logger.debug(f"[{self.service_name}] 时间点 {timepoint_timestamp} 未提供 info_score，使用默认值: {info_score}")

                if not timepoint_timestamp or not selected_image_path:
                    logger.warning(f"[{self.service_name}] 无效的选择结果: {selection}")
                    continue

                # 获取时间点信息
                timepoint = timepoint_map.get(timepoint_timestamp)
                if not timepoint:
                    logger.warning(f"[{self.service_name}] 未知的时间点: {timepoint_timestamp}")
                    continue

                try:
                    # 将选中的截图移动到输出目录
                    final_selected = await self._move_selected_screenshots([selected_image_path])

                    if final_selected:
                        # 创建标准格式的选择结果
                        selection_result = ScreenshotSelectionResult(
                            selected=final_selected,
                            reasons=[reason],
                            content_representativeness="high",  # 批量选择默认为高代表性
                            timepoint=timepoint_timestamp,
                            analysis_time=datetime.now(),
                            info_score=info_score  # 传递 info_score
                        )

                        processed_results.append(selection_result)
                        logger.info(f"[{self.service_name}] 时间点 {timepoint_timestamp} 处理完成，选中截图: {final_selected[0]}")
                    else:
                        logger.warning(f"[{self.service_name}] 时间点 {timepoint_timestamp} 截图移动失败")

                except Exception as e:
                    logger.error(f"[{self.service_name}] 处理时间点 {timepoint_timestamp} 的选择结果失败: {e}")
                    continue

            # 检查是否所有时间点都有处理结果
            processed_timepoints = {result.timepoint for result in processed_results}
            missing_timepoints = set(timepoint_map.keys()) - processed_timepoints

            if missing_timepoints:
                logger.warning(f"[{self.service_name}] {len(missing_timepoints)} 个时间点未生成选择结果: {missing_timepoints}")
                # 为缺失的时间点创建失败结果
                for missing_timepoint in missing_timepoints:
                    candidates = all_candidates.get(missing_timepoint, [])
                    if candidates:
                        # 选择第一张候选截图作为默认选择
                        first_candidate = candidates[0]
                        first_path = getattr(first_candidate, 'url', getattr(first_candidate, 'file_path', ''))
                        try:
                            final_selected = await self._move_selected_screenshots([first_path])
                            if final_selected:
                                selection_result = ScreenshotSelectionResult(
                                    selected=final_selected,
                                    reasons=["批量处理失败，默认选择第一张截图"],
                                    content_representativeness="medium",
                                    timepoint=missing_timepoint,
                                    analysis_time=datetime.now(),
                                    info_score=0.0  # 默认选择的评分为0
                                )
                                processed_results.append(selection_result)
                                logger.info(f"[{self.service_name}] 时间点 {missing_timepoint} 使用默认选择")
                        except Exception as e:
                            logger.error(f"[{self.service_name}] 时间点 {missing_timepoint} 默认选择失败: {e}")

            logger.info(f"[{self.service_name}] 批量选择结果处理完成: {len(processed_results)}/{len(timepoints)} 个时间点")

            # 执行去重处理（如果启用）
            deduplicated_count = 0
            if processed_results and settings.SCREENSHOT_DEDUP_ENABLED:
                logger.info(f"[{self.service_name}] 开始去重检测...")
                dedup_result = await self.deduplicator.remove_duplicates(processed_results)

                # 记录去重结果
                if dedup_result.dropped_timepoints:
                    deduplicated_count = len(dedup_result.dropped_timepoints)
                    logger.info(
                        f"[{self.service_name}] 去重完成: "
                        f"删除了 {deduplicated_count} 个重复截图"
                    )
                    for dropped in dedup_result.dropped_timepoints:
                        logger.debug(
                            f"[{self.service_name}] 丢弃时间点 {dropped['timepoint']}: "
                            f"{dropped['drop_reason']}"
                        )
                else:
                    logger.info(f"[{self.service_name}] 未发现重复截图")

                # 使用去重后的结果
                processed_results = dedup_result.keep_results
                logger.info(f"[{self.service_name}] 去重后保留: {len(processed_results)} 个截图")
            elif not settings.SCREENSHOT_DEDUP_ENABLED:
                logger.info(f"[{self.service_name}] 去重功能已禁用，跳过去重检测")

            return processed_results, deduplicated_count

        except Exception as e:
            logger.error(f"[{self.service_name}] 处理批量选择结果失败: {e}")
            raise ValueError(f"处理批量选择结果失败: {e}")

    async def process_screenshots_from_markdown(
        self,
        markdown: str,
        video_path: str,
        transcript_segments: List[Dict[str, Any]],
        task_id: str,
        screenshot_window: float = 2.0,
        screenshot_candidates: int = 5,
        provider_id: str = "",
        model_name: str = ""
    ) -> Tuple[str, ScreenshotProcessResult]:
        """
        基于 Markdown 中的截图标记处理截图（新流程入口）

        从 Markdown 中提取 *Screenshot-MM:SS 格式的标记，转换为时间点，
        然后调用现有的截图处理管线生成候选截图并选择最佳截图，
        最后将标记替换为实际的图片链接。

        Args:
            markdown: 包含截图标记的 Markdown 文本
            video_path: 视频文件路径
            transcript_segments: 转写片段列表
            task_id: 任务ID
            screenshot_window: 截图时间窗口（秒），默认2.0
            screenshot_candidates: 每个时间点的候选截图数量，默认5
            provider_id: AI服务提供商ID
            model_name: AI模型名称

        Returns:
            Tuple[str, ScreenshotProcessResult]: (替换后的Markdown, 截图处理结果)
        """
        from app.utils.markdown_parser import MarkdownParser

        start_time = datetime.now()
        logger.info(f"[{self.service_name}] 开始基于 Markdown 标记处理截图，任务ID: {task_id}")

        try:
            # 调试：打印完整 markdown 内容
            logger.info(f"[{self.service_name}] ===== 原始 Markdown 内容（完整）=====")
            logger.info(f"[{self.service_name}] {markdown}")
            logger.info(f"[{self.service_name}] ===== Markdown 内容结束 =====")

            # 检查是否包含任何 Screenshot 相关文本
            if "Screenshot" in markdown or "screenshot" in markdown:
                logger.info(f"[{self.service_name}] Markdown 中包含 'Screenshot' 关键字")
            else:
                logger.warning(f"[{self.service_name}] Markdown 中未包含 'Screenshot' 关键字，GPT 可能未输出截图标记")

            # 步骤1: 获取视频时长用于验证时间戳
            video_duration = None
            try:
                video_duration = VideoHelper.get_video_duration(video_path)
                logger.info(f"[{self.service_name}] 视频时长: {video_duration:.2f}秒")
            except Exception as e:
                logger.warning(f"[{self.service_name}] 获取视频时长失败: {e}，将跳过时长验证")

            # 步骤2: 从 Markdown 提取截图时间戳
            raw_timestamps = MarkdownParser.extract_screenshot_timestamps(markdown, video_duration)

            if not raw_timestamps:
                logger.warning(f"[{self.service_name}] Markdown 中未找到截图标记，跳过截图处理")
                empty_result = self._create_empty_result(task_id, start_time)
                return markdown, empty_result

            logger.info(f"[{self.service_name}] 提取到 {len(raw_timestamps)} 个截图标记")

            # 步骤3: 验证并去重时间戳（过滤间隔过近的标记）
            validated_timestamps = MarkdownParser.validate_and_deduplicate(raw_timestamps, min_interval=15.0)

            if not validated_timestamps:
                logger.warning(f"[{self.service_name}] 所有时间戳被过滤，跳过截图处理")
                empty_result = self._create_empty_result(task_id, start_time)
                return markdown, empty_result

            logger.info(f"[{self.service_name}] 有效截图标记: {len(validated_timestamps)} 个")

            # 步骤4: 转换为 TimepointSuggestion 对象
            timepoints = MarkdownParser.convert_to_timepoint_suggestions(
                validated_timestamps,
                default_window=screenshot_window
            )

            logger.info(f"[{self.service_name}] 创建了 {len(timepoints)} 个 TimepointSuggestion")

            # 步骤5: 创建截图分析请求（复用现有结构）
            request = ScreenshotAnalysisRequest(
                task_id=task_id,
                video_path=video_path,
                transcript_segments=transcript_segments,
                screenshot_enabled=True,
                screenshot_mode="smart",
                screenshot_window=screenshot_window,
                screenshot_candidates=screenshot_candidates
            )

            # 步骤6: 调用现有的批量处理流程（完全复用）
            # 使用 "GPT标记" 作为视频类型（因为时间点来自 GPT 标记）
            video_type = "GPT标记"

            selected_screenshots, deduplicated_count = await self._process_batch_timepoints_flow(
                timepoints, request, video_type, provider_id, model_name
            )

            successful_screenshots = sum(len(result.selected) for result in selected_screenshots)
            logger.info(f"[{self.service_name}] 截图生成完成: {successful_screenshots} 张, 去重删除: {deduplicated_count} 张")

            # 步骤7: 构建时间戳到图片URL的映射
            # 使用完整的服务器URL以确保前端可以正确加载图片
            from app.config.settings import settings
            full_base_url = f"http://localhost:{settings.BACKEND_PORT}/static/screenshots"

            screenshot_mapping = MarkdownParser.build_screenshot_mapping(
                selected_screenshots,
                base_url=full_base_url
            )

            logger.info(f"[{self.service_name}] 构建了 {len(screenshot_mapping)} 个截图映射")

            # 步骤8: 替换 Markdown 中的截图标记
            # 对于被去重删除的截图，标记会被删除（fallback=None）
            updated_markdown = MarkdownParser.replace_markers_with_images(
                markdown,
                screenshot_mapping,
                fallback=None  # 删除未找到的标记（被去重删除的）
            )

            # 清理连续的多余空行（最多保留2个连续换行）
            import re
            updated_markdown = re.sub(r'\n{3,}', '\n\n', updated_markdown)

            # 步骤9: 创建处理结果
            processing_time = (datetime.now() - start_time).total_seconds()

            process_result = ScreenshotProcessResult(
                task_id=task_id,
                video_type=video_type,
                total_timepoints=len(timepoints),
                successful_screenshots=successful_screenshots,
                selected_screenshots=selected_screenshots,
                processing_time=processing_time,
                deduplicated_count=deduplicated_count if deduplicated_count > 0 else None
            )

            logger.info(
                f"[{self.service_name}] Markdown 截图处理完成: "
                f"{successful_screenshots} 张截图, 去重删除: {deduplicated_count} 张, 耗时: {processing_time:.2f}秒"
            )

            return updated_markdown, process_result

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[{self.service_name}] Markdown 截图处理失败: {e}, 耗时: {processing_time:.2f}秒")

            # 失败时返回原始 Markdown 和空结果
            empty_result = self._create_empty_result(task_id, start_time)
            return markdown, empty_result
