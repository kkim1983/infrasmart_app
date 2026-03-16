"""OCR API - 손상현황표 자동 추출 (Phase 2)"""

import io
import tempfile
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_inspector
from app.models.inspector import Inspector
from app.models.damage import DamageRecord
from app.models.inspection import Inspection
from app.services.ocr_service import ocr_service
from app.services.plugin_service import plugin_service

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract-table")
async def extract_damage_table(
    file: UploadFile = File(...),
    inspection_id: Optional[str] = Form(None),
    facility_type: str = Form("BR"),
    auto_create_records: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    inspector: Inspector = Depends(get_current_inspector),
):
    """
    도면/현장 사진에서 손상현황표 자동 추출

    - file: 이미지 파일 (JPEG, PNG, PDF 첫 페이지)
    - inspection_id: 손상 기록 자동 생성 시 연결할 점검 ID
    - auto_create_records: True이면 추출 결과를 DB에 자동 저장
    """
    content = await file.read()
    mime_type = file.content_type or "image/jpeg"

    # PDF이면 첫 페이지를 이미지로 변환 (Pillow + pdf2image 필요)
    if mime_type == "application/pdf":
        try:
            import pdf2image
            images = pdf2image.convert_from_bytes(content, dpi=200, first_page=1, last_page=1)
            import io
            img_io = io.BytesIO()
            images[0].save(img_io, format="JPEG")
            content = img_io.getvalue()
            mime_type = "image/jpeg"
        except ImportError:
            raise HTTPException(
                status_code=400,
                detail="PDF 처리를 위해 pdf2image 패키지가 필요합니다. 이미지 파일을 직접 업로드하세요."
            )

    # 플러그인 설정 로드
    try:
        plugin_cfg = plugin_service.get_config(facility_type)
    except Exception:
        plugin_cfg = None

    result = await ocr_service.extract_damage_table(
        image_bytes=content,
        image_mime=mime_type,
        facility_type=facility_type,
        plugin_config=plugin_cfg,
    )

    # 자동 손상 기록 생성
    created_ids = []
    if auto_create_records and result["success"] and inspection_id:
        for dmg in result.get("damages", []):
            record = DamageRecord(
                inspection_id=inspection_id,
                damage_code=dmg.get("damage_code", "N0"),
                damage_name=dmg.get("damage_name", ""),
                severity_grade=dmg.get("severity_grade"),
                is_new=dmg.get("is_new", True),
                is_repaired=dmg.get("is_repaired", False),
                notes=dmg.get("notes", ""),
                dimensions={
                    "length_m": dmg.get("length_m"),
                    "width_mm": dmg.get("width_mm"),
                    "area_m2": dmg.get("area_m2"),
                },
                location_data={"location": dmg.get("location", "")},
            )
            db.add(record)
            await db.flush()
            created_ids.append(str(record.id))

    return {
        **result,
        "auto_created_record_ids": created_ids,
    }


@router.post("/analyze-photo")
async def analyze_damage_photo(
    file: UploadFile = File(...),
    damage_code_hint: Optional[str] = Form(None),
    inspector: Inspector = Depends(get_current_inspector),
):
    """
    손상 사진 AI 분석 - 손상 코드 자동 제안 (Phase 2)

    카메라 촬영 후 자동으로 호출, 손상 코드/심각도 제안
    """
    content = await file.read()
    mime_type = file.content_type or "image/jpeg"

    return await ocr_service.analyze_damage_photo(
        image_bytes=content,
        image_mime=mime_type,
        damage_code_hint=damage_code_hint,
    )


@router.post("/extract-pdf")
async def extract_pdf_damage_table(
    file: UploadFile = File(...),
    bridge_name: str = Form(""),
    export_excel: bool = Form(True),
    inspector: Inspector = Depends(get_current_inspector),
):
    """
    외관조사망도 PDF에서 손상물량표 전체 추출.

    - file: 외관조사망도 PDF 파일
    - bridge_name: 교량명 (Excel에 기입될 이름)
    - export_excel: True이면 Excel 파일 다운로드 응답 반환

    PDF의 각 페이지에서 손상물량표를 파싱하여:
    - 부재명, 부재위치, 손상내용, 규모(균열폭/길이/너비), 개소, 단위, 물량 추출
    - 위치코드(S1~S10, P1~P9, A1~A2) 자동 감지
    - 컬럼 위치 동적 감지 (도면마다 다른 레이아웃 대응)
    """
    try:
        from app.services.pdf_damage_parser import parse_pdf, export_to_excel
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF 파서 서비스를 로드할 수 없습니다."
        )

    content = await file.read()

    # 임시 파일에 저장 (pdfplumber는 파일 경로 필요)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = parse_pdf(tmp_path, bridge_name)
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"PDF 파싱 실패: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not export_excel:
        # JSON 응답
        return {
            "bridge_name":   result["bridge_name"],
            "total_pages":   result["total_pages"],
            "total_records": result["total_records"],
            "page_summary":  result["page_summary"],
            "records":       result["records"],
        }

    # Excel 파일 스트리밍 응답
    out_buf = io.BytesIO()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xl:
        tmp_xl_path = tmp_xl.name

    try:
        export_to_excel(result["records"], tmp_xl_path, bridge_name)
        with open(tmp_xl_path, "rb") as f:
            out_buf.write(f.read())
    finally:
        if os.path.exists(tmp_xl_path):
            os.unlink(tmp_xl_path)

    out_buf.seek(0)
    safe_name = (bridge_name or "bridge").replace(" ", "_")
    # Content-Disposition: HTTP 헤더에 한글 직접 사용 불가 → RFC 5987 UTF-8 인코딩
    filename_ascii = safe_name.encode("ascii", errors="ignore").decode() or "bridge"
    filename_utf8  = quote(f"{safe_name}_손상물량표.xlsx")

    return StreamingResponse(
        out_buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename_ascii}_damage.xlsx";'
                f" filename*=UTF-8''{filename_utf8}"
            ),
            "X-Total-Records": str(result["total_records"]),
            "X-Total-Pages":   str(result["total_pages"]),
        },
    )
