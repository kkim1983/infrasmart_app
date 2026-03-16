from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models.inspector import Inspector
from app.schemas.inspector import InspectorCreate, InspectorRead, LoginRequest, TokenResponse
from app.schemas.geofence import GeofenceCheckRequest, GeofenceCheckResponse
from app.models.facility import Facility
from app.services.geofence_service import (
    check_circular_geofence, check_linear_geofence, detect_gps_spoofing
)

router = APIRouter(prefix="/auth", tags=["인증"])


@router.post("/register", response_model=InspectorRead, status_code=201)
async def register(data: InspectorCreate, db: AsyncSession = Depends(get_db)):
    """점검자 등록"""
    existing = await db.execute(
        select(Inspector).where(Inspector.license_no == data.license_no)
    )
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


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """로그인 + JWT 토큰 발급"""
    result = await db.execute(
        select(Inspector).where(Inspector.license_no == data.license_no)
    )
    inspector = result.scalar_one_or_none()

    if not inspector or not verify_password(data.password, inspector.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="자격증 번호 또는 비밀번호가 올바르지 않습니다.",
        )
    if not inspector.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")

    token = create_access_token(
        subject=str(inspector.id),
        extra_claims={
            "name": inspector.name,
            "license_no": inspector.license_no,
            "is_admin": inspector.is_admin,
            "device_info": data.device_info,
        },
    )
    return TokenResponse(
        access_token=token,
        inspector=InspectorRead.model_validate(inspector),
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.post("/geofence/check", response_model=GeofenceCheckResponse)
async def check_geofence(
    req: GeofenceCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """현장 진입 GPS 검증"""
    result = await db.execute(select(Facility).where(Facility.id == req.facility_id))
    facility = result.scalar_one_or_none()
    if not facility:
        raise HTTPException(status_code=404, detail="시설물을 찾을 수 없습니다.")

    gd = facility.geofence_data or {}

    if facility.geofence_type == "circular":
        center_lat = gd.get("center_lat", 0)
        center_lng = gd.get("center_lng", 0)
        radius_m = gd.get("radius_m", settings.DEFAULT_GEOFENCE_RADIUS_M)
        is_inside, distance = check_circular_geofence(
            req.lat, req.lng, center_lat, center_lng, radius_m, req.accuracy
        )
    elif facility.geofence_type == "linear":
        polyline = gd.get("polyline", [])
        buffer_m = gd.get("buffer_m", 100)
        is_inside, distance = check_linear_geofence(req.lat, req.lng, polyline, buffer_m)
        radius_m = buffer_m
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 지오펜스 유형입니다.")

    message = (
        f"현장 내부 확인됨 (거리: {distance:.0f}m)"
        if is_inside
        else f"현장 외부 ({distance:.0f}m, 허용: {radius_m}m 이내)"
    )

    return GeofenceCheckResponse(
        is_inside=is_inside,
        distance_m=round(distance, 1),
        allowed_radius_m=radius_m,
        facility_name=facility.name,
        message=message,
    )
