import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, DateTime, Date, JSON, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class DamageRecord(Base):
    """손상 기록 (시설물 유형 무관 공통 구조)"""
    __tablename__ = "damage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id"), nullable=False
    )

    # 손상 코드 (플러그인 정의: C1=균열, S1=박리, E1=철근노출 등)
    damage_code: Mapped[str] = mapped_column(String(10), nullable=False)
    damage_name: Mapped[str] = mapped_column(String(100), nullable=True)  # 한글명 (캐시)

    # 위치 정보 (플러그인이 필드 정의)
    location_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    # 교량: {member_type, member_no, span_no, position}
    # 터널: {station_start, station_end, ring_no, position}

    # 손상 규모 (플러그인이 필드 정의)
    dimensions: Mapped[dict] = mapped_column(JSON, nullable=True)
    # 균열: {length_m, width_mm, depth_mm}
    # 박리: {area_m2, depth_mm}

    severity_grade: Mapped[str] = mapped_column(String(2), nullable=True)  # A, B, C, D, E

    # 손상 상태 플래그
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)       # 신규 손상
    is_expanded: Mapped[bool] = mapped_column(Boolean, default=False)  # 기존 대비 확대
    is_repaired: Mapped[bool] = mapped_column(Boolean, default=False)  # 보수 완료

    repair_date: Mapped[date] = mapped_column(Date, nullable=True)
    repair_method: Mapped[str] = mapped_column(String(200), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # 이전 점검의 동일 손상 연결 (이력 추적)
    prev_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("damage_records.id"), nullable=True
    )

    # 도면 위 위치 참조
    drawing_ref: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {drawingId, x, y}

    local_id: Mapped[str] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    inspection: Mapped["Inspection"] = relationship(back_populates="damage_records")
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="damage_record")
    photos: Mapped[list["Photo"]] = relationship(back_populates="damage_record")
