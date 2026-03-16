import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Annotation(Base):
    """도면 위 어노테이션 (마킹)"""
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    drawing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drawings.id"), nullable=False
    )

    # 어노테이션 유형
    ann_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # pen | text | voice | circle | rect | arrow | marker

    # 레이어 (CAD 레이어 매핑에 사용)
    layer: Mapped[str] = mapped_column(String(30), nullable=False)
    # damage_new(빨강) | damage_exist(노랑) | damage_expanded(주황) | repaired(초록) | note(흰색)

    # 좌표 (PDF 픽셀 좌표계)
    coordinates: Mapped[list] = mapped_column(JSON, nullable=False)
    # pen: [{x,y},...] / shape: {x,y,w,h} / text: {x,y}

    # 변환된 실제 좌표 (CAD mm 단위, Phase 2에서 채워짐)
    real_coordinates: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 내용 (텍스트 어노테이션, 음성 변환 텍스트)
    content: Mapped[str] = mapped_column(Text, nullable=True)

    # 스타일
    style: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {color, strokeWidth, fontSize, opacity}

    # 연결된 손상 기록
    damage_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("damage_records.id"), nullable=True
    )

    # 오프라인 동기화용 로컬 ID
    local_id: Mapped[str] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspectors.id"), nullable=True
    )

    drawing: Mapped["Drawing"] = relationship(back_populates="annotations")
    damage_record: Mapped["DamageRecord"] = relationship(back_populates="annotations")
