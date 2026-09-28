from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import NotFoundError, register_exception_handlers


def _app_with_error_route() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise NotFoundError("Lot not found", {"lot_id": "abc"})

    return app


def test_app_error_envelope():
    with TestClient(_app_with_error_route()) as client:
        r = client.get("/boom")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "Lot not found"
    assert body["error"]["details"] == {"lot_id": "abc"}


def test_unknown_route_returns_envelope():
    app = FastAPI()
    register_exception_handlers(app)
    with TestClient(app) as client:
        r = client.get("/nope")
    assert r.status_code == 404
    assert "error" in r.json()
