from dataclasses import dataclass
from typing import Optional, Literal

Quality = Literal["fast", "medium", "slow"]
QUALITY_MAP = {"fast": "32", "medium": "64", "slow": "128"}


@dataclass
class DownloadResult:
    file_path: str
    cover_url: str
    platform: str
    title: str
    duration: float
    raw_info: dict
    video_id: str


class Downloader:
    def download(
        self,
        video_url: str,
        output_dir: Optional[str] = None,
        quality: Quality = "fast",
        need_video: bool = False,
    ) -> DownloadResult:
        raise NotImplementedError

