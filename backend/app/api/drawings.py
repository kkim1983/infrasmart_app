import math
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.storage import get_storage
from app.api.deps import get_current_inspector
from app.models.drawing import Drawing
from app.models.inspector import Inspector
from app.schemas.drawing import DrawingCreate, DrawingRead, DrawingCalibrate, TransformMatrix

router = APIRouter(prefix="/drawings", tags=["도면"])


@router.post("", response_model=DrawingRead, status_code=201)
async def upload_drawing(
    inspection_id: str = Form(...),
    drawing_type: str = Form(...),
    drawing_name: str = Form(None),
    page_number: int = Form(1),
    coord_system: str = Form("cartesian"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
    storage=Depends(get_storage),
):
    """도면 PDF 업로드"""
    file_path = await storage.upload(file, folder=f"drawings/{inspection_id}")
    file_url = await storage.get_url(file_path)

    drawing = Drawing(
        inspection_id=inspection_id,
        drawing_type=drawing_type,
        drawing_name=drawing_name,
        file_url=file_url,
        page_number=page_number,
        coord_system=coord_system,
    )
    db.add(drawing)
    await db.flush()
    await db.refresh(drawing)
    return drawing


@router.get("/inspection/{inspection_id}", response_model=List[DrawingRead])
async def list_drawings(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    result = await db.execute(
        select(Drawing).where(Drawing.inspection_id == inspection_id)
    )
    return result.scalars().all()


@router.get("/{drawing_id}", response_model=DrawingRead)
async def get_drawing(
    drawing_id: str,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    """도면 단건 조회"""
    result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")
    return drawing


@router.post("/{drawing_id}/calibrate", response_model=DrawingRead)
async def calibrate_drawing(
    drawing_id: str,
    data: DrawingCalibrate,
    db: AsyncSession = Depends(get_db),
    _: Inspector = Depends(get_current_inspector),
):
    """
    CAD 좌표 보정점 설정 (Phase 2: 좌표 정합)
    두 개 이상의 보정점으로 변환 행렬 자동 계산
    """
    result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")

    pts = data.calibration_points
    if len(pts) < 2:
        raise HTTPException(status_code=400, detail="보정점이 2개 이상 필요합니다.")

    # 두 점으로 스케일/오프셋 계산
    p1, p2 = pts[0], pts[1]
    dx_px = p2.pixel_x - p1.pixel_x
    dy_px = p2.pixel_y - p1.pixel_y
    dx_real = p2.real_x - p1.real_x
    dy_real = p2.real_y - p1.real_y

    pixel_dist = math.sqrt(dx_px ** 2 + dy_px ** 2)
    real_dist = math.sqrt(dx_real ** 2 + dy_real ** 2)

    if pixel_dist == 0:
        raise HTTPException(status_code=400, detail="보정점이 동일한 위치입니다.")

    scale = real_dist / pixel_dist
    rotation = math.atan2(dy_real, dx_real) - math.atan2(dy_px, dx_px)

    matrix = {
        "scale_x": scale,
        "scale_y": scale,
        "offset_x": p1.real_x - p1.pixel_x * scale,
        "offset_y": p1.real_y - p1.pixel_y * scale,
        "rotation": rotation,
    }

    drawing.transform_matrix = matrix
    drawing.calibration_points = [pt.model_dump() for pt in pts]
    drawing.scale_text = data.scale_text

    await db.flush()
    await db.refresh(drawing)
    return drawing


@router.get("/{drawing_id}/export/dxf")
async def export_drawing_dxf(
    drawing_id: str,
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    """도면 어노테이션을 DXF 파일로 내보내기 (Phase 2)"""
    from fastapi.responses import Response
    from app.models.annotation import Annotation
    from app.services.cad_service import cad_service

    result = await db.execute(select(Drawing).where(Drawing.id == drawing_id))
    drawing = result.scalar_one_or_none()
    if not drawing:
        raise HTTPException(status_code=404, detail="도면을 찾을 수 없습니다.")

    ann_result = await db.execute(
        select(Annotation).where(Annotation.drawing_id == drawing_id)
    )
    annotations = ann_result.scalars().all()

    ann_list = [
        {
            "ann_type": a.ann_type,
            "layer": a.layer,
            "coordinates": a.coordinates,
            "real_coordinates": a.real_coordinates,
            "content": a.content,
            "style": a.style or {},
        }
        for a in annotations
    ]

    drawing_meta = {
        "drawing_name": drawing.drawing_name or "",
        "drawing_type": drawing.drawing_type,
        "facility_code": "",
        "inspection_date": drawing.created_at.strftime("%Y-%m-%d"),
    }

    dxf_bytes = cad_service.generate_dxf(
        annotations=ann_list,
        transform_matrix=drawing.transform_matrix,
        drawing_meta=drawing_meta,
    )

    filename = f"{drawing.drawing_name or drawing_id}.dxf"
    return Response(
        content=dxf_bytes,
        media_type="application/acad",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
