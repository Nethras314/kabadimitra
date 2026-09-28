from fastapi.testclient import TestClient

from app.foundation import app


def test_app_starts_and_serves_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "Kabadi Mitra API"}
