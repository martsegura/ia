"""Esquemas de signos vitales, triage y cola."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError


class VitalIn(BaseModel):
    recorded_at: datetime | None = None
    device: str | None = Field(default=None, max_length=80)
    heart_rate_bpm: int | None = Field(default=None, ge=20, le=250)
    systolic_mmhg: int | None = Field(default=None, ge=40, le=300)
    diastolic_mmhg: int | None = Field(default=None, ge=20, le=200)
    spo2_pct: int | None = Field(default=None, ge=50, le=100)
    sleep_quality_score: int | None = Field(default=None, ge=0, le=100)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    symptoms: list[str] = Field(default_factory=list, max_length=20)
    pain_scale: int | None = Field(default=None, ge=0, le=10)
    onset: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=1000)
    establishment_id: UUID | None = None

    @model_validator(mode="after")
    def validar_vitales(self) -> "VitalIn":
        metrics = (
            self.heart_rate_bpm,
            self.systolic_mmhg,
            self.diastolic_mmhg,
            self.spo2_pct,
        )
        if all(value is None for value in metrics):
            raise PydanticCustomError(
                "sin_vitales", "Ingresa al menos un signo vital (FC, presión o saturación)"
            )
        if (
            self.systolic_mmhg is not None
            and self.diastolic_mmhg is not None
            and self.systolic_mmhg <= self.diastolic_mmhg
        ):
            raise PydanticCustomError(
                "presion_invalida",
                "La presión sistólica debe ser mayor que la diastólica",
            )
        return self


class WatchRecordIn(BaseModel):
    timestamp: datetime | None = None
    heart_rate_bpm: int | None = Field(default=None, ge=20, le=250)
    blood_pressure: dict[str, int] | None = None
    oxygen_saturation_pct: int | None = Field(default=None, ge=50, le=100)
    sleep_quality: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validar(self) -> "WatchRecordIn":
        if (
            self.heart_rate_bpm is None
            and self.blood_pressure is None
            and self.oxygen_saturation_pct is None
        ):
            raise PydanticCustomError(
                "registro_vacio", "El registro no contiene signos vitales"
            )
        return self


class WatchUploadIn(BaseModel):
    device: str | None = Field(default=None, max_length=80)
    records: list[WatchRecordIn] = Field(min_length=1, max_length=50)
    establishment_id: UUID | None = None


class VitalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recorded_at: datetime
    source: str
    device: str | None
    heart_rate_bpm: int | None
    systolic_mmhg: int | None
    diastolic_mmhg: int | None
    spo2_pct: int | None
    sleep_quality_score: int | None
    sleep_hours: float | None


class QueueEntryOut(BaseModel):
    id: UUID
    assessment_id: UUID
    establishment_id: UUID
    patient_id: UUID
    patient_name: str
    establishment_name: str
    category: str
    color: str
    priority: int
    status: str
    position: int | None = None
    wait_minutes: int | None = None
    created_at: datetime
    called_at: datetime | None = None
    attended_at: datetime | None = None
    notes: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    vitals: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class AssessmentOut(BaseModel):
    id: UUID
    category: str
    color: str
    score: float
    triggered_rules: list[dict[str, Any]]
    rationale: str
    algorithm_version: str
    ranges_version: str
    created_at: datetime
    queue: QueueEntryOut | None = None


class LatestAssessmentOut(BaseModel):
    assessment: AssessmentOut | None = None


class QueueStatusIn(BaseModel):
    status: Literal["called", "in_attention", "attended", "left"]


class EstablishmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    tipo: str
    direccion: str | None
    comuna: str | None
    region: str | None
    lat: float | None
    lng: float | None
    telefono: str | None
    tiene_urgencia: bool
    sede_duoc: str | None
    distance_km: float | None = None
