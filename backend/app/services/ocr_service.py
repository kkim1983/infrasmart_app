"""
OCR 서비스 - 손상현황표 자동 추출 (Phase 2)

방법: OpenAI GPT-4 Vision API (gpt-4o)로 도면 이미지에서 표 추출
     → 구조화된 JSON 반환 → 손상 기록 자동 생성

PaddleOCR 대안: openai 패키지는 이미 requirements.txt에 포함됨
"""

import base64
import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.config import settings


class OcrService:

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def extract_damage_table(
        self,
        image_bytes: bytes,
        image_mime: str = "image/jpeg",
        facility_type: str = "BR",
        plugin_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        도면/현장 사진에서 손상현황표 추출

        Returns:
            {
                "success": bool,
                "damages": [
                    {
                        "damage_code": "C1",
                        "damage_name": "균열",
                        "location": "G3-1",
                        "length": 2.5,      # m
                        "width": 1.2,       # mm
                        "area": None,
                        "severity_grade": "C",
                        "is_new": True,
                        "notes": "...
                    },
                    ...
                ],
                "raw_text": "...",
                "confidence": 0.85,
            }
        """
        if not settings.OPENAI_API_KEY:
            return {
                "success": False,
                "error": "OPENAI_API_KEY가 설정되지 않았습니다.",
                "damages": [],
            }

        # 손상 코드 목록 (플러그인에서 가져오거나 기본값 사용)
        damage_codes_hint = ""
        if plugin_config and "damageCodes" in plugin_config:
            codes = plugin_config["damageCodes"]
            code_list = ", ".join([f"{c['code']}({c['name']})" for c in codes])
            damage_codes_hint = f"\n손상코드 목록: {code_list}"

        prompt = f"""이 이미지는 교량/시설물 안전점검 현장의 손상현황표 또는 점검 도면입니다.
이미지에서 손상 기록 정보를 추출하여 JSON 형식으로 반환해주세요.{damage_codes_hint}

다음 형식의 JSON 배열을 반환하세요 (마크다운 없이 순수 JSON만):
{{
  "damages": [
    {{
      "damage_code": "손상코드 (C1/S1/E1/L1 등)",
      "damage_name": "손상명칭",
      "location": "위치 (예: G3, AB-1)",
      "length_m": 숫자 또는 null,
      "width_mm": 숫자 또는 null,
      "area_m2": 숫자 또는 null,
      "severity_grade": "A/B/C/D/E 중 하나 또는 null",
      "is_new": true 또는 false,
      "is_repaired": false,
      "notes": "기타 메모"
    }}
  ],
  "raw_text": "표에서 추출된 원본 텍스트",
  "confidence": 0.0~1.0 사이 숫자
}}

표나 손상 기록이 없으면 damages를 빈 배열로 반환하세요."""

        try:
            client = self._get_client()
            b64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime};base64,{b64_image}",
                                    "detail": "high",
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=2000,
                temperature=0.1,
            )

            raw_content = response.choices[0].message.content.strip()

            # JSON 파싱 (마크다운 코드블록 제거)
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = json.loads(raw_content)

            return {
                "success": True,
                "damages": parsed.get("damages", []),
                "raw_text": parsed.get("raw_text", ""),
                "confidence": parsed.get("confidence", 0.0),
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON 파싱 실패: {e}",
                "damages": [],
                "raw_text": raw_content if "raw_content" in dir() else "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "damages": [],
            }

    async def analyze_damage_photo(
        self,
        image_bytes: bytes,
        image_mime: str = "image/jpeg",
        damage_code_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        손상 사진 AI 분석 (자동 손상 코드 제안 + 심각도)

        Returns:
            {
                "damage_code": "C1",
                "damage_name": "균열",
                "severity_grade": "C",
                "confidence": 0.82,
                "description": "폭 0.5mm 이상 균열이 거더 하부에서 발견됨",
                "requires_urgent": False,
            }
        """
        if not settings.OPENAI_API_KEY:
            return {"damage_code": damage_code_hint or "", "confidence": 0.0}

        prompt = """이 이미지는 교량/시설물 안전점검 현장 사진입니다.
사진에서 보이는 손상을 분석하여 JSON으로 반환해주세요.

손상코드:
- C1: 균열(Crack)
- S1: 박리/층분리(Spalling)
- E1: 철근노출(Exposed rebar)
- L1: 누수/백태(Leakage)
- D1: 변형/처짐(Deformation)
- J1: 신축이음 손상(Joint damage)
- W1: 세굴(Scour)
- N0: 이상없음

심각도: A(최우수)~E(심각)

형식 (순수 JSON만):
{
  "damage_code": "코드",
  "damage_name": "명칭",
  "severity_grade": "A/B/C/D/E",
  "confidence": 0.0~1.0,
  "description": "상세 설명",
  "requires_urgent": true/false
}"""

        try:
            client = self._get_client()
            b64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime};base64,{b64_image}",
                                    "detail": "high",
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=500,
                temperature=0.1,
            )

            raw_content = response.choices[0].message.content.strip()
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(raw_content)

        except Exception as e:
            return {
                "damage_code": damage_code_hint or "N0",
                "damage_name": "분석 실패",
                "severity_grade": None,
                "confidence": 0.0,
                "description": str(e),
            }


ocr_service = OcrService()
