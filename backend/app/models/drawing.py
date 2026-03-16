import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Drawing(Base):
    """도면 (PDF)"""
    __tablename__ = "drawings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id"), nullable=False
    )

    # 도면 유형 (플러그인 정의: GD=일반도, SD=구조도, LD=종단면도, UD=전개도 등)
    drawing_type: Mapped[str] = mapped_column(String(10), nullable=False)
    drawing_name: Mapped[str] = mapped_column(String(200), nullable=True)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=1)

    # CAD 좌표 정합 (Phase 2)
    transform_matrix: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {scaleX, scaleY, offsetX, offsetY, rotation}
    calibration_points: Mapped[list] = mapped_column(JSON, nullable=True)
    # [{pixelX, pixelY, realX, realY}, ...]
    scale_text: Mapped[str] = mapped_column(String(20), nullable=True)  # "1:100"
    coord_system: Mapped[str] = mapped_column(
        String(20), default="cartesian"
    )  # cartesian | unfolded | section

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    inspection: Mapped["Inspection"] = relationship(back_populates="drawings")
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="drawing")
