"""
Screenshot related DTOs and Models
截图相关的数据传输对象和模型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TimepointSuggestion(BaseModel):
    """时间点建议模型"""
    timestamp: str = Field(..., description="时间戳，格式：分:秒")
    reason: str = Field(..., description="为什么这个时刻很重要")
    importance: str = Field(..., description="重要性等级：高/中高/中")
    category: str = Field(..., description="内容类别")
    window: float = Field(2.0, description="截图时间窗口大小（秒）")

    def to_seconds(self) -> float:
        """将时间戳转换为秒数"""
        try:
            minutes, seconds = self.timestamp.split(':')
            return int(minutes) * 60 + float(seconds)
        except Exception as e:
            raise ValueError(f"Invalid timestamp format: {self.timestamp}") from e

class ScreenshotCandidate(BaseModel):
    """截图候选模型"""
    url: str = Field(..., description="截图URL或文件路径")
    timestamp: str = Field(..., description="截图时间戳")
    file_path: str = Field(..., description="截图文件路径")
    description: Optional[str] = Field(None, description="截图描述")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    def get_filename(self) -> str:
        """获取文件名"""
        return self.file_path.split('/')[-1] if '/' in self.file_path else self.file_path

class ScreenshotAnalysisRequest(BaseModel):
    """截图分析请求模型"""
    task_id: str = Field(..., description="任务ID")
    video_path: str = Field(..., description="视频文件路径")
    transcript_segments: List[Dict[str, Any]] = Field(..., description="转写片段列表")
    screenshot_enabled: bool = Field(True, description="是否启用截图")
    screenshot_mode: str = Field("smart", description="截图模式：smart/timestamp")
    screenshot_window: float = Field(2.0, description="截图时间窗口（秒）")
    screenshot_candidates: int = Field(5, description="每个时间点的候选截图数量")
    video_type_hint: Optional[str] = Field(None, description="视频类型提示")

class ScreenshotSelectionRequest(BaseModel):
    """截图选择请求模型"""
    timepoint: TimepointSuggestion = Field(..., description="时间点信息")
    content_description: str = Field(..., description="内容描述")
    context: str = Field(..., description="上下文信息")
    video_type: str = Field(..., description="视频类型")
    candidates: List[ScreenshotCandidate] = Field(..., description="候选截图列表")

class ScreenshotSelectionResult(BaseModel):
    """截图选择结果模型"""
    selected: List[str] = Field(..., description="选中的截图URL或文件路径")
    reasons: List[str] = Field(..., description="选择理由")
    content_representativeness: str = Field(..., description="内容代表性：high/medium/low")
    timepoint: str = Field(..., description="时间点")
    analysis_time: datetime = Field(default_factory=datetime.now, description="分析时间")
    info_score: Optional[float] = Field(None, description="信息评分(0-1)，用于去重时比较")
    hash_value: Optional[str] = Field(None, description="图片感知哈希值，用于去重检测")

class ScreenshotProcessResult(BaseModel):
    """截图处理结果模型"""
    task_id: str = Field(..., description="任务ID")
    video_type: str = Field(..., description="视频类型")
    total_timepoints: int = Field(..., description="处理的时间点总数")
    successful_screenshots: int = Field(..., description="成功生成的截图数量")
    selected_screenshots: List[ScreenshotSelectionResult] = Field(..., description="选中的截图结果")
    processing_time: float = Field(..., description="处理耗时（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    deduplicated_count: Optional[int] = Field(None, description="去重删除的截图数量")

class VideoContentType(BaseModel):
    """视频内容类型分析结果"""
    video_type: str = Field(..., description="视频类型：教育/娱乐/科技/生活/混合")
    confidence: float = Field(..., description="类型识别置信度")
    characteristics: List[str] = Field(..., description="内容特征列表")

class ScreenshotGenerationConfig(BaseModel):
    """截图生成配置"""
    quality: int = Field(1, description="截图质量等级 1-5")
    resolution: Optional[str] = Field("1280x720", description="截图分辨率")
    format: str = Field("jpg", description="截图格式")
    max_concurrent: int = Field(3, description="最大并发截图数")
    cleanup_temp: bool = Field(True, description="是否清理临时文件")

    def get_ffmpeg_quality_args(self) -> List[str]:
        """获取FFmpeg质量参数"""
        quality_map = {
            1: ["-q:v", "1", "-crf", "18"],  # 最高质量
            2: ["-q:v", "2", "-crf", "20"],
            3: ["-q:v", "3", "-crf", "23"],
            4: ["-q:v", "4", "-crf", "26"],
            5: ["-q:v", "5", "-crf", "28"]   # 较低质量
        }
        return quality_map.get(self.quality, quality_map[3])