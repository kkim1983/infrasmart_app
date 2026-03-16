"""감사 로그 API (Phase 2)"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.core.database import get_db
from app.api.deps import get_current_inspector
from app.models.inspector import Inspector
from app.models.audit import AuditEvent
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["감사로그"])


class AuditEventRead(BaseModel):
    id: int
    event_type: str
    inspection_id: Optional[uuid.UUID]
    actor_id: Optional[uuid.UUID]
    entity_type: Optional[str]
    entity_id: Optional[uuid.UUID]
    payload: dict
    gps_snapshot: Optional[dict]
    prev_hash: Optional[str]
    event_hash: Optional[str]
    signature: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class KeyPairGenerate(BaseModel):
    public_key_pem: str


class SignatureVerify(BaseModel):
    event_hash: str
    signature: str
    public_key_pem: str


@router.get("/{inspection_id}", response_model=List[AuditEventRead])
async def get_audit_trail(
    inspection_id: str,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    """점검 감사 이력 조회 (시간순)"""
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.inspection_id == inspection_id)
        .order_by(AuditEvent.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{inspection_id}/verify")
async def verify_audit_integrity(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    """감사 로그 해시 체인 무결성 검증"""
    return await audit_service.verify_chain_integrity(db, inspection_id)


@router.post("/keypair/generate", response_model=KeyPairGenerate)
async def generate_inspector_keypair(
    _: Inspector = Depends(get_current_inspector),
):
    """
    점검자 ECDSA 키쌍 생성 (최초 1회)
    개인키는 반환 즉시 클라이언트 보안저장소에만 저장하세요.
    """
    keys = audit_service.generate_key_pair()
    # 서버에는 공개키만 반환 (개인키 보관 안함)
    return {"public_key_pem": keys["public_key_pem"], "_private": keys["private_key_pem"]}


@router.post("/signature/verify")
async def verify_event_signature(
    data: SignatureVerify,
    _: Inspector = Depends(get_current_inspector),
):
    """이벤트 서명 검증"""
    is_valid = audit_service.verify_signature(
        event_hash=data.event_hash,
        signature_b64=data.signature,
        public_key_pem=data.public_key_pem,
    )
    return {"is_valid": is_valid}
