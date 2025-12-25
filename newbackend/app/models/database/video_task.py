"""
VideoTask Database Model
"""

import json
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from app.infrastructure.database import Base


class VideoTask(Base):
    __tablename__ = "video_task"

    id = Column(String, primary_key=True)
    batch_id = Column(String, ForeignKey("batch_task.id"))
    video_id = Column(String, index=True)
    platform = Column(String, index=True)
    source_url = Column(Text)
    status = Column(String, index=True, default="PENDING")
    message = Column(Text)
    quality = Column(String, default="fast")
    model_name = Column(String)
    provider_id = Column(String, ForeignKey("provider.id"))
    style = Column(String)
    video_type = Column(String, default="science")  # tech/dialogue/science/review
    note_style = Column(String, default="detailed")  # concise/detailed/teaching/xiaohongshu
    options = Column(Text)  # JSON string
    audio_path = Column(Text)
    result_path = Column(Text)
    transcript_path = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "ix_video_unique",
            "video_id",
            "platform",
            "model_name",
            "provider_id",
            "quality",
        ),
    )

    def to_history_dict(self) -> Dict[str, Any]:
        """将任务转换为历史记录格式，供前端展示"""
        # 解析 options JSON
        options_dict = {}
        if self.options:
            try:
                options_dict = json.loads(self.options)
            except json.JSONDecodeError:
                pass

        # 解析 result_path JSON 获取音频元数据
        audio_meta = {
            "title": "未知标题",
            "cover_url": "",
            "platform": self.platform or "generic",
            "video_id": self.video_id or ""
        }

        markdown_content = ""
        transcript_content = ""

        if self.result_path:
            try:
                result_data = json.loads(self.result_path)
                # 提取音频元数据
                if "audio_meta" in result_data:
                    meta = result_data["audio_meta"]
                    audio_meta.update({
                        "title": meta.get("title", "未知标题"),
                        "cover_url": meta.get("cover_url", ""),
                        "platform": meta.get("platform", self.platform or "generic"),
                        "video_id": meta.get("video_id", self.video_id or "")
                    })
                # 提取 markdown 和 transcript
                markdown_content = result_data.get("markdown", "")
                transcript_content = result_data.get("transcript", "")
            except json.JSONDecodeError:
                pass

        # 构建前端所需格式
        return {
            "id": self.id,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else "",
            "updatedAt": self.updated_at.isoformat() if self.updated_at else "",
            "markdown": markdown_content,
            "transcript": transcript_content,
            "audioMeta": audio_meta,
            "formData": {
                "video_url": self.source_url or "",
                "platform": self.platform or "generic",
                "model_name": self.model_name or "",
                "provider_id": self.provider_id or "",
                "quality": self.quality or "fast",
                "screenshot": options_dict.get("screenshot", False),
                "link": options_dict.get("link", False),
                "style": self.style or "concise",
                "video_type": self.video_type or "science",
                "note_style": self.note_style or "detailed",
                "format": options_dict.get("format", []),
                "extras": options_dict.get("extras", "")
            },
            "has_result": bool(self.result_path),
            "message": self.message or ""
        }