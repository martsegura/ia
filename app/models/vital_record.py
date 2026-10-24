"""Registros de signos vitales provenientes de wearables o del formulario."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class VitalRecord(TimestampMixin, Base):
    """Una medición de signos vitales de un paciente."""

    __tablename__ = "vital_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    device: Mapped[str | None] = mapped_column(String(80))
    heart_rate_bpm: Mapped[int | None] = mapped_column(Integer)
    systolic_mmhg: Mapped[int | None] = mapped_column(Integer)
    diastolic_mmhg: Mapped[int | None] = mapped_column(Integer)
    spo2_pct: Mapped[int | None] = mapped_column(Integer)
    sleep_quality_score: Mapped[int | None] = mapped_column(Integer)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
