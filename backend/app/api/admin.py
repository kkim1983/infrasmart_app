"""관리자 전용 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password
from app.api.deps import get_current_admin
from app.models.inspector import Inspector
from app.models.facility import Facility
from app.models.inspection import Inspection
from app.schemas.inspector import InspectorRead, InspectorCreate, InspectorUpdate
from app.schemas.facility import FacilityRead, FacilityCreate
from app.schemas.inspection import InspectionRead
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["관리자"])


# ─── Stats ──────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    """관리자 대시보드 통계"""
    facility_count = (await db.execute(
        select(func.count()).select_from(Facility).where(Facility.is_active == True)
    )).scalar_one()

    inspector_count = (await db.execute(
        select(func.count()).select_from(Inspector).where(Inspector.is_active == True)
    )).scalar_one()

    inspection_total = (await db.execute(
        select(func.count()).select_from(Inspection)
    )).scalar_one()

    inspection_in_progress = (await db.execute(
        select(func.count()).select_from(Inspection).where(Inspection.status == "IN_PROGRESS")
    )).scalar_one()

    inspection_completed = (await db.execute(
        select(func.count()).select_from(Inspection).where(Inspection.status == "COMPLETED")
    )).scalar_one()

    # 최근 점검 10건
    recent_result = await db.execute(
        select(Inspection).order_by(Inspection.created_at.desc()).limit(10)
    )
    recent = recent_result.scalars().all()

    return {
        "facility_count": facility_count,
        "inspector_count": inspector_count,
        "inspection_total": inspection_total,
        "inspection_in_progress": inspection_in_progress,
        "inspection_completed": inspection_completed,
        "recent_inspections": [InspectionRead.model_validate(i) for i in recent],
    }


# ─── Inspectors ──────────────────────────────────────────────────────────────

@router.get("/inspectors", response_model=list[InspectorRead])
async def list_inspectors(
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    result = await db.execute(select(Inspector).order_by(Inspector.created_at.desc()))
    return result.scalars().all()


@router.post("/inspectors", response_model=InspectorRead, status_code=201)
async def create_inspector(
    data: InspectorCreate,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    existing = await db.execute(select(Inspector).where(Inspector.license_no == data.license_no))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 등록된 자격증 번호입니다.")

    is_admin = bool(
        data.admin_key
        and settings.ADMIN_CREATION_KEY
        and data.admin_key == settings.ADMIN_CREATION_KEY
    )
    inspector = Inspector(
        name=data.name,
        license_no=data.license_no,
        license_type=data.license_type,
        phone=data.phone,
        email=data.email,
        password_hash=hash_password(data.password),
        company_id=data.company_id,
        is_admin=is_admin,
    )
    db.add(inspector)
    await db.flush()
    await db.refresh(inspector)
    return inspector


@router.patch("/inspectors/{inspector_id}", response_model=InspectorRead)
async def update_inspector(
    inspector_id: str,
    data: InspectorUpdate,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    result = await db.execute(select(Inspector).where(Inspector.id == inspector_id))
    inspector = result.scalar_one_or_none()
    if not inspector:
        raise HTTPException(status_code=404, detail="점검자를 찾을 수 없습니다.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(inspector, field, value)
    await db.flush()
    await db.refresh(inspector)
    return inspector


# ─── Facilities ──────────────────────────────────────────────────────────────

@router.get("/facilities", response_model=list[FacilityRead])
async def list_all_facilities(
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    result = await db.execute(
        select(Facility).order_by(Facility.created_at.desc())
    )
    return result.scalars().all()


@router.post("/facilities", response_model=FacilityRead, status_code=201)
async def create_facility(
    data: FacilityCreate,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    existing = await db.execute(select(Facility).where(Facility.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 등록된 시설물 코드입니다.")

    facility = Facility(**data.model_dump())
    db.add(facility)
    await db.flush()
    await db.refresh(facility)
    return facility


@router.patch("/facilities/{facility_id}", response_model=FacilityRead)
async def update_facility(
    facility_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    result = await db.execute(select(Facility).where(Facility.id == facility_id))
    facility = result.scalar_one_or_none()
    if not facility:
        raise HTTPException(status_code=404, detail="시설물을 찾을 수 없습니다.")

    allowed = {"name", "location_name", "is_active", "geofence_data", "facility_meta"}
    for field, value in data.items():
        if field in allowed:
            setattr(facility, field, value)
    await db.flush()
    await db.refresh(facility)
    return facility


# ─── Inspections ─────────────────────────────────────────────────────────────

@router.get("/inspections", response_model=list[InspectionRead])
async def list_all_inspections(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_admin),
):
    q = select(Inspection).order_by(Inspection.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(Inspection.status == status)
    result = await db.execute(q)
    return result.scalars().all()
