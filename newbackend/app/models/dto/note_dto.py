"""
Note Related DTOs
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class NoteRequestDTO(BaseModel):
    model_config = {"protected_namespaces": ()}  # 允许 model_ 开头的字段名

    video_url: str = Field(..., description="视频URL或本地路径")
    platform: str = Field(default="bilibili", description="视频平台")
    quality: str = Field(default="fast", description="音频质量")
    model_name: str = Field(..., description="AI模型名称")
    provider_id: str = Field(..., description="AI提供商ID")
    style: str = Field(default="concise", description="笔记风格")
    format: List[str] = Field(default=["outline"], description="笔记格式")
    extras: Optional[str] = Field(None, description="额外指令")
    screenshot: bool = Field(default=False, description="是否截图")
    link: bool = Field(default=True, description="是否包含原链接")
    task_id: Optional[str] = Field(None, description="任务ID（用于重试）")


class NoteResponseDTO(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    screenshots: Optional[List[str]] = None


class BatchNoteRequestDTO(BaseModel):
    items: List[NoteRequestDTO]
    max_concurrency: int = Field(default=3, description="最大并发数")


class TaskStatusDTO(BaseModel):
    task_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None