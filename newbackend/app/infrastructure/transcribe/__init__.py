"""
转写服务模块
"""

from .base_transcriber import BaseTranscriber, TranscriptResult, TranscriptSegment, TranscriberError
from .whisper_transcriber import WhisperTranscriber
from .transcriber_manager import get_transcriber, get_available_transcribers, get_current_transcriber_info

__all__ = [
    "BaseTranscriber",
    "TranscriptResult",
    "TranscriptSegment",
    "TranscriberError",
    "WhisperTranscriber",
    "get_transcriber",
    "get_available_transcribers",
    "get_current_transcriber_info"
]