"""
Transcription Service - Real Whisper Audio Transcription (Based on Original Backend)
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# Try to import dependencies
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
    print("[WHISPER] faster-whisper is available")
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    print("[WHISPER] faster-whisper not available, install with: pip install faster-whisper")

try:
    from modelscope import snapshot_download
    MODELSCOPE_AVAILABLE = True
    print("[WHISPER] ModelScope is available")
except ImportError:
    MODELSCOPE_AVAILABLE = False
    print("[WHISPER] ModelScope not available, install with: pip install modelscope")


class TranscriptSegment(BaseModel):
    """Transcript segment model"""
    start: float
    end: float
    text: str


class WhisperTranscriptionService:
    """Real Whisper transcription service based on original backend implementation"""

    # Use standard OpenAI Whisper models - good for both Chinese and English
    MODEL_MAP = {
        "tiny": "tiny",
        "base": "base",
        "small": "small",
        "medium": "medium",
        "large": "large",
        "large-v2": "large-v2",
        "large-v3": "large-v3",
        "large-v3-turbo": "large-v3-turbo",
    }

    def __init__(self, model_size: str = "base"):
        """Initialize Whisper transcription service"""
        self.model_size = model_size
        self.model = None
        self.device = "cpu"
        self.compute_type = "default"

        # Try to detect CUDA availability (from original backend)
        if self._is_cuda_available():
            self.device = "cuda"
            self.compute_type = "float16"
            print("[WHISPER] CUDA 可用，使用 GPU")
        else:
            print("[WHISPER] CUDA not available, using CPU")

        self._initialize_model()

    def _is_cuda_available(self) -> bool:
        """Check if CUDA is available (from original backend)"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _get_model_dir(self) -> str:
        """Get model directory (based on original backend path_helper)"""
        if getattr(sys, 'frozen', False):
            # Packaged app
            base_dir = os.path.join(os.getenv("APPDATA") or str(Path.home()), "MyNote", "models")
        else:
            # Development mode
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))

        path = os.path.join(base_dir, "whisper")
        os.makedirs(path, exist_ok=True)
        return path

    def _initialize_model(self):
        """Initialize Whisper model (simplified approach)"""
        try:
            if not FASTER_WHISPER_AVAILABLE:
                raise Exception("faster-whisper package not available. Install with: pip install faster-whisper")

            # Get model size from map, default to 'base'
            model_size = self.MODEL_MAP.get(self.model_size, "base")
            print(f"[WHISPER] Loading model: {model_size} on {self.device}")

            # Load model using standard Whisper approach
            self.model = WhisperModel(
                model_size_or_path=model_size,
                device=self.device,
                compute_type=self.compute_type
            )

            print("[WHISPER] Model loaded successfully")

        except Exception as e:
            print(f"[ERROR] Failed to initialize Whisper model: {e}")
            self.model = None

    def transcribe(self, audio_path: str, model_size: str = None) -> Dict[str, Any]:
        """Transcribe audio file using Whisper (based on original backend)"""
        if not FASTER_WHISPER_AVAILABLE:
            raise Exception("faster-whisper package not available. Please install it with: pip install faster-whisper")

        if self.model is None:
            raise Exception("Whisper model not initialized. Check model configuration and availability.")

        try:
            if not os.path.exists(audio_path):
                raise Exception(f"Audio file not found: {audio_path}")

            print(f"[WHISPER] Starting transcription: {audio_path}")
            print(f"[WHISPER] Using model: {model_size or self.model_size}")
            start_time = time.time()

            # Transcribe using Whisper (same as original backend)
            segments_raw, info = self.model.transcribe(audio_path)

            # Process results (same as original backend)
            segments = []
            full_text = ""

            for seg in segments_raw:
                text = seg.text.strip()
                if text:  # Only add non-empty segments
                    full_text += text + " "
                    segments.append(TranscriptSegment(
                        start=seg.start,
                        end=seg.end,
                        text=text
                    ))

            processing_time = time.time() - start_time

            result = {
                "language": info.language,
                "full_text": full_text.strip(),
                "segments": [seg.dict() for seg in segments],
                "duration": sum(seg.end - seg.start for seg in segments),
                "model_used": self.model_size,
                "word_count": len(full_text.split()),
                "processing_time": processing_time
            }

            print(f"[WHISPER] Transcription completed in {processing_time:.2f}s")
            print(f"[WHISPER] Language: {result['language']}")
            print(f"[WHISPER] Words: {result['word_count']}")
            print(f"[WHISPER] Duration: {result['duration']:.2f}s")
            print(f"[WHISPER] Full transcript text: {result['full_text'][:200]}...")

            return result

        except Exception as e:
            print(f"[ERROR] Whisper transcription failed: {str(e)}")
            raise Exception(f"Whisper transcription failed: {str(e)}")

    def get_supported_formats(self) -> List[str]:
        """Get supported audio formats"""
        return [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"]

    def validate_audio_file(self, audio_path: str) -> bool:
        """Validate if audio file is supported"""
        if not os.path.exists(audio_path):
            return False

        file_ext = Path(audio_path).suffix.lower()
        return file_ext in self.get_supported_formats()


# Simplified TranscriptionService wrapper
class TranscriptionService:
    """Wrapper service for transcription"""

    def __init__(self, model_size: str = "base"):
        """Initialize transcription service"""
        self.whisper_service = WhisperTranscriptionService(model_size=model_size)

    def transcribe(self, audio_path: str, model_size: str = None) -> Dict[str, Any]:
        """Transcribe audio file"""
        return self.whisper_service.transcribe(audio_path, model_size)

    def get_supported_formats(self) -> List[str]:
        """Get supported audio formats"""
        return self.whisper_service.get_supported_formats()

    def validate_audio_file(self, audio_path: str) -> bool:
        """Validate if audio file is supported"""
        return self.whisper_service.validate_audio_file(audio_path)