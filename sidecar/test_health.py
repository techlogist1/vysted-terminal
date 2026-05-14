"""Phase 0 placeholder tests: the sidecar must expose a healthy /health endpoint."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_payload_shape() -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "vysted-sidecar"
