"""Dependencias compartidas: sesión, usuario actual y control de roles."""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User


def load_user_from_token(request: Request, db: Session) -> User | None:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    if int(payload.get("ver", 0)) != user.token_version:
        return None
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Lee el JWT desde la cookie HttpOnly y devuelve el usuario activo."""
    user = load_user_from_token(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado o sesión expirada",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Igual que get_current_user, pero devuelve None si no hay sesión válida."""
    return load_user_from_token(request, db)


def require_roles(*roles: UserRole):
    """Fábrica de dependencias que exige uno de los roles indicados."""
    allowed = set(roles)

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )
        return user

    return checker
