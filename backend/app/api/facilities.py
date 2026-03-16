from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_inspector
from app.models.facility import Facility, FacilityType
from app.models.inspector import Inspector
from app.schemas.facility import FacilityCreate, FacilityRead, FacilityTypeRead
from app.services.plugin_service import plugin_service

router = APIRouter(prefix="/facilities", tags=["시설물"])


@router.get("/types", response_model=List[FacilityTypeRead])
async def list_facility_types(db: AsyncSession = Depends(get_db)):
    """등록된 시설물 유형(플러그인) 목록"""
    result = await db.execute(select(FacilityType))
    return result.scalars().all()


@router.get("/types/{code}/config")
async def get_plugin_config(code: str):
    """플러그인 설정 조회 (앱에서 다운로드)"""
    try:
        config = plugin_service.load_plugin(code)
        return config
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=FacilityRead, status_code=201)
async def create_facility(
    data: FacilityCreate,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    """시설물 등록"""
    existing = await db.execute(select(Facility).where(Facility.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 존재하는 시설물 코드입니다.")

    facility = Facility(**data.model_dump())
    db.add(facility)
    await db.flush()
    await db.refresh(facility)
    return facility


@router.get("", response_model=List[FacilityRead])
async def list_facilities(
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    """시설물 목록"""
    result = await db.execute(
        select(Facility).where(Facility.is_active == True).order_by(Facility.code)
    )
    return result.scalars().all()


@router.get("/{facility_id}", response_model=FacilityRead)
async def get_facility(
    facility_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(select(Facility).where(Facility.id == facility_id))
    facility = result.scalar_one_or_none()
    if not facility:
        raise HTTPException(status_code=404, detail="시설물을 찾을 수 없습니다.")
    return facility
