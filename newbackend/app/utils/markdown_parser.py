"""
Markdown Parser Utilities - Markdown 解析工具
负责从 Markdown 中提取截图标记、验证时间戳、替换占位符
"""

import re
import logging
from typing import List, Tuple, Dict, Optional
from datetime import datetime

from app.models.dto.screenshot_dto import TimepointSuggestion

logger = logging.getLogger(__name__)


class MarkdownParser:
    """Markdown 解析器 - 处理截图时间点标记"""

    # 截图标记正则表达式
    # 匹配格式: *Screenshot-MM:SS (两位数格式)
    SCREENSHOT_PATTERN = r"\*Screenshot-(\d{2}):(\d{2})"

    @staticmethod
    def extract_screenshot_timestamps(
        markdown: str,
        video_duration: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        从 Markdown 中提取截图时间标记

        Args:
            markdown: Markdown 文本
            video_duration: 视频总时长（秒），用于验证时间戳有效性

        Returns:
            List[Tuple[str, float]]: [(原始标记文本, 时间戳秒数), ...]
        """
        logger.info("[MarkdownParser] 开始提取截图时间标记")

        results = []
        matches = re.finditer(MarkdownParser.SCREENSHOT_PATTERN, markdown)

        for match in matches:
            mm = match.group(1)
            ss = match.group(2)

            total_seconds = int(mm) * 60 + int(ss)
            marker_text = match.group(0)

            # 验证时间戳有效性
            if video_duration and total_seconds > video_duration:
                logger.warning(
                    f"[MarkdownParser] 时间戳超出视频长度: {marker_text} "
                    f"({total_seconds}s > {video_duration}s)，将跳过"
                )
                continue

            results.append((marker_text, float(total_seconds)))
            logger.debug(f"[MarkdownParser] 提取到截图标记: {marker_text} -> {total_seconds}s")

        # 按时间顺序排序
        results.sort(key=lambda x: x[1])

        logger.info(f"[MarkdownParser] 提取完成，共找到 {len(results)} 个有效截图标记")
        return results

    @staticmethod
    def validate_and_deduplicate(
        timestamps: List[Tuple[str, float]],
        min_interval: float = 15.0
    ) -> List[Tuple[str, float]]:
        """
        验证并去重时间戳（过滤间隔过近的标记）

        Args:
            timestamps: 时间戳列表 [(标记文本, 秒数), ...]
            min_interval: 最小时间间隔（秒），默认15秒

        Returns:
            List[Tuple[str, float]]: 过滤后的时间戳列表
        """
        if not timestamps:
            return []

        filtered = [timestamps[0]]  # 保留第一个

        for marker, ts in timestamps[1:]:
            # 检查与最后一个保留的时间戳的间隔
            if ts - filtered[-1][1] >= min_interval:
                filtered.append((marker, ts))
            else:
                logger.warning(
                    f"[MarkdownParser] 时间戳过于接近，跳过: {marker} "
                    f"(间隔: {ts - filtered[-1][1]:.1f}s < {min_interval}s)"
                )

        logger.info(f"[MarkdownParser] 去重后保留 {len(filtered)}/{len(timestamps)} 个时间戳")
        return filtered

    @staticmethod
    def convert_to_timepoint_suggestions(
        timestamps: List[Tuple[str, float]],
        default_window: float = 2.0
    ) -> List[TimepointSuggestion]:
        """
        将解析的时间戳转换为 TimepointSuggestion 格式

        Args:
            timestamps: 时间戳列表 [(标记文本, 秒数), ...]
            default_window: 默认截图时间窗口（秒）

        Returns:
            List[TimepointSuggestion]: 时间点建议列表
        """
        timepoints = []

        for marker, seconds in timestamps:
            # 转换为 M:SS 或 MM:SS 格式（与现有系统兼容）
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            timestamp_str = f"{minutes}:{secs:02d}"

            timepoint = TimepointSuggestion(
                timestamp=timestamp_str,
                reason="GPT 标记的重要时刻",
                importance="高",
                category="GPT标记",
                window=default_window
            )

            timepoints.append(timepoint)

        logger.info(f"[MarkdownParser] 创建了 {len(timepoints)} 个 TimepointSuggestion")
        return timepoints

    @staticmethod
    def replace_markers_with_images(
        markdown: str,
        screenshot_mapping: Dict[str, str],
        fallback: str = None
    ) -> str:
        """
        替换 Markdown 中的截图标记为实际图片链接

        Args:
            markdown: 原始 Markdown 文本
            screenshot_mapping: 时间戳到图片URL的映射
                格式: {"3:39": "http://.../screenshot.jpg", "12:05": "..."}
                注意: key 格式为 M:SS 或 MM:SS（不带前导零的分钟）
            fallback: 当截图生成失败时的替换文本
                - None (默认): 删除标记
                - 空字符串 "": 保留原标记
                - 其他字符串: 用该字符串替换

        Returns:
            str: 替换后的 Markdown
        """
        logger.info(f"[MarkdownParser] 开始替换截图标记，映射数量: {len(screenshot_mapping)}")

        replaced_count = 0
        failed_count = 0

        def replacer(match):
            nonlocal replaced_count, failed_count

            mm = match.group(1)
            ss = match.group(2)

            # 转换为标准格式（去掉分钟的前导零）
            minutes = int(mm)
            seconds = int(ss)
            timestamp_key = f"{minutes}:{seconds:02d}"

            # 查找对应的图片URL
            if timestamp_key in screenshot_mapping:
                image_url = screenshot_mapping[timestamp_key]
                replaced_count += 1
                # 生成 Markdown 图片语法
                return f"\n![截图 @ {minutes:02d}:{seconds:02d}]({image_url})\n"
            else:
                failed_count += 1
                logger.warning(f"[MarkdownParser] 未找到时间戳 {timestamp_key} 的截图")

                # 根据 fallback 参数决定如何处理
                if fallback is None:
                    # None 表示删除标记
                    return ""
                elif fallback == "":
                    # 空字符串表示保留原标记
                    return match.group(0)
                else:
                    # 其他字符串用作替换
                    return fallback

        result = re.sub(MarkdownParser.SCREENSHOT_PATTERN, replacer, markdown)

        logger.info(
            f"[MarkdownParser] 替换完成: 成功 {replaced_count} 个，"
            f"失败 {failed_count} 个"
        )

        return result

    @staticmethod
    def build_screenshot_mapping(
        selected_screenshots: List,
        base_url: str = "/static/screenshots"
    ) -> Dict[str, str]:
        """
        构建时间戳到截图URL的映射

        Args:
            selected_screenshots: ScreenshotSelectionResult 列表
            base_url: 图片URL基础路径

        Returns:
            Dict[str, str]: 时间戳到图片URL的映射
        """
        mapping = {}

        for screenshot_result in selected_screenshots:
            timepoint = screenshot_result.timepoint  # 格式可能是 "3:39" 或 "3:39.00"

            # 标准化时间戳格式
            try:
                # 处理可能带小数的时间戳
                if '.' in timepoint:
                    timepoint = timepoint.split('.')[0]

                parts = timepoint.split(':')
                if len(parts) == 2:
                    mm = int(parts[0])
                    ss = int(parts[1])
                    normalized_timestamp = f"{mm}:{ss:02d}"
                else:
                    logger.warning(f"[MarkdownParser] 时间戳格式异常: {timepoint}")
                    continue
            except Exception as e:
                logger.warning(f"[MarkdownParser] 时间戳格式化失败: {timepoint}, {e}")
                continue

            # 获取选中的图片路径
            if screenshot_result.selected:
                image_path = screenshot_result.selected[0]

                # 构建完整URL
                # 提取文件名
                filename = image_path.replace('\\', '/').split('/')[-1]
                image_url = f"{base_url}/{filename}"

                mapping[normalized_timestamp] = image_url
                logger.debug(f"[MarkdownParser] 映射: {normalized_timestamp} -> {image_url}")

        logger.info(f"[MarkdownParser] 构建映射完成，共 {len(mapping)} 个时间戳")
        return mapping
