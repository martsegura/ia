"""Consulta del resultado de triage."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.triage_assessment import TriageAssessment
from app.models.user import User
from app.schemas.vitals import AssessmentOut, LatestAssessmentOut
from app.services import consultation

router = APIRouter(prefix="/triage", tags=["triage"])


@router.get("/me/latest", response_model=LatestAssessmentOut)
def my_latest(
    current_user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
) -> LatestAssessmentOut:
    assessment = consultation.latest_assessment(db, current_user)
    return LatestAssessmentOut(
        assessment=consultation.assessment_out(db, assessment) if assessment else None
    )


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentOut:
    assessment = db.get(TriageAssessment, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evaluación no encontrada"
        )
    if current_user.role == UserRole.PATIENT and assessment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta evaluación",
        )
    return consultation.assessment_out(db, assessment)
