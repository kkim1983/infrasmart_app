import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class FacilityType(Base):
    """시설물 유형 플러그인 등록 테이블"""
    __tablename__ = "facility_types"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)  # BR, TN, DM, RD
    name: Mapped[str] = mapped_column(String(50), nullable=False)   # 교량, 터널, 댐
    plugin_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    config: Mapped[dict] = mapped_column(JSON, nullable=False)       # 플러그인 전체 설정
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    facilities: Mapped[list["Facility"]] = relationship(back_populates="facility_type_rel")


class Facility(Base):
    """시설물 (교량/터널/댐 공통)"""
    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    facility_type: Mapped[str] = mapped_column(
        String(2), ForeignKey("facility_types.code"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # BR-001
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_name: Mapped[str] = mapped_column(String(200), nullable=True)

    # 지오펜스 설정 (교량: circular, 터널: linear)
    geofence_type: Mapped[str] = mapped_column(String(20), default="circular")
    geofence_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    # circular: {center_lat, center_lng, radius_m}
    # linear: {polyline: [[lat,lng],...], buffer_m}

    # 시설물별 메타데이터 (플러그인이 정의)
    facility_meta: Mapped[dict] = mapped_column(JSON, nullable=True)
    # 교량: {bridge_length, width, span_count, built_year, road_name}
    # 터널: {tunnel_length, inner_diameter, built_year}

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    facility_type_rel: Mapped["FacilityType"] = relationship(back_populates="facilities")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="facility")
