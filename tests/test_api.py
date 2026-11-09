"""End-to-end HTTP tests with the real FastAPI app and fake wallet/ABC."""
import pytest
from fastapi.testclient import TestClient

from app.container import get_payment_service, get_settings
from app.main import app

H = {"X-API-Key": "shop-secret"}


@pytest.fixture
def client(service):
    get_settings.cache_clear()
    app.dependency_overrides[get_payment_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_requires_api_key(client):
    r = client.post("/payments", json={"client_id": "1", "amount": "0.1"}, headers={"X-API-Key": "bad"})
    assert r.status_code == 401


def test_create_and_get_payment(client):
    r = client.post("/payments", json={"client_id": "1", "amount": "0.5", "description": "Order 1"}, headers=H)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "SUCCESS"
    assert body["caller_service"] == "shop-service"

    r2 = client.get(f"/payments/{body['id']}", headers=H)
    assert r2.status_code == 200 and r2.json()["id"] == body["id"]


def test_declined_payment_returns_402(client):
    r = client.post("/payments", json={"client_id": "2", "amount": "1"}, headers=H)
    assert r.status_code == 402
    assert r.json()["failure_reason"] == "INSUFFICIENT_FUNDS"


def test_validation(client):
    r = client.post("/payments", json={"client_id": "1", "amount": "-1"}, headers=H)
    assert r.status_code == 422


def test_unknown_payment(client):
    assert client.get("/payments/nope", headers=H).status_code == 404


def test_list(client):
    client.post("/payments", json={"client_id": "1", "amount": "0.1"}, headers=H)
    assert len(client.get("/payments", headers=H).json()) == 1
