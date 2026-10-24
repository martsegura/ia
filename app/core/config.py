"""Configuración central de SaluDuoc.

Todos los valores se pueden sobrescribir con variables de entorno o con el
archivo .env (ver .env.example).
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_SECRET_KEYS = {
    "dev-secret-change-me",
    "dev-secret-change-me-please-32-chars-min",
    "cambia-esta-clave-en-produccion-32-chars",
    "secret",
    "changeme",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    DATABASE_URL: str = "postgresql+psycopg://saluduoc:saluduoc@localhost:5434/saluduoc"
    SECRET_KEY: str = "dev-secret-change-me-please-32-chars-min"
    ENV: str = "dev"
    COOKIE_NAME: str = "saluduoc_token"
    COOKIE_SECURE: bool = False
    TOKEN_TTL_MINUTES: int = 720
    RATE_LIMIT_LOGIN: int = 5
    APP_NAME: str = "SaluDuoc"
    APP_VERSION: str = "0.1.0"

    @model_validator(mode="after")
    def validar_seguridad(self) -> "Settings":
        """Impide arrancar en producción con secretos débiles o cookies inseguras."""
        if self.ENV not in ("dev", "test"):
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY in WEAK_SECRET_KEYS:
                raise ValueError(
                    "SECRET_KEY debe tener al menos 32 caracteres y no ser un valor de ejemplo"
                )
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE debe ser true cuando ENV no es dev/test")
        return self


settings = Settings()
