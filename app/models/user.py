"""Modelo de usuarios y roles."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import DoctorProfile, PatientProfile


class User(TimestampMixin, Base):
    """Usuario del sistema: paciente, médico o administrador."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            native_enum=False,
            length=20,
            validate_strings=True,
            create_constraint=True,
            name="user_role",
        ),
        nullable=False,
        default=UserRole.PATIENT,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    patient_profile: Mapped[PatientProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    doctor_profile: Mapped[DoctorProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} ({self.role})>"
