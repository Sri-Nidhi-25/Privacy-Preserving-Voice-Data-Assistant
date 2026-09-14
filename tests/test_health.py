"""
tests/test_health.py - Tests for liveness, readiness, and degraded health states.
"""
from fastapi.testclient import TestClient


def test_health_live(client: TestClient):
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}


def test_health_ready_structure(client: TestClient):
    res = client.get("/health/ready")
    assert res.status_code in (200, 503)
    data = res.json()
    assert "status" in data
    assert "components" in data
    assert "whisper" in data["components"]
    assert "crm" in data["components"]


def test_health_backwards_compat(client: TestClient):
    res = client.get("/health")
    assert res.status_code in (200, 503)
    assert "status" in res.json()


def test_health_ready_degraded(client: TestClient, monkeypatch):
    # Simulate missing data file to test non-ready status
    from app.routers import health
    monkeypatch.setattr(health, "_check_whisper", lambda: "unavailable")

    res = client.get("/health/ready")
    assert res.status_code == 503
    assert res.json()["status"] == "unavailable"
