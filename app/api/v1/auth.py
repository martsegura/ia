"""Endpoints de registro, login, logout y sesión actual.

project-id: 29324fd4-f130-400e-9542-f3dcd52fb814
prd-id: 9ab3b43b-fde8-4977-b3dc-a9e57b27de7b
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.profile import PatientProfile
from app.models.user import User
from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest
from app.schemas.user import UserOut
from app.services.rate_limit import login_limiter
from app.services.user_service import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    """Registra un paciente nuevo."""
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.PATIENT,
        full_name=payload.full_name,
    )
    user.patient_profile = PatientProfile()
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo",
        ) from None
    db.refresh(user)
    return user_out(user)


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Valida credenciales y deja el JWT en una cookie HttpOnly."""
    client_ip = request.client.host if request.client else "desconocido"
    email = payload.email.lower().strip()
    rate_key = f"{client_ip}:{email}"

    if login_limiter.is_blocked(rate_key, settings.RATE_LIMIT_LOGIN):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Intenta nuevamente en un minuto",
            headers={"Retry-After": "60"},
        )

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        login_limiter.register_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    if not user.is_active:
        login_limiter.register_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada",
        )

    login_limiter.reset(rate_key)
    token = create_access_token(user.id, user.role.value, user.token_version)
    response = JSONResponse(content=user_out(user).model_dump(mode="json"))
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.TOKEN_TTL_MINUTES * 60,
        path="/",
    )
    return response


@router.post("/logout", response_model=MessageResponse)
def logout(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> JSONResponse:
    """Invalida la sesión actual y elimina la cookie."""
    if current_user is not None:
        current_user.token_version += 1
        db.add(current_user)
        db.commit()

    response = JSONResponse(content={"message": "Sesión cerrada"})
    response.delete_cookie(settings.COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Devuelve el usuario autenticado."""
    return user_out(current_user)
