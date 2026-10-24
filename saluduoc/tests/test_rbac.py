"""Tests de control de acceso basado en roles."""

from tests.conftest import PASSWORD


def test_unauthenticated_access_is_rejected(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get("/api/v1/users").status_code == 401


def test_patient_cannot_access_admin_endpoint(client, make_user):
    user = make_user()
    client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    assert client.get("/api/v1/users").status_code == 403


def test_doctor_cannot_access_admin_endpoint(client, make_user):
    doctor = make_user(role="doctor")
    client.post("/api/v1/auth/login", json={"email": doctor.email, "password": PASSWORD})
    assert client.get("/api/v1/users").status_code == 403


def test_admin_has_access(client, make_user):
    admin = make_user(role="admin")
    client.post("/api/v1/auth/login", json={"email": admin.email, "password": PASSWORD})
    assert client.get("/api/v1/users").status_code == 200
