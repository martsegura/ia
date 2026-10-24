"""Perfiles específicos de pacientes y médicos."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.establishment import Establishment
    from app.models.user import User


class PatientProfile(TimestampMixin, Base):
    """Datos clínicos básicos del paciente."""

    __tablename__ = "patient_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    rut: Mapped[str | None] = mapped_column(String(12))
    birth_date: Mapped[date | None] = mapped_column(Date)
    sexo: Mapped[str | None] = mapped_column(String(1))
    peso_kg: Mapped[float | None] = mapped_column(Float)
    talla_cm: Mapped[float | None] = mapped_column(Float)
    comorbilidades: Mapped[list[Any]] = mapped_column(JSON, default=list)
    medicamentos: Mapped[list[Any]] = mapped_column(JSON, default=list)
    es_embarazada: Mapped[bool] = mapped_column(Boolean, default=False)
    contacto_emergencia: Mapped[str | None] = mapped_column(String(150))

    user: Mapped[User] = relationship(back_populates="patient_profile")


class DoctorProfile(TimestampMixin, Base):
    """Datos del médico y establecimiento donde atiende."""

    __tablename__ = "doctor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    establecimiento_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("establishments.id", ondelete="SET NULL")
    )
    especialidad: Mapped[str | None] = mapped_column(String(120))

    user: Mapped[User] = relationship(back_populates="doctor_profile")
    establecimiento: Mapped[Establishment | None] = relationship()
