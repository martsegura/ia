#!/usr/bin/env python3
"""Carga idempotente de datos iniciales de SaluDuoc.

Uso:
    python scripts/seed.py          # establecimientos + rangos
    python scripts/seed.py --demo   # además crea las cuentas demo
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, update  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    DoctorProfile,
    Establishment,
    NormalRange,
    PatientProfile,
    User,
    UserRole,
)

DATA_DIR = ROOT / "data" / "seed"
DEMO_PASSWORD = "Demo123!"


def load_json(name: str) -> list[dict]:
    path = DATA_DIR / name
    if not path.exists():
        print(f"[aviso] No existe {path}; se omite")
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def seed_establishments(db) -> int:
    count = 0
    items = load_json("establishments.json")
    managed_codes = [item["codigo"] for item in items]
    for item in items:
        existing = db.scalar(select(Establishment).where(Establishment.codigo == item["codigo"]))
        if existing is None:
            existing = Establishment(codigo=item["codigo"])
            db.add(existing)
            count += 1
        existing.nombre = item["nombre"]
        existing.tipo = item["tipo"]
        existing.direccion = item.get("direccion") or None
        existing.comuna = item.get("comuna") or None
        existing.region = item.get("region") or None
        existing.lat = item.get("lat")
        existing.lng = item.get("lng")
        existing.telefono = item.get("telefono") or None
        existing.tiene_urgencia = bool(item.get("tiene_urgencia"))
        existing.servicios = item.get("servicios") or []
        existing.sede_duoc = item.get("sede_duoc")
        existing.fuente = item.get("fuente")
        existing.fecha_snapshot = (
            date.fromisoformat(item["fecha_snapshot"]) if item.get("fecha_snapshot") else None
        )
        existing.is_active = True

    # Desactiva establecimientos DEIS que ya no pertenecen al snapshot actual.
    if managed_codes:
        db.execute(
            update(Establishment)
            .where(
                Establishment.fuente.like("DEIS MINSAL%"),
                ~Establishment.codigo.in_(managed_codes),
            )
            .values(is_active=False)
        )
    return count


def seed_normal_ranges(db) -> int:
    count = 0
    for item in load_json("normal_ranges.json"):
        existing = db.scalar(
            select(NormalRange).where(
                NormalRange.metric == item["metric"],
                NormalRange.version == item.get("version", "v1"),
            )
        )
        if existing is None:
            existing = NormalRange(
                metric=item["metric"], version=item.get("version", "v1")
            )
            db.add(existing)
            count += 1
        existing.label = item["label"]
        existing.unit = item.get("unit")
        for field in (
            "normal_min",
            "normal_max",
            "mild_low",
            "mild_high",
            "moderate_low",
            "moderate_high",
            "critical_low",
            "critical_high",
        ):
            setattr(existing, field, item.get(field))
        existing.is_informational = bool(item.get("is_informational"))
        existing.fuente = item.get("fuente")
        existing.is_active = True

    return count


def get_or_create_user(db, email: str, full_name: str, role: UserRole) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        db.flush()
    return user


def seed_users(db) -> None:
    patient = get_or_create_user(db, "paciente@demo.cl", "Paciente Demo", UserRole.PATIENT)
    if patient.patient_profile is None:
        patient.patient_profile = PatientProfile(
            birth_date=date(1995, 4, 12),
            sexo="F",
            peso_kg=64.0,
            talla_cm=165.0,
            comorbilidades=[],
            medicamentos=[],
            es_embarazada=False,
            contacto_emergencia="Contacto Demo +56 9 1234 5678",
        )

    doctor = get_or_create_user(
        db, "medico@demo.cl", "Dra. Valentina Soto", UserRole.DOCTOR
    )
    establishment = db.scalar(
        select(Establishment)
        .where(
            Establishment.sede_duoc == "Sede Alameda",
            Establishment.tiene_urgencia.is_(True),
        )
        .order_by(Establishment.nombre)
        .limit(1)
    )
    if establishment is None:
        establishment = db.scalar(select(Establishment).order_by(Establishment.nombre).limit(1))
    if doctor.doctor_profile is None:
        doctor.doctor_profile = DoctorProfile(especialidad="Medicina de Urgencia")
    if establishment is not None:
        doctor.doctor_profile.establecimiento_id = establishment.id

    get_or_create_user(db, "admin@demo.cl", "Administrador SaluDuoc", UserRole.ADMIN)


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga los datos iniciales de SaluDuoc")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Crea las cuentas demo (solo permitido en dev/test)",
    )
    args = parser.parse_args()

    if args.demo and settings.ENV not in ("dev", "test"):
        raise SystemExit(
            "ERROR: las cuentas demo con contraseña fija solo se permiten con ENV=dev o ENV=test"
        )

    with SessionLocal() as db:
        new_establishments = seed_establishments(db)
        db.flush()
        new_ranges = seed_normal_ranges(db)
        db.flush()
        if args.demo:
            seed_users(db)
        db.commit()

        total_establishments = (
            db.query(Establishment).filter(Establishment.is_active.is_(True)).count()
        )
        total_ranges = db.query(NormalRange).count()
        total_users = db.query(User).count()

    print("Seed SaluDuoc completado")
    print(f"  Establecimientos: {total_establishments} ({new_establishments} nuevos)")
    print(f"  Rangos normales:  {total_ranges} ({new_ranges} nuevos)")
    print(f"  Usuarios:         {total_users}")
    if args.demo:
        print("\nCuentas demo (password Demo123!):")
        print("  paciente@demo.cl | medico@demo.cl | admin@demo.cl")


if __name__ == "__main__":
    main()
