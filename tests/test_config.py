import pytest

from app.config import database_url_from_env, inspect_database_url
from tools.validate_production_config import _validate_database_url


def _clear_database_env(monkeypatch):
    for name in (
        "DATABASE_URL",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)


def test_split_database_env_supports_special_password(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "db.example.test")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "censo_px")
    monkeypatch.setenv("DB_USER", "usuario")
    monkeypatch.setenv("DB_PASSWORD", "pass/with?#,@chars")

    database_url = database_url_from_env()

    assert database_url.host == "db.example.test"
    assert database_url.database == "censo_px"
    assert database_url.username == "usuario"
    assert database_url.password == "pass/with?#,@chars"


def test_validator_preserves_split_database_url_password(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "db.example.test")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "censo_px")
    monkeypatch.setenv("DB_USER", "usuario")
    monkeypatch.setenv("DB_PASSWORD", "pass/with?#,@chars")

    database_url = _validate_database_url()

    assert database_url.password == "pass/with?#,@chars"


def test_database_url_rejects_unencoded_special_chars(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://usuario:pass/with?#,@chars@db.example.test:5432/censo_px",
    )

    with pytest.raises(RuntimeError, match="caracteres especiales sin codificar"):
        database_url_from_env()


def test_database_url_accepts_encoded_special_chars(monkeypatch):
    _clear_database_env(monkeypatch)
    database_url = "postgresql://usuario:pass%2Fwith%3F%23%2C%40chars@db.example.test:5432/censo_px"
    monkeypatch.setenv("DATABASE_URL", database_url)

    assert database_url_from_env() == database_url
    info = inspect_database_url(database_url)
    assert info.password_set is True
