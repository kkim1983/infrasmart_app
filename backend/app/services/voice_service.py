"""
음성 입력 서비스 - OpenAI Whisper (Phase 2)

현장 점검 시 음성 메모 → 텍스트 변환 → 어노테이션 내용 입력
"""

import io
from typing import Optional, Dict, Any

from app.core.config import settings


class VoiceService:

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str = "ko",
        context_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        음성 파일 → 텍스트 변환 (Whisper)

        Args:
            audio_bytes: 음성 파일 (m4a, mp4, wav, mp3, webm)
            filename: 파일명 (확장자 포함, MIME 타입 추론용)
            language: 언어 코드 (ko=한국어)
            context_hint: 문맥 힌트 (예: "교량 안전점검 균열 측정")

        Returns:
            {
                "text": "변환된 텍스트",
                "language": "ko",
                "duration": 5.2,  # 초
                "confidence": "high",
            }
        """
        if not settings.OPENAI_API_KEY:
            return {
                "text": "",
                "error": "OPENAI_API_KEY가 설정되지 않았습니다.",
                "language": language,
            }

        try:
            client = self._get_client()

            # 파일명에서 확장자 추출
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "m4a"
            supported = {"m4a", "mp4", "wav", "mp3", "webm", "ogg", "flac"}
            if ext not in supported:
                ext = "m4a"

            # 시스템 프롬프트로 전문용어 힌트
            prompt = context_hint or (
                "교량 안전점검 현장 음성 메모입니다. "
                "균열, 박리, 철근노출, 누수, 세굴, 변형, 심각도, 등급, 교각, 거더, "
                "슬래브, 교대, 지간, 경간 등 토목/건설 전문용어를 정확히 인식하세요."
            )

            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"recording.{ext}"

            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format="verbose_json",
            )

            return {
                "text": response.text,
                "language": response.language or language,
                "duration": getattr(response, "duration", None),
                "confidence": "high" if response.text else "low",
            }

        except Exception as e:
            return {
                "text": "",
                "error": str(e),
                "language": language,
            }

    async def transcribe_and_enhance(
        self,
        audio_bytes: bytes,
        filename: str,
        damage_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        음성 변환 + 구조화 (GPT-4o로 후처리)

        음성: "거더 하부 3번 위치에 폭 0.5 균열 약 2미터 발견"
        결과: {
            "text": "거더 하부 3번 위치에 폭 0.5mm 균열 약 2m 발견",
            "structured": {
                "location": "G-3 하부",
                "damage_code": "C1",
                "dimensions": {"length_m": 2.0, "width_mm": 0.5},
                "severity_suggestion": "C"
            }
        }
        """
        # 1단계: Whisper 변환
        transcribe_result = await self.transcribe(audio_bytes, filename)
        if not transcribe_result.get("text"):
            return transcribe_result

        raw_text = transcribe_result["text"]

        # 2단계: GPT-4o로 구조화
        if not settings.OPENAI_API_KEY:
            return transcribe_result

        try:
            client = self._get_client()
            prompt = f"""다음은 교량 안전점검 현장 음성 메모입니다:
"{raw_text}"

이 텍스트에서 손상 정보를 구조화하여 JSON으로 반환하세요:
{{
  "text": "정제된 원본 텍스트 (단위 보정 포함)",
  "location": "위치 정보 (예: G3, AB-1, SL-2)",
  "damage_code": "손상코드 (C1/S1/E1/L1/D1/J1/W1 또는 null)",
  "dimensions": {{
    "length_m": 숫자 또는 null,
    "width_mm": 숫자 또는 null,
    "area_m2": 숫자 또는 null
  }},
  "severity_suggestion": "A/B/C/D/E 또는 null",
  "notes": "추가 메모"
}}
손상 정보가 없으면 null로 채우세요."""

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            import json
            structured = json.loads(response.choices[0].message.content)
            return {
                **transcribe_result,
                "structured": structured,
            }

        except Exception as e:
            return {
                **transcribe_result,
                "structured": None,
                "structure_error": str(e),
            }


voice_service = VoiceService()
