"""
Transcribe Controller - Audio Transcription
"""

from fastapi import APIRouter
from app.utils.response import R

router = APIRouter(tags=["Transcription"])


@router.get("/transcribe")
async def get_transcription():
    """Get transcription status (placeholder)"""
    return R.success({"message": "Transcription endpoint - coming soon"})