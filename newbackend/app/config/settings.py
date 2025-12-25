import os
from pydantic_settings import BaseSettings
from typing import List

try:
    import psutil
except ImportError:
    psutil = None


def _calculate_ocr_workers() -> int:
    """根据CPU核心数智能计算基础OCR线程数"""
    try:
        # 优先使用物理核心数
        if psutil:
            physical = psutil.cpu_count(logical=False)
            logical = os.cpu_count() or 4

            if physical:
                # 分档策略
                if physical <= 4:
                    return 4
                elif physical <= 8:
                    return min(8, max(6, physical // 2))
                else:  # >8核
                    return min(10, max(8, physical // 2))
            else:
                # psutil不可用时降级到逻辑核心
                return max(2, min(logical // 2 or 2, 8))
        else:
            # psutil不可用时的安全降级
            logical = os.cpu_count() or 4
            return max(2, min(logical // 2 or 2, 8))
    except Exception:
        # 出错时的保守配置
        return 4


def _default_ocr_workers() -> int:
    """获取最终的OCR线程数，考虑环境变量调整"""
    # 获取基础线程数
    base_workers = _calculate_ocr_workers()

    try:
        # 检查是否有直接覆盖值
        override = os.getenv("OCR_MAX_WORKERS_OVERRIDE")
        if override and override.strip():
            override_workers = int(override.strip())
            print(f"[配置] OCR线程数被环境变量直接覆盖为: {override_workers}")
            return max(2, min(override_workers, 16))  # 限制在2-16之间

        # 检查是否有倍数调整
        multiplier_str = os.getenv("OCR_MAX_WORKERS_MULTIPLIER")
        if multiplier_str and multiplier_str.strip():
            multiplier = float(multiplier_str.strip())
            if multiplier != 1.0:
                adjusted_workers = int(base_workers * multiplier)
                final_workers = max(2, min(adjusted_workers, 16))  # 限制在2-16之间
                print(f"[配置] OCR线程数倍数调整: {base_workers} × {multiplier} = {final_workers}")
                return final_workers

        # 使用默认计算值
        print(f"[配置] OCR线程数自动计算: {base_workers}")
        return base_workers

    except Exception as e:
        print(f"[配置] OCR线程数计算出错，使用默认值: {base_workers}, 错误: {e}")
        return base_workers


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./mynote.db"

    # File Paths
    NOTE_OUTPUT_DIR: str = "note_results"
    DATA_DIR: str = "data"
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    STATIC_DIR: str = "static"
    SCREENSHOT_OUTPUT_DIR: str = "static/screenshots"
    TEMP_SCREENSHOT_DIR: str = "temp_screenshots"

    # Concurrency Settings
    MAX_CONCURRENCY: int = 3

    # Screenshot Settings
    SCREENSHOT_MODE: str = "smart"
    SCREENSHOT_WINDOW: float = 4.0  # 候选截图时间窗口：4秒范围，5张候选，间隔1秒
    SCREENSHOT_CANDIDATES: int = 5
    SCREENSHOT_ENABLED: bool = True
    SCREENSHOT_QUALITY: int = 2  # 1-5, 1=highest, 5=lowest
    SCREENSHOT_RESOLUTION: str = "1280x720"
    SCREENSHOT_FORMAT: str = "jpg"
    SCREENSHOT_MAX_CONCURRENT: int = 3
    SCREENSHOT_CLEANUP_TEMP: bool = True

    # FFmpeg Configuration
    FFMPEG_PATH: str = "ffmpeg"  # Assumes FFmpeg is in PATH
    FFPROBE_PATH: str = "ffprobe"  # Assumes FFprobe is in PATH
    FFMPEG_TIMEOUT: int = 60

    # AI Analysis Settings
    AI_ANALYSIS_ENABLED: bool = True
    AI_FALLBACK_ENABLED: bool = True
    AI_ANALYSIS_TIMEOUT: int = 120

    # Server Configuration
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    STATIC_URL_PREFIX: str = "/static"

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "http://tauri.localhost",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176"
    ]

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # API Configuration
    API_RATE_LIMIT: int = 100
    API_TIMEOUT: int = 30

    # Task Configuration
    TASK_RESULT_RETENTION_DAYS: int = 7
    SCREENSHOT_RETENTION_DAYS: int = 30

    # 智能截图选择配置
    INTELLIGENT_SCREENSHOT_ENABLED: bool = True
    CAPABILITY_CACHE_TTL: int = 3600
    MULTIMODAL_TIMEOUT: int = 60
    # OCR配置 - 根据CPU核心数智能计算
    OCR_MAX_WORKERS: int = _default_ocr_workers()

    # OCR调整参数（可选的环境变量覆盖）
    OCR_MAX_WORKERS_MULTIPLIER: float = 1.0
    OCR_PROCESSING_TIMEOUT: int = 30
    IMAGE_MAX_SIZE: int = 1920
    IMAGE_COMPRESSION_QUALITY: int = 85

    # OCR降级配置
    OCR_FALLBACK_ENABLED: bool = True

    # 截图去重配置
    SCREENSHOT_DEDUP_ENABLED: bool = True  # 启用截图去重
    SCREENSHOT_DEDUP_HASH_THRESHOLD: int = 5  # 哈希距离阈值，小于等于该值视为重复

    # 多节点并发配置
    MAX_CONCURRENT_NODES: int = 4
    MAX_CONCURRENT_IMAGES: int = 3
    MAX_CONCURRENT_OPERATIONS: int = 6

    # 详细日志配置
    LOG_STRATEGY_CALLS: bool = True
    LOG_PERFORMANCE_METRICS: bool = True
    LOG_ERROR_DETAILS: bool = True
    LOG_RESOURCE_USAGE: bool = False
    LOG_THREAD_POOL_STATUS: bool = True

    # P2.1新增：Whisper性能优化配置
    WHISPER_MODEL_SIZE: str = "base"  # tiny/base/small/medium/large
    WHISPER_DEVICE: str = "auto"  # auto/cpu/cuda
    WHISPER_COMPUTE_TYPE: str = "auto"  # auto/int8/float16/float32
    WHISPER_ENABLE_VAD: bool = True  # 启用语音活动检测
    WHISPER_BEAM_SIZE: int = 5  # 束搜索大小
    WHISPER_NO_SPEECH_THRESHOLD: float = 0.7  # 无语音阈值
    WHISPER_COMPRESSION_RATIO_THRESHOLD: float = 2.3  # 压缩比阈值
    WHISPER_CONDITION_ON_PREVIOUS_TEXT: bool = False  # 避免错误累积
    WHISPER_MIN_SILENCE_DURATION_MS: int = 900  # VAD最小静音时长
    WHISPER_SPEECH_PAD_MS: int = 300  # VAD语音填充

    # P2.1新增：转写进度反馈配置
    TRANSCRIBE_PROGRESS_ENABLED: bool = True  # 启用转写进度反馈
    TRANSCRIBE_PROGRESS_INTERVAL: int = 50  # 进度更新间隔（处理的片段数）
    TRANSCRIBE_PROGRESS_TIMEOUT: int = 1200  # 转写超时时间（秒）
    TRANSCRIBE_KEEPALIVE_INTERVAL: int = 25  # SSE保活间隔（秒）

    @property
    def screenshot_full_output_dir(self) -> str:
        """获取完整的截图输出目录路径"""
        return os.path.join(self.BASE_DIR, self.SCREENSHOT_OUTPUT_DIR)

    @property
    def screenshot_full_temp_dir(self) -> str:
        """获取完整的临时截图目录路径"""
        return os.path.join(self.BASE_DIR, self.TEMP_SCREENSHOT_DIR)

    @property
    def static_full_dir(self) -> str:
        """获取完整的静态文件目录路径"""
        return os.path.join(self.BASE_DIR, self.STATIC_DIR)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
