"""
Webhook / 외부 연동 서비스 (Phase 2)

외부 솔루션(시설물 관리 시스템, 보고서 자동화 등)과의 표준 JSON 연동
- Webhook 등록/해제
- 이벤트 발생 시 자동 발송 (httpx 비동기)
- 재시도 로직 (3회, 지수 백오프)
- 표준화된 페이로드 포맷
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import httpx


# Webhook 이벤트 유형
WEBHOOK_EVENTS = {
    "inspection.started": "점검 시작",
    "inspection.completed": "점검 완료",
    "inspection.report_exported": "보고서 생성",
    "damage.critical_found": "심각 손상 발견 (E등급)",
    "photo.ai_analyzed": "AI 사진 분석 완료",
}


class WebhookConfig:
    """인메모리 Webhook 설정 저장소 (Phase 3에서 DB로 이전)"""

    def __init__(self):
        self._webhooks: Dict[str, Dict] = {}

    def register(
        self,
        webhook_id: str,
        url: str,
        events: List[str],
        secret: str,
        description: str = "",
    ) -> Dict[str, Any]:
        config = {
            "id": webhook_id,
            "url": url,
            "events": events,
            "secret": secret,
            "description": description,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_delivery_at": None,
            "delivery_count": 0,
            "failure_count": 0,
        }
        self._webhooks[webhook_id] = config
        return config

    def unregister(self, webhook_id: str) -> bool:
        return self._webhooks.pop(webhook_id, None) is not None

    def get(self, webhook_id: str) -> Optional[Dict]:
        return self._webhooks.get(webhook_id)

    def list_all(self) -> List[Dict]:
        return list(self._webhooks.values())

    def get_for_event(self, event_type: str) -> List[Dict]:
        return [
            w for w in self._webhooks.values()
            if w["is_active"] and event_type in w["events"]
        ]

    def update_delivery_stats(self, webhook_id: str, success: bool):
        if webhook_id in self._webhooks:
            self._webhooks[webhook_id]["last_delivery_at"] = datetime.now(timezone.utc).isoformat()
            self._webhooks[webhook_id]["delivery_count"] += 1
            if not success:
                self._webhooks[webhook_id]["failure_count"] += 1


_webhook_store = WebhookConfig()


class WebhookService:

    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 10

    def get_store(self) -> WebhookConfig:
        return _webhook_store

    def _build_signature(self, payload_bytes: bytes, secret: str) -> str:
        """HMAC-SHA256 서명 (GitHub Webhook 방식)"""
        sig = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={sig}"

    def _build_standard_payload(
        self,
        event_type: str,
        data: Dict[str, Any],
        inspection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """표준화된 InfraSmart Webhook 페이로드"""
        return {
            "id": f"evt_{int(time.time() * 1000)}",
            "event": event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "api_version": "2024-03",
            "source": "infrasmart",
            "inspection_id": inspection_id,
            "data": data,
        }

    async def dispatch(
        self,
        event_type: str,
        data: Dict[str, Any],
        inspection_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        이벤트 발생 시 등록된 모든 Webhook 발송

        Returns: 각 Webhook 발송 결과 목록
        """
        webhooks = _webhook_store.get_for_event(event_type)
        if not webhooks:
            return []

        payload = self._build_standard_payload(event_type, data, inspection_id)
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        results = []
        async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
            for webhook in webhooks:
                result = await self._deliver_with_retry(
                    client=client,
                    webhook=webhook,
                    payload_bytes=payload_bytes,
                    payload=payload,
                )
                _webhook_store.update_delivery_stats(webhook["id"], result["success"])
                results.append(result)

        return results

    async def _deliver_with_retry(
        self,
        client: httpx.AsyncClient,
        webhook: Dict,
        payload_bytes: bytes,
        payload: Dict,
    ) -> Dict[str, Any]:
        """지수 백오프 재시도"""
        signature = self._build_signature(payload_bytes, webhook["secret"])
        headers = {
            "Content-Type": "application/json",
            "X-InfraSmart-Signature": signature,
            "X-InfraSmart-Event": payload["event"],
            "X-InfraSmart-Delivery": payload["id"],
            "User-Agent": "InfraSmart-Webhook/1.0",
        }

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = await client.post(
                    webhook["url"],
                    content=payload_bytes,
                    headers=headers,
                )
                if resp.status_code < 300:
                    return {
                        "webhook_id": webhook["id"],
                        "url": webhook["url"],
                        "success": True,
                        "status_code": resp.status_code,
                        "attempts": attempt + 1,
                    }
                last_error = f"HTTP {resp.status_code}"
            except httpx.TimeoutException:
                last_error = "Timeout"
            except Exception as e:
                last_error = str(e)

            # 지수 백오프 (0.5s, 1s, 2s)
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))

        return {
            "webhook_id": webhook["id"],
            "url": webhook["url"],
            "success": False,
            "error": last_error,
            "attempts": self.MAX_RETRIES,
        }

    async def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Webhook 연결 테스트"""
        webhook = _webhook_store.get(webhook_id)
        if not webhook:
            return {"success": False, "error": "Webhook을 찾을 수 없습니다."}

        test_payload = self._build_standard_payload(
            event_type="webhook.test",
            data={"message": "InfraSmart Webhook 연결 테스트", "webhook_id": webhook_id},
        )
        payload_bytes = json.dumps(test_payload, ensure_ascii=False).encode("utf-8")

        async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
            return await self._deliver_with_retry(
                client=client,
                webhook=webhook,
                payload_bytes=payload_bytes,
                payload=test_payload,
            )


# asyncio 임포트 필요
import asyncio

webhook_service = WebhookService()
