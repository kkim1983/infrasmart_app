import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, BigInteger, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AuditEvent(Base):
    """
    불변 감사 로그 (Append-Only)
    INSERT만 허용, UPDATE/DELETE 불가 (DB Row-Level Security로 강제)
    """
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 이벤트 유형
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # INSPECTION_STARTED | DRAWING_OPENED | ANNOTATION_CREATED | PHOTO_TAKEN
    # DAMAGE_UPDATED | OCR_EXTRACTED | INSPECTION_ENDED | REPORT_EXPORTED

    # 관련 엔티티
    inspection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)  # inspector
    entity_type: Mapped[str] = mapped_column(String(30), nullable=True)
    # drawing | annotation | photo | damage | inspection
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    # 이벤트 데이터 (변경 전/후 모두 포함)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # GPS 스냅샷 (이벤트 시점 위치)
    gps_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Phase 2: 해시 체인 (불변성 증명)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=True)   # SHA256
    event_hash: Mapped[str] = mapped_column(String(64), nullable=True)  # SHA256(payload+prev)

    # Phase 2: 디지털 서명
    signature: Mapped[str] = mapped_column(Text, nullable=True)  # ECDSA

    # Phase 2: 공인 타임스탬프 (KISA TSA)
    tsa_token: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_inspection_id", "inspection_id"),
        Index("ix_audit_actor_id", "actor_id"),
        Index("ix_audit_created_at", "created_at"),
    )
