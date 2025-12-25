from .base import Downloader, DownloadResult, QUALITY_MAP
from pathlib import Path
import yt_dlp  # type: ignore
import uuid
import os
import shutil


class YtDlpDownloader(Downloader):
    def download(
        self,
        video_url: str,
        output_dir: str | None = None,
        quality: str = "fast",
        need_video: bool = False,
    ) -> DownloadResult:
        # Local file shortcut for testing
        if video_url.startswith("file://"):
            local_path = video_url[len("file://") :]
            if not os.path.exists(local_path):
                raise FileNotFoundError(local_path)
            return DownloadResult(
                file_path=local_path,
                cover_url="",
                platform="local",
                title=Path(local_path).stem,
                duration=0.0,
                raw_info={},
                video_id=Path(local_path).stem,
            )
        if os.path.exists(video_url):
            return DownloadResult(
                file_path=video_url,
                cover_url="",
                platform="local",
                title=Path(video_url).stem,
                duration=0.0,
                raw_info={},
                video_id=Path(video_url).stem,
            )
        out_dir = Path(output_dir or "data")
        out_dir.mkdir(parents=True, exist_ok=True)
        uid = uuid.uuid4().hex[:8]
        outtmpl = str(out_dir / f"{uid}.%(ext)s")
        fmt = "best" if need_video else "bestaudio/best"
        q = QUALITY_MAP.get(quality, "32")

        print(f"[DOWNLOAD] 初始化下载器:")
        print(f"   - 输出目录: {out_dir}")
        print(f"   - 文件UID: {uid}")
        print(f"   - 输出模板: {outtmpl}")
        print(f"   - 格式: {fmt}")
        print(f"   - 质量: {q}")

        archive = str(Path(out_dir) / "download.archive")
        ffmpeg_location_env = os.getenv("FFMPEG_LOCATION") or os.getenv("FFMPEG_BINARY")
        ffmpeg_dir: str | None = None
        if ffmpeg_location_env:
            # allow either pointing to the directory or to the binary path
            p = Path(ffmpeg_location_env)
            ffmpeg_dir = str(p if p.is_dir() else p.parent)

        opts: dict = {
            "format": fmt,
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "prefer_ffmpeg": True,
            "noprogress": True,
            "retries": 3,
            "fragment_retries": 3,
            "download_archive": archive,
            # try to improve HLS/DASH performance
            "concurrent_fragment_downloads": 5,
            # postprocessors filled below when ffmpeg is available
        }
        if ffmpeg_dir:
            opts["ffmpeg_location"] = ffmpeg_dir

        ffmpeg_ok = bool(shutil.which("ffmpeg") or ffmpeg_dir)
        print(f"[DOWNLOAD] FFmpeg检查:")
        print(f"   - FFmpeg可用: {ffmpeg_ok}")
        print(f"   - FFmpeg路径: {shutil.which('ffmpeg')}")
        print(f"   - FFmpeg目录: {ffmpeg_dir}")

        if ffmpeg_ok:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": q,
                }
            ]
            opts["postprocessor_args"] = [
                "-ac",
                "1",
                "-ar",
                "16000",
                "-movflags",
                "+faststart",
            ]
            print(f"[DOWNLOAD] 启用音频后处理")

        # Simple retry loop for robustness
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                print(f"[DOWNLOAD] 尝试下载 (第{attempt+1}次):")
                with yt_dlp.YoutubeDL(opts) as ydl:
                    print(f"[DOWNLOAD] 正在提取视频信息...")
                    info = ydl.extract_info(video_url, False)
                    print(f"[DOWNLOAD] 视频信息提取成功: {info.get('title', 'unknown')}")
                    print(f"[DOWNLOAD] 开始下载文件...")
                    ydl.download([video_url])
                    print(f"[DOWNLOAD] 文件下载完成")
                break
            except Exception as e:
                last_exc = e
                print(f"[ERROR] 下载失败 (第{attempt+1}次): {e}")
                import time
                time.sleep(1.0)
        else:
            print(f"[ERROR] 下载重试次数已用尽，最后错误: {last_exc}")
            raise last_exc  # type: ignore

        # 查找实际生成的文件
        print(f"[DOWNLOAD] 查找下载的音频文件...")
        audio = None

        # 先列出目录中的所有文件进行调试
        print(f"[DEBUG] 扫描目录: {out_dir}")
        all_files = list(out_dir.glob("*"))
        print(f"[DEBUG] 目录中所有文件: {all_files}")

        # 查找匹配UID的文件
        uid_files = list(out_dir.glob(f"{uid}.*"))
        print(f"[DEBUG] 匹配UID {uid} 的文件: {uid_files}")

        # 优先使用UID匹配的文件
        for ext in ("m4a", "webm", "mp4", "mp3", "wav"):
            p = str(out_dir / f"{uid}.{ext}")
            if os.path.exists(p):
                audio = p
                print(f"[DOWNLOAD] 找到音频文件: {audio}")
                break

        # 如果没有找到UID匹配的文件，使用最新的音频文件
        if not audio:
            print(f"[WARNING] 没有找到UID匹配的文件，使用最新的音频文件")
            audio_files = []
            for ext in ("m4a", "webm", "mp4", "mp3", "wav"):
                audio_files.extend(list(out_dir.glob(f"*.{ext}")))

            if audio_files:
                # 按修改时间排序，选择最新的
                audio_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                audio = str(audio_files[0])
                print(f"[DOWNLOAD] 使用最新音频文件: {audio}")
            else:
                print(f"[ERROR] 没有找到任何音频文件")
                print(f"[DEBUG] UID: {uid}")
                print(f"[DEBUG] 输出目录: {out_dir}")
                print(f"[DEBUG] 目录内容:")
                for file in out_dir.iterdir():
                    print(f"   - {file.name} (大小: {file.stat().st_size if file.is_file() else 'N/A'} bytes)")
                raise FileNotFoundError(f"下载完成但未找到音频文件: {uid}.*")

        return DownloadResult(
            file_path=audio,
            cover_url=info.get("thumbnail") or "",
            platform=(info.get("extractor_key") or "generic").lower(),
            title=info.get("title") or "unknown",
            duration=float(info.get("duration") or 0),
            raw_info=info,
            video_id=info.get("id") or uid,
        )
