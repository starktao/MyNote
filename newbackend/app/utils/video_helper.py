"""
Video Helper Utilities - 视频处理工具类
提供视频文件验证、时间戳解析、截图生成等功能
"""

import os
import subprocess
import re
import uuid
from typing import List, Tuple, Optional
import logging

from app.models.dto.screenshot_dto import ScreenshotCandidate, ScreenshotGenerationConfig

logger = logging.getLogger(__name__)

class VideoHelper:
    """视频处理工具类"""

    @staticmethod
    def validate_video_file(video_path: str) -> bool:
        """
        验证视频文件是否有效

        Args:
            video_path: 视频文件路径

        Returns:
            bool: 文件是否有效

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或文件损坏
        """
        try:
            logger.info(f"[VIDEO_HELPER] 验证视频文件: {video_path}")

            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            # 使用ffprobe检查视频文件
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name,width,height,duration',
                '-of', 'json',
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise ValueError(f"视频文件格式无效或损坏: {result.stderr}")

            import json
            probe_data = json.loads(result.stdout)

            if not probe_data.get('streams'):
                raise ValueError("视频文件中没有找到视频流")

            stream = probe_data['streams'][0]
            duration = float(stream.get('duration', 0))

            if duration <= 0:
                raise ValueError("视频文件时长无效")

            logger.info(f"[VIDEO_HELPER] 视频文件验证成功: {video_path}, 时长: {duration:.2f}秒")
            return True

        except subprocess.TimeoutExpired:
            raise ValueError("视频文件验证超时")
        except json.JSONDecodeError as e:
            raise ValueError(f"视频文件解析失败: {e}")
        except Exception as e:
            logger.error(f"[VIDEO_HELPER] 视频文件验证失败: {e}")
            raise ValueError(f"视频文件验证失败: {e}")

    @staticmethod
    def parse_timestamp_to_seconds(timestamp: str) -> float:
        """
        将时间戳转换为秒数

        Args:
            timestamp: 时间戳，支持格式：
                      - "分:秒" 如 "1:30"
                      - "时:分:秒" 如 "0:1:30"
                      - 纯秒数 如 "90"

        Returns:
            float: 秒数

        Raises:
            ValueError: 时间戳格式无效
        """
        try:
            if isinstance(timestamp, (int, float)):
                return float(timestamp)

            timestamp = str(timestamp).strip()

            # 处理不同格式的时间戳
            if ':' in timestamp:
                parts = timestamp.split(':')
                if len(parts) == 2:  # 分:秒
                    minutes, seconds = parts
                    return int(minutes) * 60 + float(seconds)
                elif len(parts) == 3:  # 时:分:秒
                    hours, minutes, seconds = parts
                    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                else:
                    raise ValueError(f"不支持的时间戳格式: {timestamp}")
            else:
                # 纯数字，当作秒数处理
                return float(timestamp)

        except ValueError as e:
            raise ValueError(f"无效的时间戳格式 '{timestamp}': {e}")
        except Exception as e:
            raise ValueError(f"时间戳解析失败 '{timestamp}': {e}")

    @staticmethod
    def parse_seconds_to_timestamp(seconds: float) -> str:
        """
        将秒数转换为时间戳格式

        Args:
            seconds: 秒数

        Returns:
            str: "分:秒" 格式的时间戳
        """
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:05.2f}"

    @staticmethod
    def calculate_screenshot_range(
        base_timestamp: str,
        window: float,
        count: int = 5
    ) -> List[float]:
        """
        计算候选截图的时间戳列表

        Args:
            base_timestamp: 基准时间戳
            window: 时间窗口大小（秒）
            count: 候选截图数量

        Returns:
            List[float]: 截图时间戳列表（秒数）
        """
        try:
            base_seconds = VideoHelper.parse_timestamp_to_seconds(base_timestamp)

            # 计算时间范围
            start_time = max(0, base_seconds - window / 2)
            end_time = base_seconds + window / 2

            # 生成均匀分布的时间戳
            if count == 1:
                return [base_seconds]

            interval = (end_time - start_time) / (count - 1)
            timestamps = [start_time + i * interval for i in range(count)]

            logger.info(f"[VIDEO_HELPER] 计算截图范围: {base_timestamp}±{window}s, 生成{len(timestamps)}个时间点")
            return timestamps

        except Exception as e:
            logger.error(f"[VIDEO_HELPER] 计算截图范围失败: {e}")
            raise ValueError(f"计算截图范围失败: {e}")

    @staticmethod
    def generate_screenshot(
        video_path: str,
        timestamp: float,
        output_path: str,
        config: ScreenshotGenerationConfig = None
    ) -> ScreenshotCandidate:
        """
        生成单个截图

        Args:
            video_path: 视频文件路径
            timestamp: 截图时间点（秒）
            output_path: 输出文件路径
            config: 截图配置

        Returns:
            ScreenshotCandidate: 截图候选对象

        Raises:
            RuntimeError: 截图生成失败
        """
        try:
            if config is None:
                config = ScreenshotGenerationConfig()

            logger.info(f"[VIDEO_HELPER] 生成截图: {video_path} @ {timestamp}s -> {output_path}")

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-y',  # 覆盖输出文件
            ]

            # 添加质量参数
            cmd.extend(config.get_ffmpeg_quality_args())

            # 添加分辨率参数
            if config.resolution:
                cmd.extend(['-s', config.resolution])

            # 添加输出路径
            cmd.append(output_path)

            # 执行截图命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"FFmpeg截图失败: {error_msg}")

            # 验证生成的截图文件
            if not os.path.exists(output_path):
                raise RuntimeError("截图文件未生成")

            file_size = os.path.getsize(output_path)
            if file_size == 0:
                os.remove(output_path)
                raise RuntimeError("生成的截图文件为空")

            # 创建截图候选对象
            timestamp_str = VideoHelper.parse_seconds_to_timestamp(timestamp)
            candidate = ScreenshotCandidate(
                url=output_path,
                timestamp=timestamp_str,
                file_path=output_path,
                description=f"截图 @ {timestamp_str}",
                file_size=file_size
            )

            logger.info(f"[VIDEO_HELPER] 截图生成成功: {output_path}, 大小: {file_size}字节")
            return candidate

        except subprocess.TimeoutExpired:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError("FFmpeg截图超时")
        except Exception as e:
            # 清理可能生成的无效文件
            if os.path.exists(output_path):
                os.remove(output_path)
            logger.error(f"[VIDEO_HELPER] 截图生成失败: {e}")
            raise RuntimeError(f"截图生成失败: {e}")

    @staticmethod
    def generate_candidate_screenshots(
        video_path: str,
        base_timestamp: str,
        window: float,
        candidate_count: int = 5,
        output_dir: str = None,
        config: ScreenshotGenerationConfig = None
    ) -> List[ScreenshotCandidate]:
        """
        为指定时间点生成候选截图

        Args:
            video_path: 视频文件路径
            base_timestamp: 基准时间戳
            window: 时间窗口大小（秒）
            candidate_count: 候选截图数量
            output_dir: 输出目录
            config: 截图配置

        Returns:
            List[ScreenshotCandidate]: 候选截图列表

        Raises:
            RuntimeError: 截图生成失败
        """
        try:
            if output_dir is None:
                output_dir = os.path.join(os.path.dirname(video_path), 'screenshots')

            if config is None:
                config = ScreenshotGenerationConfig()

            logger.info(f"[VIDEO_HELPER] 生成候选截图: {base_timestamp}±{window}s, 数量: {candidate_count}")

            # 计算候选时间点
            candidate_timestamps = VideoHelper.calculate_screenshot_range(
                base_timestamp, window, candidate_count
            )

            candidates = []
            errors = []

            # 生成每个候选截图
            for i, timestamp in enumerate(candidate_timestamps):
                try:
                    # 生成唯一的文件名
                    unique_id = str(uuid.uuid4())[:8]
                    timestamp_str = VideoHelper.parse_seconds_to_timestamp(timestamp).replace(':', '')
                    filename = f"candidate_{i}_{timestamp_str}_{unique_id}.{config.format}"
                    output_path = os.path.join(output_dir, filename)

                    candidate = VideoHelper.generate_screenshot(
                        video_path, timestamp, output_path, config
                    )

                    candidates.append(candidate)

                except Exception as e:
                    error_msg = f"生成候选截图{i}失败 ({timestamp}s): {e}"
                    errors.append(error_msg)
                    logger.error(f"[VIDEO_HELPER] {error_msg}")

            if not candidates and errors:
                raise RuntimeError(f"所有候选截图生成失败: {'; '.join(errors)}")
            elif errors:
                logger.warning(f"[VIDEO_HELPER] 部分截图生成失败: {'; '.join(errors)}")

            logger.info(f"[VIDEO_HELPER] 候选截图生成完成: {len(candidates)}/{candidate_count} 成功")
            return candidates

        except Exception as e:
            logger.error(f"[VIDEO_HELPER] 候选截图生成失败: {e}")
            raise RuntimeError(f"候选截图生成失败: {e}")

    @staticmethod
    def cleanup_temporary_files(file_paths: List[str]):
        """
        清理临时文件

        Args:
            file_paths: 要清理的文件路径列表
        """
        try:
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.debug(f"[VIDEO_HELPER] 已清理临时文件: {file_path}")
                except Exception as e:
                    logger.warning(f"[VIDEO_HELPER] 清理文件失败 {file_path}: {e}")
        except Exception as e:
            logger.warning(f"[VIDEO_HELPER] 清理临时文件时发生错误: {e}")

    @staticmethod
    def get_video_duration(video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            float: 视频时长（秒）
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"获取视频时长失败: {result.stderr}")

            duration = float(result.stdout.strip())
            return duration

        except Exception as e:
            logger.error(f"[VIDEO_HELPER] 获取视频时长失败: {e}")
            raise RuntimeError(f"获取视频时长失败: {e}")