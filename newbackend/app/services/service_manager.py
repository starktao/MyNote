"""
Global Service Manager - Singleton services for better performance
"""

from typing import Dict, Optional
import threading
import atexit
from app.services.transcription_service import TranscriptionService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceManager:
    """Singleton service manager for global service instances"""

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
        if self._initialized:
            return

        self._transcription_services: Dict[str, TranscriptionService] = {}
        self._lock = threading.Lock()
        self._initialized = True

        # Register cleanup function
        atexit.register(self._cleanup)

        logger.info("[SERVICE_MANAGER] Service manager initialized")

    def get_transcription_service(self, model_size: str = "base") -> TranscriptionService:
        """Get or create a transcription service instance"""
        with self._lock:
            if model_size not in self._transcription_services:
                logger.info(f"[SERVICE_MANAGER] Creating new transcription service for model: {model_size}")
                self._transcription_services[model_size] = TranscriptionService(model_size=model_size)
                logger.info(f"[SERVICE_MANAGER] Transcription service created for model: {model_size}")
            else:
                logger.info(f"[SERVICE_MANAGER] Reusing existing transcription service for model: {model_size}")

            return self._transcription_services[model_size]

    def preload_models(self, model_sizes: list = None):
        """Preload Whisper models at startup"""
        if model_sizes is None:
            model_sizes = ["base"]  # Default model

        logger.info(f"[SERVICE_MANAGER] Starting to preload models: {model_sizes}")

        for model_size in model_sizes:
            try:
                logger.info(f"[SERVICE_MANAGER] Preloading model: {model_size}")
                service = self.get_transcription_service(model_size)
                if service.whisper_service.model is not None:
                    logger.info(f"[SERVICE_MANAGER] Successfully preloaded model: {model_size}")
                else:
                    logger.error(f"[SERVICE_MANAGER] Failed to preload model: {model_size}")
            except Exception as e:
                logger.error(f"[SERVICE_MANAGER] Error preloading model {model_size}: {e}")

        logger.info("[SERVICE_MANAGER] Model preloading completed")

    def _cleanup(self):
        """Cleanup resources"""
        logger.info("[SERVICE_MANAGER] Cleaning up resources")
        self._transcription_services.clear()


# Global instance
_service_manager = None

def get_service_manager() -> ServiceManager:
    """Get the global service manager instance"""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager

def get_transcription_service(model_size: str = "base") -> TranscriptionService:
    """Get a transcription service instance"""
    return get_service_manager().get_transcription_service(model_size)