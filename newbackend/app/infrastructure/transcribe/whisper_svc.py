from __future__ import annotations

import os
from typing import Any, Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


class WhisperService:
    """
    Thin wrapper for faster-whisper (if available). Falls back to a stub
    when the package or model is not present. This keeps the service runnable
    without heavy downloads, while allowing drop-in acceleration later.
    """

    def __init__(self, model_size: str | None = None, device: str | None = None):
        self.model_size = model_size or os.getenv("WHISPER_MODEL", "base")
        self.device = device or os.getenv("WHISPER_DEVICE", None)
        self._impl = None
        try:
            from faster_whisper import WhisperModel  # type: ignore

            kwargs = {}
            if self.device:
                kwargs["device"] = self.device
            compute_type = os.getenv("WHISPER_COMPUTE_TYPE")
            if compute_type:
                kwargs["compute_type"] = compute_type  # e.g., "float16", "int8_float16"
            self._impl = WhisperModel(self.model_size, **kwargs)
            logger.info(f"WhisperService using faster-whisper model={self.model_size}")
        except Exception as e:
            logger.warning(f"faster-whisper not available or failed to init: {e}")
            self._impl = None

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Returns:
          dict with keys: language, full_text, segments[{start, end, text}]
        """
        if not self._impl:
            # Fallback stub keeps pipeline functional
            return {
                "language": "zh",
                "full_text": "示例转写文本（stub）",
                "segments": [{"start": 1.0, "end": 3.0, "text": "关键点A"}],
            }
        try:
            beam = int(os.getenv("WHISPER_BEAM_SIZE", "1"))
            segments, info = self._impl.transcribe(
                audio_path,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                beam_size=beam,
            )
            seg_list: List[Dict[str, Any]] = []
            full_text_parts: List[str] = []
            for s in segments:
                seg_list.append({"start": float(s.start), "end": float(s.end), "text": s.text})
                full_text_parts.append(s.text)
            return {
                "language": getattr(info, "language", "unknown"),
                "full_text": "".join(full_text_parts).strip(),
                "segments": seg_list,
            }
        except Exception as e:
            logger.error(f"whisper transcribe failed: {e}")
            return {
                "language": "unknown",
                "full_text": "",
                "segments": [],
            }
