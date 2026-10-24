"""Serialización de usuarios y sus perfiles."""

from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserOut


def profile_dict(user: User) -> dict | None:
    if user.role == UserRole.PATIENT and user.patient_profile is not None:
        profile = user.patient_profile
        return {
            "rut": profile.rut,
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
            "sexo": profile.sexo,
            "peso_kg": profile.peso_kg,
            "talla_cm": profile.talla_cm,
            "comorbilidades": profile.comorbilidades or [],
            "medicamentos": profile.medicamentos or [],
            "es_embarazada": profile.es_embarazada,
            "contacto_emergencia": profile.contacto_emergencia,
        }
    if user.role == UserRole.DOCTOR and user.doctor_profile is not None:
        profile = user.doctor_profile
        return {
            "especialidad": profile.especialidad,
            "establecimiento_id": (
                str(profile.establecimiento_id) if profile.establecimiento_id else None
            ),
        }
    return None


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        profile=profile_dict(user),
    )
