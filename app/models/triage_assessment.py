"""Resultado explicable del motor de triage."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TriageAssessment(Base):
    __tablename__ = "triage_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vital_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vital_records.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    symptom_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("symptom_reports.id", ondelete="SET NULL")
    )
    establishment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("establishments.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[str] = mapped_column(String(2), nullable=False)
    color: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    triggered_rules: Mapped[list[Any]] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    ranges_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    final_category: Mapped[str | None] = mapped_column(String(2))
    override_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    vital_record: Mapped[Any] = relationship("VitalRecord")
    symptom_report: Mapped[Any] = relationship("SymptomReport")
