"""Tests de las pantallas por rol y sus redirecciones."""

from tests.conftest import PASSWORD


def _login(client, user):
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get("/paciente", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_authenticated_user_is_redirected_away_from_login(client, make_user):
    user = make_user()
    _login(client, user)
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/paciente"


def test_patient_page_renders_profile(client, make_user):
    user = make_user(full_name="Ana Paciente")
    _login(client, user)
    response = client.get("/paciente")
    assert response.status_code == 200
    assert "Hola, Ana" in response.text
    assert "Mi perfil" in response.text
    assert "Próximos pasos" in response.text


def test_patient_cannot_open_admin_or_doctor_pages(client, make_user):
    user = make_user()
    _login(client, user)

    admin = client.get("/admin", follow_redirects=False)
    assert admin.status_code == 303
    assert admin.headers["location"] == "/paciente"

    doctor = client.get("/medico", follow_redirects=False)
    assert doctor.status_code == 303
    assert doctor.headers["location"] == "/paciente"


def test_doctor_page_renders_queue_and_establishment(client, make_user):
    doctor = make_user(role="doctor", full_name="Dra. Valentina")
    _login(client, doctor)
    response = client.get("/medico")
    assert response.status_code == 200
    assert "Dra. Valentina" in response.text
    assert "Cola de espera" in response.text
    assert "Mi establecimiento" in response.text

    denied = client.get("/paciente", follow_redirects=False)
    assert denied.status_code == 303
    assert denied.headers["location"] == "/medico"


def test_admin_page_renders_stats_and_tables(client, make_user):
    admin = make_user(role="admin", full_name="Admin Demo")
    _login(client, admin)
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Panel de administración" in response.text
    assert "Establecimientos" in response.text
    assert "Usuarios recientes" in response.text

    denied = client.get("/medico", follow_redirects=False)
    assert denied.status_code == 303
    assert denied.headers["location"] == "/admin"


def test_dashboard_redirects_to_role_home(client, make_user):
    doctor = make_user(role="doctor")
    _login(client, doctor)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/medico"
