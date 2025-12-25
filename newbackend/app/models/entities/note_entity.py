"""
Note Business Entity
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


class NoteEntity:
    def __init__(
        self,
        id: str,
        video_url: str,
        platform: str,
        model_name: str,
        provider_id: str,
        status: str = "PENDING",
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        screenshots: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.video_url = video_url
        self.platform = platform
        self.model_name = model_name
        self.provider_id = provider_id
        self.status = status
        self.message = message
        self.result = result or {}
        self.screenshots = screenshots or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def update_status(self, status: str, message: Optional[str] = None):
        self.status = status
        if message:
            self.message = message
        self.updated_at = datetime.now()

    def add_result(self, result: Dict[str, Any]):
        self.result.update(result)
        self.updated_at = datetime.now()

    def add_screenshot(self, screenshot_path: str):
        if screenshot_path not in self.screenshots:
            self.screenshots.append(screenshot_path)
        self.updated_at = datetime.now()