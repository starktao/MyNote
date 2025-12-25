"""
转写器管理器
参考BiliNote项目设计，支持多种转写器
"""
import os
import threading
from typing import Dict, Optional, Type
from .base_transcriber import BaseTranscriber, TranscriberError
from .whisper_transcriber import WhisperTranscriber
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TranscriberManager:
    """转写器管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not getattr(self, '_initialized', False):
            self._transcribers: Dict[str, BaseTranscriber] = {}
            self._current_transcriber_type = os.getenv("TRANSCRIBER_TYPE", "whisper")
            self._default_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
            self._default_device = os.getenv("WHISPER_DEVICE", "auto")
            self._initialized = True
            logger.info("[TRANSCRIBER] 转写器管理器初始化完成")

    def register_transcriber(self, transcriber_type: str, transcriber_class: Type[BaseTranscriber]):
        """注册转写器"""
        self._transcribers[transcriber_type] = transcriber_class
        logger.info(f"[TRANSCRIBER] 注册转写器: {transcriber_type}")

    def get_transcriber(
        self,
        transcriber_type: Optional[str] = None,
        model_size: Optional[str] = None,
        device: Optional[str] = None
    ) -> BaseTranscriber:
        """获取转写器实例"""
        transcriber_type = transcriber_type or self._current_transcriber_type
        model_size = model_size or self._default_model_size
        device = device or self._default_device

        logger.info(f"[TRANSCRIBER] 获取转写器: {transcriber_type}, 模型: {model_size}, 设备: {device}")

        # 生成缓存键
        cache_key = f"{transcriber_type}:{model_size}:{device}"

        if cache_key not in self._transcribers:
            # 创建新的转写器实例
            if transcriber_type == "whisper":
                transcriber = WhisperTranscriber(model_size=model_size, device=device)
                self._transcribers[cache_key] = transcriber
                # 预加载模型
                transcriber.load_model()
            else:
                raise TranscriberError(f"不支持的转写器类型: {transcriber_type}")

        return self._transcribers[cache_key]

    def get_available_transcribers(self) -> Dict[str, Dict]:
        """获取可用的转写器列表"""
        return {
            "whisper": {
                "name": "Whisper",
                "description": "OpenAI Whisper语音识别",
                "models": ["tiny", "base", "small", "medium", "large"],
                "default_model": self._default_model_size,
                "supports_gpu": True
            }
        }

    def get_current_transcriber_info(self) -> Dict:
        """获取当前转写器信息"""
        transcriber = self.get_transcriber()
        return {
            "type": self._current_transcriber_type,
            "model_size": transcriber.model_size,
            "device": transcriber.device,
            "status": transcriber.get_status() if hasattr(transcriber, 'get_status') else None
        }

    def cleanup(self):
        """清理资源"""
        for transcriber in self._transcribers.values():
            try:
                if hasattr(transcriber, '_model') and transcriber._model:
                    del transcriber._model
                    transcriber._model = None
            except Exception as e:
                logger.warning(f"[TRANSCRIBER] 清理转写器资源失败: {e}")

        self._transcribers.clear()
        logger.info("[TRANSCRIBER] 资源清理完成")


# 全局转写器管理器实例
transcriber_manager = TranscriberManager()


def get_transcriber(
    transcriber_type: Optional[str] = None,
    model_size: Optional[str] = None,
    device: Optional[str] = None
) -> BaseTranscriber:
    """获取转写器实例的便捷函数"""
    return transcriber_manager.get_transcriber(transcriber_type, model_size, device)


def get_available_transcribers() -> Dict[str, Dict]:
    """获取可用转写器列表的便捷函数"""
    return transcriber_manager.get_available_transcribers()


def get_current_transcriber_info() -> Dict:
    """获取当前转写器信息的便捷函数"""
    return transcriber_manager.get_current_transcriber_info()