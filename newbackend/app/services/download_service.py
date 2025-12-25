"""
Download Service - Video/Audio Download Processing
支持音频和视频下载，为截图功能提供视频文件
"""

import os
import json
import uuid
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from pydantic import HttpUrl

import yt_dlp

logger = logging.getLogger(__name__)


class DownloadService:
    """Service for downloading video/audio from various platforms"""

    def __init__(self):
        """Initialize download service"""
        self.cache_dir = Path(tempfile.gettempdir()) / "mynote_downloads"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.service_name = "DownloadService"
        logger.info(f"[{self.service_name}] 下载服务初始化完成")

    def download(self, video_url: Union[str, HttpUrl], quality: str = "fast",
                output_dir: Optional[str] = None, need_video: bool = False) -> Dict[str, Any]:
        """
        Download audio/video from URL

        Args:
            video_url: Video or audio URL
            quality: Download quality ('fast', 'medium', 'slow')
            output_dir: Output directory (optional)
            need_video: Whether video download is required for screenshots

        Returns:
            Dict with download results

        Raises:
            Exception: Download failed
        """
        try:
            logger.info(f"[{self.service_name}] 开始下载: {video_url}, 需要视频: {need_video}")

            if output_dir is None:
                output_dir = self.cache_dir

            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            download_id = str(uuid.uuid4())[:8]

            # 首先按照原有逻辑下载音频（这个是成功的）
            audio_result = self._download_audio(video_url, quality, output_dir, download_id)

            if need_video:
                # 如果需要截图，额外下载视频
                try:
                    logger.info(f"[{self.service_name}] 额外下载视频用于截图")
                    video_result = self._download_video_simple(video_url, quality, output_dir, f"{download_id}_video")

                    # 合并结果
                    result = {
                        "audio_path": audio_result["audio_path"],
                        "video_path": video_result["video_path"],
                        "video_info": {
                            **audio_result["video_info"],
                            "download_type": "video_and_audio"
                        }
                    }
                except Exception as video_error:
                    logger.warning(f"[{self.service_name}] 视频下载失败，继续使用音频: {video_error}")
                    # 视频下载失败，只返回音频结果
                    result = audio_result
                    result["video_info"]["download_type"] = "audio_only_video_failed"
            else:
                result = audio_result

            logger.info(f"[{self.service_name}] 下载完成: {result['video_info']['title']}")
            return result

        except Exception as e:
            logger.error(f"[{self.service_name}] 下载失败: {str(e)}")
            raise Exception(f"下载失败: {str(e)}")

    def _download_audio(self, video_url: Union[str, HttpUrl], quality: str,
                       output_dir: Path, download_id: str) -> Dict[str, Any]:
        """下载音频文件用于转录"""
        try:
            output_template = str(output_dir / f"{download_id}_audio.%(ext)s")

            # 音频质量设置
            quality_settings = {
                "fast": {"preferredquality": "64", "audio_format": "m4a"},
                "medium": {"preferredquality": "128", "audio_format": "m4a"},
                "slow": {"preferredquality": "192", "audio_format": "m4a"}
            }

            settings = quality_settings.get(quality, quality_settings["medium"])

            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'outtmpl': output_template,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': settings["audio_format"],
                        'preferredquality': settings["preferredquality"],
                    }
                ],
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            return self._execute_download(video_url, ydl_opts, output_dir, download_id, audio_only=True)

        except Exception as e:
            logger.error(f"[{self.service_name}] 音频下载失败: {e}")
            raise Exception(f"音频下载失败: {e}")

    def _download_video_simple(self, video_url: Union[str, HttpUrl], quality: str,
                            output_dir: Path, download_id: str) -> Dict[str, Any]:
        """简化版视频下载用于截图 - 使用原始项目的成功方案"""
        try:
            video_template = str(output_dir / f"%(id)s.%(ext)s")

            # 检测平台并使用对应的格式
            platform = self._detect_platform(str(video_url))

            if platform == "bilibili":
                # 使用原始项目中B站专用的成功格式
                video_opts = {
                    'format': 'bv*[ext=mp4]/bestvideo+bestaudio/best',
                    'outtmpl': video_template,
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'writesubtitles': False,
                    'writeautomaticsub': False,
                    'merge_output_format': 'mp4',  # 确保合并成 mp4
                }
                logger.info(f"[{self.service_name}] 使用B站专用视频格式")
            else:
                # 其他平台使用通用格式
                video_opts = {
                    'format': 'bestvideo[ext=mp4]/bestvideo+bestaudio/best',
                    'outtmpl': video_template,
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'writesubtitles': False,
                    'writeautomaticsub': False,
                    'merge_output_format': 'mp4',
                }
                logger.info(f"[{self.service_name}] 使用通用视频格式")

            logger.info(f"[{self.service_name}] 开始视频下载: {video_url}")

            with yt_dlp.YoutubeDL(video_opts) as ydl:
                # 下载视频文件
                info = ydl.extract_info(str(video_url), download=True)
                video_id = info.get("id", "")

                # 根据原始项目的逻辑，生成视频文件路径
                video_file = os.path.join(output_dir, f"{video_id}.mp4")

                if not os.path.exists(video_file):
                    raise FileNotFoundError(f"视频文件未找到: {video_file}")

                logger.info(f"[{self.service_name}] 视频下载完成: {video_file}")
                return {
                    "video_path": video_file,
                    "video_info": {
                        "video_id": video_id,
                        "title": info.get("title", "Unknown Title"),
                        "duration": info.get("duration", 0),
                        "uploader": info.get("uploader", ""),
                        "upload_date": info.get("upload_date", ""),
                        "platform": platform,
                        "download_type": "video_only",
                        "path": video_file
                    }
                }

        except Exception as e:
            logger.error(f"[{self.service_name}] 视频下载失败: {e}")
            raise Exception(f"视频下载失败: {e}")

    def _download_video_complex(self, video_url: Union[str, HttpUrl], quality: str,
                              output_dir: Path, download_id: str) -> Dict[str, Any]:
        """复杂版视频下载（备用）"""
        try:
            video_template = str(output_dir / f"{download_id}_video.%(ext)s")
            audio_template = str(output_dir / f"{download_id}_audio.%(ext)s")

            # 检测平台并选择合适的格式
            platform = self._detect_platform(str(video_url))

            if platform == "bilibili":
                # B站专用格式选择
                video_format_map = {
                    "fast": "dash-flv-720",
                    "medium": "dash-flv-1080",
                    "slow": "dash-flv-1080"
                }
                video_format = video_format_map.get(quality, video_format_map["medium"])
            else:
                # 通用格式选择
                video_format_map = {
                    "fast": "worstvideo+worstaudio/worst",
                    "medium": "bestvideo[height<=720]+bestaudio/best",
                    "slow": "bestvideo+bestaudio/best"
                }
                video_format = video_format_map.get(quality, video_format_map["medium"])

            # 首先尝试下载视频文件
            video_opts = {
                'format': video_format,
                'outtmpl': video_template,
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }

            try:
                video_result = self._execute_download(video_url, video_opts, output_dir, download_id, audio_only=False)
            except Exception as video_error:
                logger.warning(f"[{self.service_name}] 视频下载失败，尝试使用通用格式: {video_error}")
                # 备用方案：使用最通用的格式
                fallback_opts = {
                    'format': 'best',
                    'outtmpl': video_template,
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                }
                video_result = self._execute_download(video_url, fallback_opts, output_dir, download_id, audio_only=False)

            return video_result

        except Exception as e:
            logger.error(f"[{self.service_name}] 复杂视频下载失败: {e}")
            raise Exception(f"复杂视频下载失败: {e}")

    def _execute_download(self, video_url: Union[str, HttpUrl], ydl_opts: Dict[str, Any],
                         output_dir: Path, download_id: str, audio_only: bool = True) -> Dict[str, Any]:
        """执行下载操作"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 提取视频信息
                info = ydl.extract_info(str(video_url), download=False)

                # 提取元数据
                video_id = info.get("id", "")
                title = info.get("title", "Unknown Title")
                duration = info.get("duration", 0)
                uploader = info.get("uploader", "")
                upload_date = info.get("upload_date", "")
                description = info.get("description", "")

                logger.info(f"[{self.service_name}] 视频信息: {title} ({duration}s)")

                # 下载文件
                info = ydl.extract_info(str(video_url), download=True)

                # 获取下载的文件路径
                downloaded_file = ydl.prepare_filename(info)

                if audio_only:
                    # 音频文件处理
                    audio_file = self._find_audio_file(downloaded_file, "m4a")
                    if not audio_file or not os.path.exists(audio_file):
                        raise Exception("音频文件未找到")

                    logger.info(f"[{self.service_name}] 音频下载完成: {audio_file}")
                    return {
                        "audio_path": audio_file,
                        "video_info": {
                            "video_id": video_id,
                            "title": title,
                            "duration": duration,
                            "uploader": uploader,
                            "upload_date": upload_date,
                            "platform": self._detect_platform(str(video_url)),
                            "download_type": "audio_only",
                            "path": audio_file
                        }
                    }
                else:
                    # 视频文件处理
                    video_file = self._find_video_file(downloaded_file)
                    if not video_file or not os.path.exists(video_file):
                        raise Exception("视频文件未找到")

                    logger.info(f"[{self.service_name}] 视频下载完成: {video_file}")
                    return {
                        "video_path": video_file,
                        "video_info": {
                            "video_id": video_id,
                            "title": title,
                            "duration": duration,
                            "uploader": uploader,
                            "upload_date": upload_date,
                            "platform": self._detect_platform(str(video_url)),
                            "download_type": "video_only",
                            "path": video_file
                        }
                    }

        except Exception as e:
            logger.error(f"[{self.service_name}] 执行下载失败: {e}")
            raise Exception(f"执行下载失败: {e}")

    def _find_audio_file(self, original_path: str, audio_format: str) -> Optional[str]:
        """Find the actual audio file after post-processing"""
        base_path = Path(original_path)

        # Try different possible extensions
        for ext in [f".{audio_format}", ".mp3", ".m4a", ".wav"]:
            candidate = base_path.with_suffix(ext)
            if candidate.exists():
                return str(candidate)

        # Try removing any existing extension and adding the audio format
        no_ext = base_path.with_suffix('')
        candidate = no_ext.with_suffix(f".{audio_format}")
        if candidate.exists():
            return str(candidate)

        # Search in the same directory
        parent_dir = base_path.parent
        base_name = base_path.stem
        for ext in [f".{audio_format}", ".mp3", ".m4a", ".wav"]:
            candidate = parent_dir / f"{base_name}{ext}"
            if candidate.exists():
                return str(candidate)

        return None

    def _find_video_file(self, original_path: str) -> Optional[str]:
        """Find the actual video file after download"""
        base_path = Path(original_path)

        # Try common video extensions
        video_extensions = [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"]

        # First try the original path
        if base_path.exists() and base_path.suffix.lower() in video_extensions:
            return str(base_path)

        # Try different extensions
        for ext in video_extensions:
            candidate = base_path.with_suffix(ext)
            if candidate.exists():
                return str(candidate)

        # Search in the same directory for files with the same base name
        parent_dir = base_path.parent
        base_name = base_path.stem
        for ext in video_extensions:
            candidate = parent_dir / f"{base_name}{ext}"
            if candidate.exists():
                return str(candidate)

        # List all files in the directory and look for video files
        try:
            for file_path in parent_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    if base_name in file_path.name or file_path.stat().st_size > 10 * 1024 * 1024:  # > 10MB
                        logger.info(f"[{self.service_name}] 找到候选视频文件: {file_path}")
                        return str(file_path)
        except Exception as e:
            logger.warning(f"[{self.service_name}] 搜索视频文件失败: {e}")

        return None

    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL"""
        url_lower = url.lower()

        if "bilibili.com" in url_lower:
            return "bilibili"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "douyin.com" in url_lower:
            return "douyin"
        elif "kuaishou.com" in url_lower:
            return "kuaishou"
        else:
            return "generic"

    def get_video_info(self, video_url: Union[str, HttpUrl]) -> Dict[str, Any]:
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(str(video_url), download=False)

                return {
                    "video_id": info.get("id", ""),
                    "title": info.get("title", "Unknown Title"),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", ""),
                    "upload_date": info.get("upload_date", ""),
                    "description": info.get("description", ""),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "platform": self._detect_platform(str(video_url))
                }

        except Exception as e:
            print(f"[ERROR] Failed to get video info: {str(e)}")
            raise Exception(f"Failed to get video info: {str(e)}")