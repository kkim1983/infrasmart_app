from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_inspector
from app.models.annotation import Annotation
from app.models.inspector import Inspector
from app.schemas.annotation import AnnotationCreate, AnnotationRead, AnnotationBatchSync

router = APIRouter(prefix="/annotations", tags=["어노테이션"])


@router.post("", response_model=AnnotationRead, status_code=201)
async def create_annotation(
    data: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    annotation = Annotation(
        **data.model_dump(exclude={"damage_record_id"}),
        damage_record_id=data.damage_record_id,
        created_by=inspector.id,
    )
    db.add(annotation)
    await db.flush()
    await db.refresh(annotation)
    return annotation


@router.post("/sync", response_model=List[AnnotationRead])
async def sync_annotations(
    data: AnnotationBatchSync,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    """오프라인에서 쌓인 어노테이션 일괄 동기화"""
    results = []
    for ann_data in data.annotations:
        # local_id로 중복 체크
        if ann_data.local_id:
            existing = await db.execute(
                select(Annotation).where(Annotation.local_id == ann_data.local_id)
            )
            if existing.scalar_one_or_none():
                continue  # 이미 동기화됨

        annotation = Annotation(
            **ann_data.model_dump(exclude={"damage_record_id"}),
            damage_record_id=ann_data.damage_record_id,
            created_by=inspector.id,
        )
        db.add(annotation)
        await db.flush()
        await db.refresh(annotation)
        results.append(annotation)

    return results


@router.get("/drawing/{drawing_id}", response_model=List[AnnotationRead])
async def list_annotations(
    drawing_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(
        select(Annotation).where(Annotation.drawing_id == drawing_id)
    )
    return result.scalars().all()


@router.delete("/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail="어노테이션을 찾을 수 없습니다.")
    await db.delete(annotation)
