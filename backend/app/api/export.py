from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.deps import get_current_inspector
from app.models.inspection import Inspection
from app.models.facility import Facility
from app.models.inspector import Inspector
from app.models.damage import DamageRecord
from app.models.photo import Photo
from app.services.export_service import export_service
from app.services.audit_service import audit_service
from app.services.webhook_service import webhook_service

router = APIRouter(prefix="/export", tags=["내보내기"])


@router.get("/{inspection_id}/excel")
async def export_excel(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    """점검 결과 엑셀 파일 생성 및 다운로드"""
    # 점검 조회
    insp_result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = insp_result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="점검을 찾을 수 없습니다.")

    # 시설물 조회
    fac_result = await db.execute(select(Facility).where(Facility.id == inspection.facility_id))
    facility = fac_result.scalar_one_or_none()

    # 손상 기록 조회
    dmg_result = await db.execute(
        select(DamageRecord).where(DamageRecord.inspection_id == inspection_id)
    )
    damage_records = [r.__dict__ for r in dmg_result.scalars().all()]

    # 사진 조회
    photo_result = await db.execute(
        select(Photo).where(Photo.inspection_id == inspection_id).order_by(Photo.photo_number)
    )
    photos = [p.__dict__ for p in photo_result.scalars().all()]

    # 엑셀 생성
    excel_bytes = export_service.generate_inspection_report(
        inspection=inspection.__dict__,
        facility=facility.__dict__,
        inspector=inspector.__dict__,
        damage_records=damage_records,
        photos=photos,
        gps_track=list(inspection.gps_track or []),
    )

    filename = f"inspection_{facility.code}_{inspection_id[:8]}.xlsx"
    filename_kr = f"점검결과_{facility.code}_{inspection_id[:8]}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename_kr)}"},
    )
