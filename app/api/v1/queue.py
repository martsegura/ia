"""Cola de espera visible para pacientes y médicos."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.queue_entry import QueueEntry
from app.models.user import User
from app.schemas.vitals import QueueEntryOut, QueueStatusIn
from app.services import queue_service

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=list[QueueEntryOut])
def get_queue(
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[QueueEntryOut]:
    establishment_id = None
    if current_user.role == UserRole.DOCTOR:
        profile = current_user.doctor_profile
        if profile is None or profile.establecimiento_id is None:
            return []
        establishment_id = profile.establecimiento_id
    return queue_service.list_queue(db, establishment_id)


@router.get("/me", response_model=QueueEntryOut | None)
def my_queue_entry(
    current_user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
) -> QueueEntryOut | None:
    entry = queue_service.entry_for_patient(db, current_user.id)
    return queue_service.serialize_entry(db, entry) if entry else None


@router.post("/{entry_id}/status", response_model=QueueEntryOut)
def change_status(
    entry_id: UUID,
    payload: QueueStatusIn,
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> QueueEntryOut:
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrada no encontrada")
    if current_user.role == UserRole.DOCTOR:
        profile = current_user.doctor_profile
        if profile is None or profile.establecimiento_id != entry.establishment_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta entrada pertenece a otro establecimiento",
            )
    try:
        updated = queue_service.update_status(db, entry, payload.status, current_user)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
    return queue_service.serialize_entry(db, updated)
