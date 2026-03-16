from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_inspector
from app.models.damage import DamageRecord
from app.models.inspector import Inspector
from app.schemas.damage import DamageRecordCreate, DamageRecordRead, DamageRecordUpdate

router = APIRouter(prefix="/damages", tags=["손상기록"])


@router.post("", response_model=DamageRecordRead, status_code=201)
async def create_damage(
    data: DamageRecordCreate,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    record = DamageRecord(**data.model_dump())
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.get("/inspection/{inspection_id}", response_model=List[DamageRecordRead])
async def list_damages(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(
        select(DamageRecord)
        .where(DamageRecord.inspection_id == inspection_id)
        .order_by(DamageRecord.created_at)
    )
    return result.scalars().all()


@router.patch("/{damage_id}", response_model=DamageRecordRead)
async def update_damage(
    damage_id: str,
    data: DamageRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(select(DamageRecord).where(DamageRecord.id == damage_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="손상 기록을 찾을 수 없습니다.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(record, field, value)

    await db.flush()
    await db.refresh(record)
    return record
