"""Utilidades de seguridad: hash de contraseñas y tokens JWT."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Devuelve el hash Argon2 de una contraseña."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash."""
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:  # hash inválido o corrupto
        return False


def create_access_token(subject: UUID | str, role: str, token_version: int = 0) -> str:
    """Crea un JWT con id de usuario, rol y versión de sesión."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "role": role,
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodifica un JWT exigiendo exp y sub."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
