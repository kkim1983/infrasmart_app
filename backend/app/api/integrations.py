"""외부 솔루션 연동 API (Phase 2)"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

from app.api.deps import get_current_inspector
from app.models.inspector import Inspector
from app.services.webhook_service import webhook_service, WEBHOOK_EVENTS

router = APIRouter(prefix="/integrations", tags=["외부연동"])


class WebhookCreate(BaseModel):
    url: str
    events: List[str]
    secret: Optional[str] = None
    description: Optional[str] = ""


class WebhookRead(BaseModel):
    id: str
    url: str
    events: List[str]
    description: str
    is_active: bool
    created_at: str
    delivery_count: int
    failure_count: int


class WebhookDispatch(BaseModel):
    event_type: str
    data: dict
    inspection_id: Optional[str] = None


@router.get("/events")
async def list_supported_events(
    _: Inspector = Depends(get_current_inspector),
):
    """지원하는 Webhook 이벤트 목록"""
    return [
        {"event": k, "description": v}
        for k, v in WEBHOOK_EVENTS.items()
    ]


@router.post("/webhooks", response_model=WebhookRead, status_code=201)
async def register_webhook(
    data: WebhookCreate,
    _: Inspector = Depends(get_current_inspector),
):
    """Webhook 등록"""
    # 이벤트 검증
    invalid = [e for e in data.events if e not in WEBHOOK_EVENTS and e != "*"]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 이벤트: {invalid}. /integrations/events에서 목록 확인"
        )

    webhook_id = str(uuid.uuid4())
    secret = data.secret or str(uuid.uuid4()).replace("-", "")

    config = webhook_service.get_store().register(
        webhook_id=webhook_id,
        url=data.url,
        events=data.events,
        secret=secret,
        description=data.description or "",
    )
    # secret은 등록 시에만 반환
    return {**config, "_secret_once": secret}


@router.get("/webhooks", response_model=List[WebhookRead])
async def list_webhooks(
    _: Inspector = Depends(get_current_inspector),
):
    """등록된 Webhook 목록"""
    return webhook_service.get_store().list_all()


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    _: Inspector = Depends(get_current_inspector),
):
    """Webhook 삭제"""
    if not webhook_service.get_store().unregister(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook을 찾을 수 없습니다.")
    return {"message": "삭제되었습니다."}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    _: Inspector = Depends(get_current_inspector),
):
    """Webhook 연결 테스트"""
    result = await webhook_service.test_webhook(webhook_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=f"Webhook 전송 실패: {result.get('error')}",
        )
    return result


@router.post("/webhooks/dispatch")
async def manual_dispatch(
    data: WebhookDispatch,
    _: Inspector = Depends(get_current_inspector),
):
    """
    수동 Webhook 발송 (테스트/재발송용)

    event_type: inspection.completed, damage.critical_found 등
    """
    if data.event_type not in WEBHOOK_EVENTS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 이벤트: {data.event_type}"
        )

    results = await webhook_service.dispatch(
        event_type=data.event_type,
        data=data.data,
        inspection_id=data.inspection_id,
    )
    return {
        "dispatched": len(results),
        "success_count": sum(1 for r in results if r.get("success")),
        "results": results,
    }


@router.get("/webhooks/{inspection_id}/payload-preview")
async def preview_inspection_payload(
    inspection_id: str,
    _: Inspector = Depends(get_current_inspector),
):
    """
    점검 완료 시 외부 발송될 표준 JSON 페이로드 미리보기
    (실제 발송 없이 포맷 확인용)
    """
    return {
        "id": "evt_preview",
        "event": "inspection.completed",
        "created_at": "2024-01-01T09:00:00Z",
        "api_version": "2024-03",
        "source": "infrasmart",
        "inspection_id": inspection_id,
        "data": {
            "facility_code": "BR-001",
            "facility_name": "예시교",
            "inspector_name": "홍길동",
            "started_at": "2024-01-01T09:00:00Z",
            "ended_at": "2024-01-01T11:30:00Z",
            "total_damages": 5,
            "critical_damages": 1,
            "photo_count": 23,
            "report_url": f"/export/{inspection_id}/excel",
            "audit_verified": True,
        },
    }
