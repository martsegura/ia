"""Configuración central de SaluDuoc.

Todos los valores se pueden sobrescribir con variables de entorno o con el
archivo .env (ver .env.example).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
