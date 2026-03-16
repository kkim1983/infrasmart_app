from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_inspector
from app.models.inspection import Inspection, InspectionStatus
from app.services.audit_service import audit_service
from app.services.webhook_service import webhook_service
from app.models.inspector import Inspector
from app.schemas.inspection import InspectionCreate, InspectionRead, InspectionUpdate, GpsTrackPoint

router = APIRouter(prefix="/inspections", tags=["점검"])


@router.post("", response_model=InspectionRead, status_code=201)
async def start_inspection(
    data: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    """점검 시작"""
    inspection = Inspection(
        facility_id=data.facility_id,
        inspector_id=inspector.id,
        inspection_type=data.inspection_type,
        status=InspectionStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
        device_info=data.device_info,
        notes=data.notes,
    )
    db.add(inspection)
    await db.flush()
    await db.refresh(inspection)

    # 감사 로그 기록 (Phase 2)
    await audit_service.record_event(
        db=db,
        event_type="INSPECTION_STARTED",
        actor_id=str(inspector.id),
        inspection_id=str(inspection.id),
        entity_type="inspection",
        entity_id=str(inspection.id),
        payload={"facility_id": str(data.facility_id), "type": str(data.inspection_type)},
    )

    return inspection


@router.get("", response_model=List[InspectionRead])
async def list_inspections(
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    """내 점검 목록"""
    result = await db.execute(
        select(Inspection)
        .where(Inspection.inspector_id == inspector.id)
        .order_by(Inspection.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{inspection_id}", response_model=InspectionRead)
async def get_inspection(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="점검을 찾을 수 없습니다.")
    return inspection


@router.patch("/{inspection_id}", response_model=InspectionRead)
async def update_inspection(
    inspection_id: str,
    data: InspectionUpdate,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="점검을 찾을 수 없습니다.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(inspection, field, value)

    await db.flush()
    await db.refresh(inspection)
    return inspection


@router.post("/{inspection_id}/gps", status_code=204)
async def append_gps_track(
    inspection_id: str,
    point: GpsTrackPoint,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    """GPS 이동 경로 추가"""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="점검을 찾을 수 없습니다.")

    track = list(inspection.gps_track or [])
    track.append({
        "lat": point.lat,
        "lng": point.lng,
        "accuracy": point.accuracy,
        "time": point.timestamp.isoformat() if point.timestamp else datetime.now(timezone.utc).isoformat(),
    })
    inspection.gps_track = track
    await db.flush()
