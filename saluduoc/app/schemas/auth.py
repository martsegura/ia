"""Esquemas de autenticación con mensajes de error en español."""

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError


def normalizar_email(value: str) -> str:
    """Valida y normaliza un correo, con mensaje de error en español."""
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise PydanticCustomError(
            "email_invalido", "Ingresa un correo electrónico válido"
        ) from None


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, value: str) -> str:
        return normalizar_email(value)

    @field_validator("password")
    @classmethod
    def password_valida(cls, value: str) -> str:
        if len(value) < 8:
            raise PydanticCustomError(
                "password_corta", "La contraseña debe tener al menos 8 caracteres"
            )
        if len(value) > 128:
            raise PydanticCustomError(
                "password_larga", "La contraseña no puede superar los 128 caracteres"
            )
        if not any(char.isdigit() for char in value):
            raise PydanticCustomError(
                "password_sin_numero", "La contraseña debe incluir al menos un número"
            )
        return value

    @field_validator("full_name")
    @classmethod
    def nombre_valido(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise PydanticCustomError(
                "nombre_corto", "El nombre completo debe tener al menos 2 caracteres"
            )
        if len(normalized) > 150:
            raise PydanticCustomError(
                "nombre_largo", "El nombre completo no puede superar los 150 caracteres"
            )
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_valido(cls, value: str) -> str:
        return normalizar_email(value)


class MessageResponse(BaseModel):
    message: str
