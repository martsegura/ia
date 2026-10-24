"""Cola de espera por establecimiento."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.queue_entry import QueueEntry
from app.models.triage_assessment import TriageAssessment
from app.models.user import User
from app.schemas.vitals import QueueEntryOut
from app.services.triage import PRIORITY

ACTIVE_STATUSES = ("waiting", "called", "in_attention")
ALLOWED_TRANSITIONS = {
    "waiting": {"called", "left"},
    "called": {"in_attention", "left"},
    "in_attention": {"attended", "left"},
    "attended": set(),
    "left": set(),
}


def _position(db: Session, entry: QueueEntry) -> int | None:
    if entry.status != "waiting":
        return None
    ahead = db.scalar(
        select(func.count())
        .select_from(QueueEntry)
        .where(
            QueueEntry.establishment_id == entry.establishment_id,
            QueueEntry.status == "waiting",
            (QueueEntry.priority < entry.priority)
            | (
                (QueueEntry.priority == entry.priority)
                & (QueueEntry.created_at < entry.created_at)
            ),
        )
    )
    return (ahead or 0) + 1

def _wait_minutes(entry: QueueEntry) -> int:
    now = datetime.now(timezone.utc)
    created = entry.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0, int((now - created).total_seconds() // 60))


def serialize_entry(db: Session, entry: QueueEntry) -> QueueEntryOut:
    assessment: TriageAssessment = entry.assessment
    vital = assessment.vital_record
    symptom = assessment.symptom_report
    patient = db.get(User, entry.patient_id)
    establishment = entry.establishment
    vitals = {
        "heart_rate_bpm": vital.heart_rate_bpm,
        "systolic_mmhg": vital.systolic_mmhg,
        "diastolic_mmhg": vital.diastolic_mmhg,
        "spo2_pct": vital.spo2_pct,
        "sleep_quality_score": vital.sleep_quality_score,
        "sleep_hours": vital.sleep_hours,
    }
    return QueueEntryOut(
        id=entry.id,
        assessment_id=entry.assessment_id,
        establishment_id=entry.establishment_id,
        patient_id=entry.patient_id,
        patient_name=patient.full_name if patient else "Paciente",
        establishment_name=establishment.nombre if establishment else "Establecimiento",
        category=entry.category,
        color=entry.color,
        priority=entry.priority,
        status=entry.status,
        position=_position(db, entry),
        wait_minutes=_wait_minutes(entry),
        created_at=entry.created_at,
        called_at=entry.called_at,
        attended_at=entry.attended_at,
        notes=entry.notes,
        symptoms=symptom.symptoms if symptom else [],
        vitals=vitals,
        rationale=assessment.rationale,
    )


def create_entry(
    db: Session, assessment: TriageAssessment, establishment_id: UUID
) -> QueueEntry:
    # Cierra solicitudes activas previas del mismo paciente.
    previous = db.scalars(
        select(QueueEntry).where(
            QueueEntry.patient_id == assessment.patient_id,
            QueueEntry.status.in_(ACTIVE_STATUSES),
        )
    ).all()
    for entry in previous:
        entry.status = "left"
        entry.notes = "Cerrada automáticamente por un nuevo registro"

    queue_entry = QueueEntry(
        assessment_id=assessment.id,
        establishment_id=establishment_id,
        patient_id=assessment.patient_id,
        category=assessment.category,
        color=assessment.color,
        priority=PRIORITY[assessment.category],
        status="waiting",
    )
    db.add(queue_entry)
    db.flush()
    return queue_entry


def list_queue(db: Session, establishment_id: UUID | None = None) -> list[QueueEntryOut]:
    query = select(QueueEntry).where(QueueEntry.status.in_(ACTIVE_STATUSES))
    if establishment_id is not None:
        query = query.where(QueueEntry.establishment_id == establishment_id)
    entries = db.scalars(
        query.order_by(QueueEntry.priority, QueueEntry.created_at)
    ).all()
    return [serialize_entry(db, entry) for entry in entries]


def entry_for_patient(db: Session, patient_id: UUID) -> QueueEntry | None:
    return db.scalar(
        select(QueueEntry)
        .where(
            QueueEntry.patient_id == patient_id,
            QueueEntry.status.in_(ACTIVE_STATUSES),
        )
        .order_by(QueueEntry.created_at.desc())
        .limit(1)
    )


def update_status(
    db: Session, entry: QueueEntry, new_status: str, doctor: User
) -> QueueEntry:
    if new_status not in ALLOWED_TRANSITIONS.get(entry.status, set()):
        raise ValueError(
            f"No se puede pasar de '{entry.status}' a '{new_status}'"
        )
    now = datetime.now(timezone.utc)
    entry.status = new_status
    if new_status == "called":
        entry.called_at = now
        entry.doctor_id = doctor.id
    elif new_status == "in_attention":
        entry.doctor_id = doctor.id
    elif new_status == "attended":
        entry.attended_at = now
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
