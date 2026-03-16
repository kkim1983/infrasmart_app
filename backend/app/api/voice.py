"""음성 입력 API (Phase 2)"""

from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Optional

from app.api.deps import get_current_inspector
from app.models.inspector import Inspector
from app.services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["음성입력"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("ko"),
    context_hint: Optional[str] = Form(None),
    inspector: Inspector = Depends(get_current_inspector),
):
    """
    음성 파일 → 텍스트 변환 (Whisper)

    지원 형식: m4a, mp4, wav, mp3, webm
    최대 파일 크기: 25MB (Whisper API 제한)
    """
    content = await file.read()
    return await voice_service.transcribe(
        audio_bytes=content,
        filename=file.filename or "recording.m4a",
        language=language,
        context_hint=context_hint,
    )


@router.post("/transcribe-structured")
async def transcribe_and_structure(
    file: UploadFile = File(...),
    language: str = Form("ko"),
    inspector: Inspector = Depends(get_current_inspector),
):
    """
    음성 변환 + GPT-4o 구조화

    음성: "거더 3번 하부 폭 0.3 균열 1.5미터"
    → {text, location, damage_code, dimensions, severity_suggestion}
    """
    content = await file.read()
    return await voice_service.transcribe_and_enhance(
        audio_bytes=content,
        filename=file.filename or "recording.m4a",
    )
