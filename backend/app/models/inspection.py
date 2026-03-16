import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import enum


class InspectionType(str, enum.Enum):
    ROUTINE = "ROUTINE"       # 정기점검
    PRECISE = "PRECISE"       # 정밀안전진단
    EMERGENCY = "EMERGENCY"   # 긴급점검


class InspectionStatus(str, enum.Enum):
    DRAFT = "DRAFT"           # 초안
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXPORTED = "EXPORTED"     # 엑셀/보고서 출력 완료


class Inspection(Base):
    """점검 이력"""
    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    inspector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspectors.id"), nullable=False
    )
    inspection_type: Mapped[str] = mapped_column(
        String(20), default=InspectionType.ROUTINE.value
    )
    status: Mapped[str] = mapped_column(
        String(20), default=InspectionStatus.IN_PROGRESS.value
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # GPS 이동 경로: [{lat, lng, time, accuracy}, ...]
    gps_track: Mapped[list] = mapped_column(JSON, default=list)

    # 기기 정보 (불법 하도급 감지)
    device_info: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {deviceId, os, osVersion, appVersion, model}

    notes: Mapped[str] = mapped_column(String(2000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    facility: Mapped["Facility"] = relationship(back_populates="inspections")
    inspector: Mapped["Inspector"] = relationship(back_populates="inspections")
    drawings: Mapped[list["Drawing"]] = relationship(back_populates="inspection")
    damage_records: Mapped[list["DamageRecord"]] = relationship(back_populates="inspection")
    photos: Mapped[list["Photo"]] = relationship(back_populates="inspection")
