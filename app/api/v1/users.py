"""Endpoints de perfil y administración de usuarios."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.profile import DoctorProfile
from app.models.user import User
from app.schemas.user import ProfileUpdate, UserListResponse, UserOut
from app.services.user_service import user_out

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return user_out(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    """Actualiza el nombre y los datos del perfil según el rol."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    if current_user.role == UserRole.PATIENT and current_user.patient_profile is not None:
        profile = current_user.patient_profile
        for field in (
            "rut",
            "birth_date",
            "sexo",
            "peso_kg",
            "talla_cm",
            "comorbilidades",
            "medicamentos",
            "es_embarazada",
            "contacto_emergencia",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(profile, field, value)

    if current_user.role == UserRole.DOCTOR:
        if current_user.doctor_profile is None:
            current_user.doctor_profile = DoctorProfile()
        if payload.especialidad is not None:
            current_user.doctor_profile.especialidad = payload.especialidad

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return user_out(current_user)


@router.get("", response_model=UserListResponse)
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """Lista paginada de usuarios. Solo administradores."""
    total = db.scalar(select(func.count()).select_from(User)) or 0
    users = db.scalars(
        select(User)
        .options(selectinload(User.patient_profile), selectinload(User.doctor_profile))
        .order_by(User.created_at.desc(), User.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return UserListResponse(
        items=[user_out(user, include_profile=False) for user in users], total=total
    )
