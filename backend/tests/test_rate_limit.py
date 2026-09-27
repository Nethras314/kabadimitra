from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rate_limit import RateLimitMiddleware


def test_rate_limit_returns_429_after_limit():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limit=2, window_seconds=60)

    @app.get("/x")
    async def x():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/x").status_code == 200
    assert client.get("/x").status_code == 200
    assert client.get("/x").status_code == 429


def test_exempt_paths_not_rate_limited():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limit=1, window_seconds=60, exempt_paths=["/health"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
