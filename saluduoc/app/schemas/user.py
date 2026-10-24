"""Esquemas de usuarios y perfiles."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: UserRole
    full_name: str
    is_active: bool
    created_at: datetime
    profile: dict | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    rut: str | None = Field(default=None, max_length=12)
    birth_date: date | None = None
    sexo: Literal["M", "F", "X"] | None = None
    peso_kg: float | None = Field(default=None, gt=0, lt=500)
    talla_cm: float | None = Field(default=None, gt=0, lt=300)
    comorbilidades: list[str] | None = None
    medicamentos: list[str] | None = None
    es_embarazada: bool | None = None
    contacto_emergencia: str | None = Field(default=None, max_length=150)
    especialidad: str | None = Field(default=None, max_length=120)

    @field_validator("full_name")
    @classmethod
    def nombre_limpio(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("El nombre completo debe tener al menos 2 caracteres")
        return normalized


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
