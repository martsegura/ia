"""Establecimientos de salud (seed desde DEIS/MINSAL)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import JSON, Boolean, Date, Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Establishment(TimestampMixin, Base):
    """Establecimiento de salud con coordenadas para calcular distancias."""

    __tablename__ = "establishments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(120), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(255))
    comuna: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    telefono: Mapped[str | None] = mapped_column(String(80))
    tiene_urgencia: Mapped[bool] = mapped_column(Boolean, default=False)
    servicios: Mapped[list[Any]] = mapped_column(JSON, default=list)
    sede_duoc: Mapped[str | None] = mapped_column(String(120), index=True)
    fuente: Mapped[str | None] = mapped_column(String(255))
    fecha_snapshot: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Establishment {self.nombre} ({self.comuna})>"
