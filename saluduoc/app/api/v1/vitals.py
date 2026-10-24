"""Registro de signos vitales desde formulario o JSON de wearable."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.symptom_report import SymptomReport
from app.models.user import User
from app.models.vital_record import VitalRecord
from app.schemas.vitals import AssessmentOut, VitalIn, VitalOut, WatchUploadIn
from app.services import consultation
from app.services.triage import SUPPORTED_SYMPTOMS

router = APIRouter(prefix="/vitals", tags=["vitals"])


@router.get("/symptoms", response_model=list[str])
def symptoms_catalog() -> list[str]:
    return SUPPORTED_SYMPTOMS


@router.get("/me", response_model=list[VitalOut])
def my_vitals(
    limit: int = 20,
    current_user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
) -> list[VitalOut]:
    return consultation.vitals_history(db, current_user, limit=min(max(limit, 1), 100))


@router.post("", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_manual(
    payload: VitalIn,
    current_user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
) -> AssessmentOut:
    """Registra signos vitales y síntomas, calcula el triage y encola."""
    vital = consultation.build_vital(
        patient_id=current_user.id,
        source="manual",
        recorded_at=payload.recorded_at,
        device=payload.device,
        heart_rate_bpm=payload.heart_rate_bpm,
        systolic_mmhg=payload.systolic_mmhg,
        diastolic_mmhg=payload.diastolic_mmhg,
        spo2_pct=payload.spo2_pct,
        sleep_quality_score=payload.sleep_quality_score,
        sleep_hours=payload.sleep_hours,
        raw_payload=payload.model_dump(mode="json"),
    )
    symptom = SymptomReport(
        patient_id=current_user.id,
        symptoms=payload.symptoms,
        pain_scale=payload.pain_scale,
        onset=payload.onset,
        notes=payload.notes,
    )
    db.add(vital)
    db.flush()
    symptom.vital_record_id = vital.id
    db.add(symptom)
    db.flush()

    try:
        assessment = consultation.evaluate_and_queue(
            db,
            patient=current_user,
            vital=vital,
            symptom=symptom,
            establishment_id=payload.establishment_id,
        )
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from None
    return consultation.assessment_out(db, assessment)


@router.post("/upload", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def upload_wearable(
    payload: WatchUploadIn,
    current_user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
) -> AssessmentOut:
    """Carga un JSON de reloj inteligente y evalúa el registro más reciente."""
    records: list[VitalRecord] = []
    for item in payload.records:
        pressure = item.blood_pressure or {}
        sleep = item.sleep_quality or {}
        vital = consultation.build_vital(
            patient_id=current_user.id,
            source="upload",
            recorded_at=item.timestamp,
            device=payload.device,
            heart_rate_bpm=item.heart_rate_bpm,
            systolic_mmhg=pressure.get("systolic"),
            diastolic_mmhg=pressure.get("diastolic"),
            spo2_pct=item.oxygen_saturation_pct,
            sleep_quality_score=sleep.get("score"),
            sleep_hours=sleep.get("hours"),
            raw_payload=item.model_dump(mode="json"),
        )
        db.add(vital)
        records.append(vital)

    db.flush()
    latest = max(records, key=lambda record: record.recorded_at)
    symptom = SymptomReport(patient_id=current_user.id, symptoms=[])
    symptom.vital_record_id = latest.id
    db.add(symptom)
    db.flush()

    try:
        assessment = consultation.evaluate_and_queue(
            db,
            patient=current_user,
            vital=latest,
            symptom=symptom,
            establishment_id=payload.establishment_id,
        )
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from None
    return consultation.assessment_out(db, assessment)
