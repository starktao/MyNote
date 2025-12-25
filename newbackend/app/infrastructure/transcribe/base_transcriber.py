"""
转写器基类
参考BiliNote项目设计
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import time


@dataclass
class TranscriptSegment:
    """转写片段"""
    start: float  # 开始时间（秒）
    end: float    # 结束时间（秒）
    text: str     # 文本内容


@dataclass
class TranscriptResult:
    """转写结果"""
    language: Optional[str] = None           # 检测语言
    full_text: str = ""                      # 完整文本
    segments: List[TranscriptSegment] = None # 时间片段
    raw: Optional[Dict[str, Any]] = None    # 原始数据
    duration: Optional[float] = None         # 音频时长
    model_size: Optional[str] = None         # 使用的模型大小

    def __post_init__(self):
        if self.segments is None:
            self.segments = []


class BaseTranscriber(ABC):
    """转写器基类"""

    def __init__(self, model_size: str = "base", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._model = None

    @abstractmethod
    def load_model(self) -> None:
        """加载模型"""
        pass

    @abstractmethod
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """执行转写"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """转写器名称"""
        pass

    def is_ready(self) -> bool:
        """检查转写器是否就绪"""
        return self._model is not None

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "name": self.name,
            "model_size": self.model_size,
            "device": self.device,
            "ready": self.is_ready()
        }


class TranscriberError(Exception):
    """转写错误"""
    pass


class TranscriberTimeoutError(TranscriberError):
    """转写超时错误"""
    pass


class TranscriberModelNotFoundError(TranscriberError):
    """模型未找到错误"""
    pass