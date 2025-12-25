from __future__ import annotations

from typing import Any, Dict, Optional

from app.infrastructure.database.connection import SessionLocal
from app.repositories.provider_repository import ProviderRepository
from app.utils.logger import get_logger
from app.services.transcription_service import TranscriptSegment

logger = get_logger(__name__)


def _load_provider(provider_id: str) -> Optional[Dict[str, Any]]:
    try:
        with ProviderRepository() as provider_repo:
            provider = provider_repo.find_by_id(provider_id)
            if provider:
                return {
                    "id": provider.id,
                    "name": provider.name,
                    "type": provider.type,
                    "api_key": provider.api_key or "",
                    "base_url": provider.base_url or "",
                    "enabled": bool(provider.enabled),
                }
    except Exception as e:
        logger.warning(f"load provider failed: {e}")
    return None


def _build_openai_client(api_key: str, base_url: str | None):
    try:
        # OpenAI v1 client
        from openai import OpenAI  # type: ignore
        import httpx
    except Exception as e:
        logger.error(f"openai package not available: {e}")
        return None

    # 创建自定义httpx客户端，设置足够的超时时间用于AI分析
    timeout = httpx.Timeout(60.0, connect=10.0)  # 60秒总超时，10秒连接超时

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url, http_client=httpx.Client(timeout=timeout))
    return OpenAI(api_key=api_key, http_client=httpx.Client(timeout=timeout))


def generate_markdown_via_llm(
    provider_id: str,
    model_name: str,
    transcript_text: str,
    video_type: str = "science",
    note_style: str = "detailed",
    formats: list[str] | None = None,
    extras: str | None = None,
    segments: list[dict] | None = None,
    screenshot_density: str = "medium",  # 截图密度
) -> str:
    """
    Generate markdown summary using AI service.
    Integrates with the new AI service for better transcript processing.

    Args:
        provider_id: AI provider ID
        model_name: Model name to use
        transcript_text: Full transcript text (used as fallback if segments not provided)
        video_type: Video type (tech/dialogue/science/review)
        note_style: Note style (concise/detailed/teaching/xiaohongshu)
        formats: List of format options (e.g., ["screenshot", "link"])
        extras: Additional instructions
        segments: Real transcript segments with timestamps from Whisper
                  Format: [{"start": float, "end": float, "text": str}, ...]
    """
    from app.services.ai_service import AIService, AISource

    prov = _load_provider(provider_id)
    if not prov:
        raise Exception(f"Provider not found: {provider_id}")

    if not prov.get("api_key"):
        raise Exception(f"Provider {provider_id} has no API key configured")

    # Initialize AI service
    ai_service = AIService(
        api_key=prov["api_key"],
        base_url=prov.get("base_url") or "",
        model_name=model_name
    )

    # Use real segments if provided, otherwise fall back to text-based estimation
    if segments:
        logger.info(f"Using real Whisper segments: {len(segments)} segments")
        actual_segments = segments
    else:
        logger.warning("No real segments provided, falling back to text-based estimation")
        actual_segments = _create_segments_from_text(transcript_text)

    # Create AI source with new video_type and note_style
    source = AISource(
        title="视频转写内容",
        segments=actual_segments,
        tags=["AI生成", "视频笔记"],
        screenshot="screenshot" in (formats or []),
        link="link" in (formats or []),
        formats=formats or [],
        video_type=video_type,
        note_style=note_style,
        extras=extras,
        screenshot_density=screenshot_density  # 传递截图密度
    )

    # Generate summary
    logger.info(f"Starting AI summarization with model: {model_name}, video_type: {video_type}, note_style: {note_style}")
    result = ai_service.summarize(source)
    logger.info(f"AI summarization completed, result length: {len(result)}")

    return result


def _create_segments_from_text(text: str) -> list[TranscriptSegment]:
    """
    Create transcript segments from plain text.
    This is a simple implementation - in production, use actual timestamp data.
    """
    segments = []
    lines = text.split('\n')
    current_time = 0.0

    for line in lines:
        line = line.strip()
        if line:
            # Estimate 5 seconds per line of text
            segment = TranscriptSegment(
                start=current_time,
                end=current_time + 5.0,
                text=line
            )
            # Convert to dict to ensure proper Pydantic validation
            segments.append(segment.model_dump())
            current_time += 5.0

    return segments
