import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Photo(Base):
    """현장 사진"""
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id"), nullable=False
    )
    damage_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("damage_records.id"), nullable=True
    )

    # 사진 번호 자동 부여: BR001-G3-CR-004
    photo_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # 파일
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int] = mapped_column(nullable=True)  # bytes

    # GPS 메타데이터 (촬영 시점)
    gps: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {lat, lng, altitude, accuracy}

    # EXIF 데이터
    exif_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {make, model, focalLength, iso, ...}

    # 손상 유형/규모 (촬영 시 입력)
    damage_code: Mapped[str] = mapped_column(String(10), nullable=True)
    damage_description: Mapped[str] = mapped_column(Text, nullable=True)

    # 도면 위 위치 참조
    drawing_ref: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {drawingId, x, y}

    # Phase 2: AI 분석 결과
    ai_analysis: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {detectedType, confidence, boundingBoxes:[...]}

    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    taken_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspectors.id"), nullable=True
    )

    local_id: Mapped[str] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    inspection: Mapped["Inspection"] = relationship(back_populates="photos")
    damage_record: Mapped["DamageRecord"] = relationship(back_populates="photos")
