import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.storage import get_storage
from app.api.deps import get_current_inspector
from app.models.photo import Photo
from app.models.inspection import Inspection
from app.models.facility import Facility
from app.models.inspector import Inspector
from app.schemas.photo import PhotoCreate, PhotoRead
from app.services.plugin_service import plugin_service

router = APIRouter(prefix="/photos", tags=["사진"])


async def _generate_photo_number(
    db: AsyncSession,
    inspection: Inspection,
    facility: Facility,
    damage_code: str,
    location: str,
) -> str:
    """사진 번호 자동 생성 (BR001-G3-CR-004) - 시설물 전체 기준 전역 순번"""
    facility_code = facility.code.replace("-", "")
    loc = location or "XX"
    code = damage_code or "XX"

    # 손상코드 약어
    code_abbr = {
        "C1": "CR", "C2": "CR",
        "S1": "SP", "S2": "SP",
        "E1": "RE", "L1": "LK",
        "R1": "RP",
    }
    abbr = code_abbr.get(code, code[:2].upper())
    prefix = f"{facility_code}-{loc}-{abbr}-"

    # 해당 시설물의 같은 패턴 사진 전체 개수
    result = await db.execute(
        select(func.count(Photo.id))
        .join(Inspection, Photo.inspection_id == Inspection.id)
        .where(Inspection.facility_id == facility.id)
        .where(Photo.photo_number.like(f"{prefix}%"))
    )
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:03d}"


@router.post("", response_model=PhotoRead, status_code=201)
async def upload_photo(
    inspection_id: str = Form(...),
    damage_record_id: str = Form(None),
    damage_code: str = Form(None),
    damage_description: str = Form(None),
    gps: str = Form(None),           # JSON string
    drawing_ref: str = Form(None),   # JSON string
    location: str = Form("XX"),      # 위치 약칭 (사진번호에 사용)
    taken_at: str = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
    storage=Depends(get_storage),
):
    """사진 업로드 + 메타데이터 자동 저장"""
    # 점검 + 시설물 조회
    insp_result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = insp_result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="점검을 찾을 수 없습니다.")

    fac_result = await db.execute(select(Facility).where(Facility.id == inspection.facility_id))
    facility = fac_result.scalar_one_or_none()

    # 파일 업로드
    file_path = await storage.upload(file, folder=f"photos/{inspection_id}")
    file_url = await storage.get_url(file_path)

    # 사진 번호 자동 생성
    photo_number = await _generate_photo_number(db, inspection, facility, damage_code, location)

    photo = Photo(
        inspection_id=inspection_id,
        damage_record_id=damage_record_id,
        photo_number=photo_number,
        file_url=file_url,
        damage_code=damage_code,
        damage_description=damage_description,
        gps=json.loads(gps) if gps else None,
        drawing_ref=json.loads(drawing_ref) if drawing_ref else None,
        taken_at=datetime.fromisoformat(taken_at) if taken_at else None,
        taken_by=inspector.id,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)
    return photo


@router.get("/inspection/{inspection_id}", response_model=List[PhotoRead])
async def list_photos(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(
        select(Photo)
        .where(Photo.inspection_id == inspection_id)
        .order_by(Photo.photo_number)
    )
    return result.scalars().all()
