import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Company(Base):
    """점검 회사"""
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    license_no: Mapped[str] = mapped_column(String(50), nullable=True)  # 안전점검 업체 면허
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    inspectors: Mapped[list["Inspector"]] = relationship(back_populates="company")


class Inspector(Base):
    """점검자"""
    __tablename__ = "inspectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    license_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # 자격증 번호
    license_type: Mapped[str] = mapped_column(String(100), nullable=True)  # 자격 종류
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )

    # Phase 2: 디지털 서명용 공개키
    public_key: Mapped[str] = mapped_column(Text, nullable=True)

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    company: Mapped["Company"] = relationship(back_populates="inspectors")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="inspector")
