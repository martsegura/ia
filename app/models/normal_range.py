"""Rangos de normalidad versionados (MINSAL)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class NormalRange(TimestampMixin, Base):
    """Umbrales por métrica. Ej.: FC normal 60-100, leve 50-59/101-120."""

    __tablename__ = "normal_ranges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    metric: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    normal_min: Mapped[float | None] = mapped_column(Float)
    normal_max: Mapped[float | None] = mapped_column(Float)
    mild_low: Mapped[float | None] = mapped_column(Float)
    mild_high: Mapped[float | None] = mapped_column(Float)
    moderate_low: Mapped[float | None] = mapped_column(Float)
    moderate_high: Mapped[float | None] = mapped_column(Float)
    critical_low: Mapped[float | None] = mapped_column(Float)
    critical_high: Mapped[float | None] = mapped_column(Float)
    edad_min: Mapped[int | None] = mapped_column(Integer)
    edad_max: Mapped[int | None] = mapped_column(Integer)
    sexo: Mapped[str | None] = mapped_column(String(1))
    is_informational: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    fuente: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<NormalRange {self.metric} {self.version}>"
