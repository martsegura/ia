"""Síntomas declarados por el paciente junto con sus signos vitales."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class SymptomReport(TimestampMixin, Base):
    __tablename__ = "symptom_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vital_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vital_records.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    symptoms: Mapped[list[Any]] = mapped_column(JSON, default=list)
    pain_scale: Mapped[int | None] = mapped_column(Integer)
    onset: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
