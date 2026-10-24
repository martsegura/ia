"""Crea registros de vitales, evalúa el triage y encola al paciente."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.establishment import Establishment
from app.models.normal_range import NormalRange
from app.models.queue_entry import QueueEntry
from app.models.symptom_report import SymptomReport
from app.models.triage_assessment import TriageAssessment
from app.models.user import User
from app.models.vital_record import VitalRecord
from app.schemas.vitals import AssessmentOut, QueueEntryOut, VitalOut
from app.services import queue_service
from app.services.triage import assess, calculate_age


def get_ranges(db: Session) -> dict[str, NormalRange]:
    ranges = db.scalars(
        select(NormalRange).where(NormalRange.is_active.is_(True)).order_by(NormalRange.metric)
    ).all()
    return {item.metric: item for item in ranges}


def evaluate_and_queue(
    db: Session,
    *,
    patient: User,
    vital: VitalRecord,
    symptom: SymptomReport,
    establishment_id: UUID | None,
) -> TriageAssessment:
    ranges = get_ranges(db)
    age = calculate_age(patient.patient_profile.birth_date if patient.patient_profile else None)
    comorbidities = (
        list(patient.patient_profile.comorbilidades or [])
        if patient.patient_profile
        else []
    )

    result = assess(
        heart_rate_bpm=vital.heart_rate_bpm,
        systolic_mmhg=vital.systolic_mmhg,
        diastolic_mmhg=vital.diastolic_mmhg,
        spo2_pct=vital.spo2_pct,
        symptoms=list(symptom.symptoms or []),
        pain_scale=symptom.pain_scale,
        age=age,
        comorbidities=comorbidities,
        ranges=ranges,
    )

    establishment = None
    if establishment_id is not None:
        establishment = db.get(Establishment, establishment_id)
        if establishment is None or not establishment.is_active:
            raise ValueError("El establecimiento seleccionado no existe o está inactivo")

    assessment = TriageAssessment(
        patient_id=patient.id,
        vital_record_id=vital.id,
        symptom_report_id=symptom.id,
        establishment_id=establishment.id if establishment else None,
        category=result.category,
        color=result.color,
        score=result.score,
        triggered_rules=result.triggered_rules,
        rationale=result.rationale,
        algorithm_version=result.algorithm_version,
        ranges_version=result.ranges_version,
    )
    db.add(assessment)
    db.flush()

    if establishment is not None:
        queue_service.create_entry(db, assessment, establishment.id)

    db.commit()
    db.refresh(assessment)
    return assessment


def _queue_out(db: Session, assessment: TriageAssessment) -> QueueEntryOut | None:
    entry = db.scalar(
        select(QueueEntry).where(QueueEntry.assessment_id == assessment.id)
    )
    if entry is None:
        return None
    return queue_service.serialize_entry(db, entry)


def assessment_out(db: Session, assessment: TriageAssessment) -> AssessmentOut:
    return AssessmentOut(
        id=assessment.id,
        category=assessment.category,
        color=assessment.color,
        score=assessment.score,
        triggered_rules=assessment.triggered_rules or [],
        rationale=assessment.rationale,
        algorithm_version=assessment.algorithm_version,
        ranges_version=assessment.ranges_version,
        created_at=assessment.created_at,
        queue=_queue_out(db, assessment),
    )


def latest_assessment(db: Session, patient: User) -> TriageAssessment | None:
    return db.scalar(
        select(TriageAssessment)
        .where(TriageAssessment.patient_id == patient.id)
        .order_by(TriageAssessment.created_at.desc())
        .limit(1)
    )


def vitals_history(db: Session, patient: User, limit: int = 20) -> list[VitalOut]:
    records = db.scalars(
        select(VitalRecord)
        .where(VitalRecord.patient_id == patient.id)
        .order_by(VitalRecord.recorded_at.desc())
        .limit(limit)
    ).all()
    return [VitalOut.model_validate(record) for record in records]


def build_vital(
    *,
    patient_id: UUID,
    source: str,
    recorded_at: datetime | None,
    device: str | None,
    heart_rate_bpm: int | None,
    systolic_mmhg: int | None,
    diastolic_mmhg: int | None,
    spo2_pct: int | None,
    sleep_quality_score: int | None,
    sleep_hours: float | None,
    raw_payload: dict | None,
) -> VitalRecord:
    return VitalRecord(
        patient_id=patient_id,
        source=source,
        recorded_at=recorded_at or datetime.now(timezone.utc),
        device=device,
        heart_rate_bpm=heart_rate_bpm,
        systolic_mmhg=systolic_mmhg,
        diastolic_mmhg=diastolic_mmhg,
        spo2_pct=spo2_pct,
        sleep_quality_score=sleep_quality_score,
        sleep_hours=sleep_hours,
        raw_payload=raw_payload,
    )
