"""Tests de integración de vitales, triage y cola."""

from uuid import uuid4

from app.models.establishment import Establishment
from tests.conftest import PASSWORD


def create_establishment(db, nombre="CESFAM de Prueba") -> Establishment:
    establishment = Establishment(
        codigo=f"TEST-{uuid4().hex[:8]}",
        nombre=nombre,
        tipo="Centro de Salud Familiar (CESFAM)",
        direccion="Calle Prueba 123",
        comuna="Santiago",
        region="Metropolitana",
        lat=-33.45,
        lng=-70.66,
        tiene_urgencia=True,
        servicios=[],
        sede_duoc="Sede Alameda",
        fuente="test",
        is_active=True,
    )
    db.add(establishment)
    db.commit()
    db.refresh(establishment)
    return establishment


def base_payload(establishment_id=None):
    return {
        "heart_rate_bpm": 78,
        "systolic_mmhg": 118,
        "diastolic_mmhg": 76,
        "spo2_pct": 97,
        "sleep_quality_score": 82,
        "sleep_hours": 7.5,
        "symptoms": [],
        "pain_scale": 0,
        "establishment_id": establishment_id,
    }


def test_manual_vitals_creates_assessment_and_queue(client, make_user, db):
    patient = make_user(full_name="Paciente Vitales")
    establishment = create_establishment(db)
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})

    response = client.post(
        "/api/v1/vitals",
        json=base_payload(str(establishment.id)),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["category"] == "C5"
    assert body["color"] == "verde"
    assert body["queue"] is not None
    assert body["queue"]["position"] == 1
    assert body["queue"]["establishment_name"] == establishment.nombre

    latest = client.get("/api/v1/triage/me/latest")
    assert latest.status_code == 200
    assert latest.json()["assessment"]["id"] == body["id"]

    mine = client.get("/api/v1/queue/me")
    assert mine.status_code == 200
    assert mine.json()["category"] == "C5"

    history = client.get("/api/v1/vitals/me")
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_spo2_critical_creates_c1(client, make_user, db):
    patient = make_user(full_name="Paciente Crítico")
    establishment = create_establishment(db)
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})

    payload = base_payload(str(establishment.id))
    payload["spo2_pct"] = 84
    response = client.post("/api/v1/vitals", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "C1"
    assert body["color"] == "rojo"
    assert body["queue"]["priority"] == 1


def test_upload_watch_json(client, make_user):
    patient = make_user(full_name="Paciente Reloj")
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})
    payload = {
        "device": "SmartWatch Demo",
        "records": [
            {
                "timestamp": "2026-10-24T08:00:00-03:00",
                "heart_rate_bpm": 78,
                "blood_pressure": {"systolic": 118, "diastolic": 76},
                "oxygen_saturation_pct": 97,
                "sleep_quality": {"score": 82, "hours": 7.5},
            }
        ],
    }
    response = client.post("/api/v1/vitals/upload", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["category"] == "C5"


def test_empty_vitals_are_rejected(client, make_user):
    patient = make_user()
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})
    response = client.post(
        "/api/v1/vitals",
        json={"symptoms": ["Mareo"], "pain_scale": 2},
    )
    assert response.status_code == 422


def test_systolic_must_exceed_diastolic(client, make_user):
    patient = make_user()
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})
    payload = base_payload()
    payload["systolic_mmhg"] = 70
    payload["diastolic_mmhg"] = 90
    response = client.post("/api/v1/vitals", json=payload)
    assert response.status_code == 422


def test_doctor_sees_and_moves_queue(client, make_user, db):
    patient = make_user(full_name="Paciente Cola")
    establishment = create_establishment(db, nombre="CESFAM Cola")
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})
    assessment = client.post("/api/v1/vitals", json=base_payload(str(establishment.id)))
    assert assessment.status_code == 201
    queue_id = assessment.json()["queue"]["id"]

    doctor = make_user(role="doctor", full_name="Dr. Cola")
    doctor.doctor_profile.establecimiento_id = establishment.id
    db.add(doctor)
    db.commit()

    client.cookies.clear()
    client.post("/api/v1/auth/login", json={"email": doctor.email, "password": PASSWORD})
    queue = client.get("/api/v1/queue")
    assert queue.status_code == 200
    assert any(item["id"] == queue_id for item in queue.json())

    called = client.post(f"/api/v1/queue/{queue_id}/status", json={"status": "called"})
    assert called.status_code == 200, called.text
    assert called.json()["status"] == "called"

    in_attention = client.post(
        f"/api/v1/queue/{queue_id}/status", json={"status": "in_attention"}
    )
    assert in_attention.status_code == 200
    attended = client.post(
        f"/api/v1/queue/{queue_id}/status", json={"status": "attended"}
    )
    assert attended.status_code == 200
    assert attended.json()["status"] == "attended"


def test_doctor_cannot_move_other_establishment(client, make_user, db):
    patient = make_user()
    establishment = create_establishment(db, nombre="CESFAM Ajeno")
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})
    queue_id = client.post(
        "/api/v1/vitals", json=base_payload(str(establishment.id))
    ).json()["queue"]["id"]

    doctor = make_user(role="doctor")
    other = create_establishment(db, nombre="CESFAM Propio")
    doctor.doctor_profile.establecimiento_id = other.id
    db.add(doctor)
    db.commit()

    client.cookies.clear()
    client.post("/api/v1/auth/login", json={"email": doctor.email, "password": PASSWORD})
    response = client.post(f"/api/v1/queue/{queue_id}/status", json={"status": "called"})
    assert response.status_code == 403


def test_patient_cannot_access_doctor_queue(client, make_user):
    patient = make_user()
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})
    assert client.get("/api/v1/queue").status_code == 403


def test_establishments_sorted_by_distance(client, make_user, db):
    far = Establishment(
        codigo=f"FAR-{uuid4().hex[:8]}",
        nombre="Lejano Test",
        tipo="Hospital",
        lat=-34.0,
        lng=-71.0,
        tiene_urgencia=True,
        servicios=[],
        is_active=True,
        fuente="test",
    )
    near = Establishment(
        codigo=f"NEAR-{uuid4().hex[:8]}",
        nombre="Cercano Test",
        tipo="SAPU",
        lat=-33.45,
        lng=-70.66,
        tiene_urgencia=True,
        servicios=[],
        is_active=True,
        fuente="test",
    )
    db.add_all([far, near])
    db.commit()

    patient = make_user()
    client.post("/api/v1/auth/login", json={"email": patient.email, "password": PASSWORD})
    response = client.get("/api/v1/establishments?lat=-33.45&lng=-70.66")
    assert response.status_code == 200
    by_name = {item["nombre"]: item for item in response.json()}
    assert by_name["Cercano Test"]["distance_km"] < by_name["Lejano Test"]["distance_km"]
