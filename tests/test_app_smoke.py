import importlib
import sys

from fastapi.testclient import TestClient


class DummySession:
    def execute(self, statement):
        return None


def _import_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test_db")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("FERNET_KEY", "wLmCPbBPxgsk2uyZOHIto5xO4bB1UfoajkVXqmKOwyQ=")
    monkeypatch.setenv("FRONTEND_URL", "https://frontend.example.test")

    for module_name in list(sys.modules):
        if module_name == "app.main" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)

    return importlib.import_module("app.main")


def test_healthcheck_uses_configured_app(monkeypatch):
    main = _import_app(monkeypatch)

    def override_get_db():
        yield DummySession()

    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        client = TestClient(main.app)
        response = client.get("/health")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_cors_allows_configured_frontend(monkeypatch):
    main = _import_app(monkeypatch)
    client = TestClient(main.app)

    response = client.options(
        "/health",
        headers={
            "Origin": "https://frontend.example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://frontend.example.test"


def test_cors_rejects_unconfigured_frontend(monkeypatch):
    main = _import_app(monkeypatch)
    client = TestClient(main.app)

    response = client.options(
        "/health",
        headers={
            "Origin": "https://otro.example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
