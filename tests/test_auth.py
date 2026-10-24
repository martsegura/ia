"""Tests de registro, login, logout y sesión."""

from tests.conftest import PASSWORD, unique_email


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_creates_patient_with_profile(client):
    email = unique_email("paciente")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "  Ana   Pérez  "},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == email
    assert body["role"] == "patient"
    assert body["full_name"] == "Ana Pérez"
    assert body["profile"]["comorbilidades"] == []


def test_register_duplicate_email_returns_409(client):
    email = unique_email("dup")
    payload = {"email": email, "password": PASSWORD, "full_name": "Duplicado"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "existe" in response.json()["detail"].lower()


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email("weak"), "password": "sololetras", "full_name": "Débil"},
    )
    assert response.status_code == 422


def test_login_sets_httponly_cookie_and_me_works(client, make_user):
    user = make_user(full_name="Paciente Login")
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    assert "saluduoc_token" in response.cookies
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == user.email


def test_login_wrong_password_returns_401(client, make_user):
    user = make_user()
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Incorrecta1"}
    )
    assert response.status_code == 401


def test_logout_clears_session(client, make_user):
    user = make_user()
    client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_rate_limit(client, make_user):
    user = make_user()
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "MalaClave1"}
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "MalaClave1"}
    )
    assert blocked.status_code == 429


def test_me_without_cookie_returns_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401
