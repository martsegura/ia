"""Configuración de pytest para SaluDuoc.

Los tests corren contra PostgreSQL (no SQLite) para cubrir JSON, UUID y
constraints reales. Levanta el servicio db-test con:
    docker compose up -d db-test
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://saluduoc:saluduoc@localhost:5433/saluduoc_test",
)
if "test" not in TEST_DATABASE_URL.lower():
    raise RuntimeError("TEST_DATABASE_URL debe apuntar a una base de datos de pruebas")

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import DoctorProfile, NormalRange, PatientProfile, User, UserRole  # noqa: E402
from app.services.rate_limit import login_limiter  # noqa: E402

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)

PASSWORD = "Demo123!"


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    data_file = Path(__file__).resolve().parents[1] / "data" / "seed" / "normal_ranges.json"
    items = json.loads(data_file.read_text(encoding="utf-8"))
    with TestingSessionLocal() as session:
        for item in items:
            session.add(
                NormalRange(
                    metric=item["metric"],
                    label=item["label"],
                    unit=item.get("unit"),
                    normal_min=item.get("normal_min"),
                    normal_max=item.get("normal_max"),
                    mild_low=item.get("mild_low"),
                    mild_high=item.get("mild_high"),
                    moderate_low=item.get("moderate_low"),
                    moderate_high=item.get("moderate_high"),
                    critical_low=item.get("critical_low"),
                    critical_high=item.get("critical_high"),
                    is_informational=bool(item.get("is_informational")),
                    version=item.get("version", "v1"),
                    fuente=item.get("fuente"),
                    is_active=True,
                )
            )
        session.commit()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Generator[None, None, None]:
    login_limiter.clear()
    yield
    login_limiter.clear()


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid4().hex[:8]}@example.cl"


@pytest.fixture()
def make_user(db: Session):
    def _make(
        email: str | None = None,
        role: UserRole | str = UserRole.PATIENT,
        password: str = PASSWORD,
        full_name: str = "Usuario de Prueba",
    ) -> User:
        role_value = role if isinstance(role, UserRole) else UserRole(role)
        user = User(
            email=email or unique_email(role_value.value),
            full_name=full_name,
            role=role_value,
            password_hash=hash_password(password),
        )
        if role_value == UserRole.PATIENT:
            user.patient_profile = PatientProfile()
        elif role_value == UserRole.DOCTOR:
            user.doctor_profile = DoctorProfile(especialidad="Medicina General")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def login(client: TestClient):
    def _login(email: str, password: str = PASSWORD):
        return client.post("/api/v1/auth/login", json={"email": email, "password": password})

    return _login
