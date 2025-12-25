"""
Whisper转写器实现
参考BiliNote项目的Whisper实现，添加了更好的错误处理和进度反馈
P1.1新增：支持SSE进度反馈
"""
import os
import time
import threading
import asyncio
from typing import Optional, Callable, Dict, Any
from .base_transcriber import BaseTranscriber, TranscriptResult, TranscriptSegment, TranscriberError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WhisperTranscriber(BaseTranscriber):
    """Whisper转写器实现 - P1.1新增SSE进度反馈支持"""

    def __init__(self, model_size: str = "base", device: str = "auto"):
        super().__init__(model_size, device)
        self._impl = None  # 实际的Whisper实现
        self._is_loading = False
        self._load_error = None
        self.progress_callback: Optional[Callable] = None  # P1.1新增：进度回调函数

    @property
    def name(self) -> str:
        return "Whisper"

    def load_model(self) -> None:
        """加载Whisper模型"""
        if self._is_loading:
            return

        if self._model is not None:
            return

        self._is_loading = True
        self._load_error = None

        def load_in_thread():
            try:
                logger.info(f"[WHISPER] 开始加载模型: {self.model_size}")

                # 尝试导入faster-whisper
                try:
                    from faster_whisper import WhisperModel
                    logger.info("[WHISPER] 使用faster-whisper")

                    # 设备选择逻辑
                    if self.device == "auto":
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    else:
                        device = self.device

                    logger.info(f"[WHISPER] 使用设备: {device}")

                    # 加载模型 - P0.1优化：使用int8量化提升CPU性能
                    compute_type = "int8" if device == "cpu" else "float16"
                    logger.info(f"[WHISPER] 使用计算类型: {compute_type}")

                    model = WhisperModel(
                        self.model_size,
                        device=device,
                        compute_type=compute_type
                    )
                    self._impl = model

                except ImportError:
                    logger.warning("[WHISPER] faster-whisper未安装，使用openai-whisper")
                    import whisper
                    self._impl = whisper.load_model(self.model_size)

                self._model = True
                logger.info(f"[WHISPER] 模型加载完成: {self.model_size}")

            except Exception as e:
                self._load_error = e
                logger.error(f"[WHISPER] 模型加载失败: {e}")
            finally:
                self._is_loading = False

        # 在后台线程中加载模型
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def transcribe(self, audio_path: str) -> TranscriptResult:
        """执行转写"""
        if not os.path.exists(audio_path):
            raise TranscriberError(f"音频文件不存在: {audio_path}")

        # 确保模型已加载
        if self._model is None:
            if self._is_loading:
                # 等待模型加载完成
                logger.info("[WHISPER] 等待模型加载...")
                while self._is_loading:
                    time.sleep(0.5)

                if self._load_error:
                    raise TranscriberError(f"模型加载失败: {self._load_error}")
            else:
                self.load_model()
                if self._load_error:
                    raise TranscriberError(f"模型加载失败: {self._load_error}")

        logger.info(f"[WHISPER] 开始转写: {audio_path}")
        start_time = time.time()

        try:
            if hasattr(self._impl, 'transcribe'):
                # faster-whisper接口 - P0.2优化：增强转写参数
                segments, info = self._impl.transcribe(
                    audio_path,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters={
                        "min_silence_duration_ms": 900,
                        "speech_pad_ms": 300
                    },
                    no_speech_threshold=0.7,
                    compression_ratio_threshold=2.3,
                    condition_on_previous_text=False,  # 避免错误累积
                    language=None  # 自动检测语言
                )

                # 转换结果格式
                transcript_segments = []
                full_text_parts = []

                for segment in segments:
                    transcript_segments.append(TranscriptSegment(
                        start=segment.start,
                        end=segment.end,
                        text=segment.text.strip()
                    ))
                    full_text_parts.append(segment.text.strip())

                full_text = " ".join(full_text_parts)
                language = info.language if hasattr(info, 'language') else None

            else:
                # openai-whisper接口
                result = self._impl.transcribe(
                    audio_path,
                    language=None,  # 自动检测语言
                    fp16=False
                )

                # 转换结果格式
                transcript_segments = []
                for segment in result.get('segments', []):
                    transcript_segments.append(TranscriptSegment(
                        start=segment['start'],
                        end=segment['end'],
                        text=segment['text'].strip()
                    ))

                full_text = result.get('text', '').strip()
                language = result.get('language')

            elapsed = time.time() - start_time
            logger.info(f"[WHISPER] 转写完成，用时: {elapsed:.2f}秒")
            logger.info(f"[WHISPER] 检测语言: {language}")
            logger.info(f"[WHISPER] 文本长度: {len(full_text)} 字符")
            logger.info(f"[WHISPER] 时间片段数: {len(transcript_segments)}")

            return TranscriptResult(
                language=language,
                full_text=full_text,
                segments=transcript_segments,
                duration=None,  # 可以从音频文件获取
                model_size=self.model_size,
                raw=None
            )

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[WHISPER] 转写失败，用时: {elapsed:.2f}秒，错误: {e}")
            raise TranscriberError(f"转写失败: {e}")

    def is_ready(self) -> bool:
        """检查转写器是否就绪"""
        return self._model is not None and self._load_error is None

    def get_status(self) -> dict:
        """获取转写器状态"""
        return {
            "name": self.name,
            "model_size": self.model_size,
            "device": self.device,
            "is_loading": self._is_loading,
            "is_ready": self.is_ready(),
            "load_error": str(self._load_error) if self._load_error else None
        }

    # P1.1新增：SSE进度反馈支持方法
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback
        logger.info("[WHISPER] 进度回调函数已设置")

    async def _emit_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """发送进度事件"""
        if self.progress_callback:
            try:
                await self.progress_callback(task_id, progress_data)
            except Exception as e:
                logger.error(f"[WHISPER] 发送进度事件失败: {e}")

    async def transcribe_with_progress(self, audio_path: str, task_id: str = None) -> TranscriptResult:
        """支持进度反馈的转写方法 - P1.1新增"""
        if not os.path.exists(audio_path):
            raise TranscriberError(f"音频文件不存在: {audio_path}")

        # 发送开始事件
        if task_id:
            await self._emit_progress(task_id, {
                "status": "started",
                "progress": 0,
                "message": "开始转写",
                "timestamp": time.time()
            })

        # 确保模型已加载
        if self._model is None:
            if self._is_loading:
                # 发送加载中事件
                if task_id:
                    await self._emit_progress(task_id, {
                        "status": "loading_model",
                        "progress": 5,
                        "message": "正在加载模型",
                        "timestamp": time.time()
                    })

                # 等待模型加载完成
                logger.info("[WHISPER] 等待模型加载...")
                while self._is_loading:
                    await asyncio.sleep(0.5)

                if self._load_error:
                    if task_id:
                        await self._emit_progress(task_id, {
                            "status": "error",
                            "progress": 0,
                            "message": f"模型加载失败: {self._load_error}",
                            "timestamp": time.time()
                        })
                    raise TranscriberError(f"模型加载失败: {self._load_error}")
            else:
                self.load_model()
                if self._load_error:
                    if task_id:
                        await self._emit_progress(task_id, {
                            "status": "error",
                            "progress": 0,
                            "message": f"模型加载失败: {self._load_error}",
                            "timestamp": time.time()
                        })
                    raise TranscriberError(f"模型加载失败: {self._load_error}")

        # 发送模型加载完成事件
        if task_id:
            await self._emit_progress(task_id, {
                "status": "model_loaded",
                "progress": 10,
                "message": "模型加载完成，开始转写",
                "timestamp": time.time()
            })

        logger.info(f"[WHISPER] 开始转写: {audio_path}")
        start_time = time.time()

        try:
            if hasattr(self._impl, 'transcribe'):
                # faster-whisper接口 - 使用优化参数
                if task_id:
                    await self._emit_progress(task_id, {
                        "status": "transcribing",
                        "progress": 20,
                        "message": "正在处理音频",
                        "timestamp": time.time()
                    })

                segments, info = self._impl.transcribe(
                    audio_path,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters={
                        "min_silence_duration_ms": 900,
                        "speech_pad_ms": 300
                    },
                    no_speech_threshold=0.7,
                    compression_ratio_threshold=2.3,
                    condition_on_previous_text=False,
                    language=None  # 自动检测语言
                )

                # 转换结果格式
                transcript_segments = []
                full_text_parts = []
                segment_count = 0
                total_segments = 0  # 我们无法预先知道段数，使用进度估算

                for segment in segments:
                    transcript_segments.append(TranscriptSegment(
                        start=segment.start,
                        end=segment.end,
                        text=segment.text.strip()
                    ))
                    full_text_parts.append(segment.text.strip())
                    segment_count += 1

                    # 每处理50个片段发送一次进度（20%->90%）
                    if task_id and segment_count % 50 == 0:
                        progress = min(20 + (segment_count // 50) * 10, 90)
                        await self._emit_progress(task_id, {
                            "status": "transcribing",
                            "progress": progress,
                            "message": f"已处理 {segment_count} 个片段",
                            "segments_processed": segment_count,
                            "timestamp": time.time()
                        })

                full_text = " ".join(full_text_parts)
                language = info.language if hasattr(info, 'language') else None

            else:
                # openai-whisper接口
                if task_id:
                    await self._emit_progress(task_id, {
                        "status": "transcribing",
                        "progress": 30,
                        "message": "使用openai-whisper处理",
                        "timestamp": time.time()
                    })

                result = self._impl.transcribe(
                    audio_path,
                    language=None,  # 自动检测语言
                    fp16=False
                )

                # 转换结果格式
                transcript_segments = []
                for segment in result.get('segments', []):
                    transcript_segments.append(TranscriptSegment(
                        start=segment['start'],
                        end=segment['end'],
                        text=segment['text'].strip()
                    ))

                full_text = result.get('text', '').strip()
                language = result.get('language')

            elapsed = time.time() - start_time
            logger.info(f"[WHISPER] 转写完成，用时: {elapsed:.2f}秒")
            logger.info(f"[WHISPER] 检测语言: {language}")
            logger.info(f"[WHISPER] 文本长度: {len(full_text)} 字符")
            logger.info(f"[WHISPER] 时间片段数: {len(transcript_segments)}")

            # 发送完成事件
            if task_id:
                await self._emit_progress(task_id, {
                    "status": "completed",
                    "progress": 100,
                    "message": "转写完成",
                    "result": {
                        "text": full_text,
                        "language": language,
                        "segments": len(transcript_segments),
                        "duration": elapsed
                    },
                    "timestamp": time.time()
                })

            return TranscriptResult(
                language=language,
                full_text=full_text,
                segments=transcript_segments,
                duration=None,  # 可以从音频文件获取
                model_size=self.model_size,
                raw=None
            )

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[WHISPER] 转写失败，用时: {elapsed:.2f}秒，错误: {e}")

            # 发送错误事件
            if task_id:
                await self._emit_progress(task_id, {
                    "status": "error",
                    "progress": 0,
                    "message": f"转写失败: {str(e)}",
                    "timestamp": time.time()
                })

            raise TranscriberError(f"转写失败: {e}")