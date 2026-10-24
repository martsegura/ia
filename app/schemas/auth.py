"""Esquemas de autenticación."""

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)

    @field_validator("password")
    @classmethod
    def password_debe_tener_numero(cls, value: str) -> str:
        if not any(char.isdigit() for char in value):
            raise ValueError("La contraseña debe incluir al menos un número")
        return value

    @field_validator("full_name")
    @classmethod
    def nombre_limpio(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("El nombre completo debe tener al menos 2 caracteres")
        return normalized


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MessageResponse(BaseModel):
    message: str
