"""Tests de perfil, actualización y listado de usuarios."""

from tests.conftest import PASSWORD, unique_email


def test_get_and_update_patient_profile(client, make_user):
    user = make_user(full_name="Perfil Inicial")
    client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})

    response = client.patch(
        "/api/v1/users/me",
        json={
            "full_name": "Perfil Actualizado",
            "birth_date": "1990-05-20",
            "sexo": "F",
            "peso_kg": 70.5,
            "talla_cm": 168,
            "comorbilidades": ["hipertensión"],
            "medicamentos": ["losartán"],
            "contacto_emergencia": "+56 9 1111 2222",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Perfil Actualizado"
    assert body["profile"]["peso_kg"] == 70.5
    assert body["profile"]["comorbilidades"] == ["hipertensión"]
    assert body["profile"]["birth_date"] == "1990-05-20"


def test_patient_cannot_list_users(client, make_user):
    user = make_user()
    client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    assert client.get("/api/v1/users").status_code == 403


def test_admin_can_list_users(client, make_user):
    admin = make_user(role="admin")
    client.post("/api/v1/auth/login", json={"email": admin.email, "password": PASSWORD})
    response = client.get("/api/v1/users?limit=10")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert any(item["email"] == admin.email for item in body["items"])


def test_doctor_can_update_specialty(client, make_user):
    doctor = make_user(role="doctor")
    client.post("/api/v1/auth/login", json={"email": doctor.email, "password": PASSWORD})
    response = client.patch(
        "/api/v1/users/me",
        json={"especialidad": "Medicina de Urgencia", "full_name": "Dra. Prueba"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile"]["especialidad"] == "Medicina de Urgencia"
    assert body["full_name"] == "Dra. Prueba"


def test_new_patient_has_empty_profile(client):
    email = unique_email("nuevo")
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Nuevo Paciente"},
    )
    client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    me = client.get("/api/v1/users/me")
    assert me.status_code == 200
    assert me.json()["profile"]["rut"] is None
