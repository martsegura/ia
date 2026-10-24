"""Tests de la configuración de seguridad por entorno."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

STRONG_SECRET = "x" * 48


def test_prod_rejects_weak_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENV="prod", SECRET_KEY="weak", COOKIE_SECURE=True)


def test_prod_requires_secure_cookie():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENV="prod", SECRET_KEY=STRONG_SECRET, COOKIE_SECURE=False)


def test_prod_accepts_strong_config():
    settings = Settings(_env_file=None, ENV="prod", SECRET_KEY=STRONG_SECRET, COOKIE_SECURE=True)
    assert settings.ENV == "prod"
    assert settings.COOKIE_SECURE is True


def test_dev_allows_defaults():
    settings = Settings(_env_file=None, ENV="dev")
    assert settings.ENV == "dev"
