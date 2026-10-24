"""Tests del frontend base y de los estáticos."""

def test_index_uses_root_relative_static_paths(client):
    response = client.get("/")
    assert response.status_code == 200
    # Rutas relativas: evitan mixed content cuando hay un proxy HTTPS delante.
    assert 'href="/static/css/style.css' in response.text
    assert 'src="/static/js/app.js' in response.text
    assert "http://testserver/static" not in response.text


def test_static_css_is_served(client):
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "--primary" in response.text


def test_static_js_is_served(client):
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert "text/javascript" in response.headers["content-type"]
