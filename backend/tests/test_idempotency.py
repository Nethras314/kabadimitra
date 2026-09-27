import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import create_pool
from app.idempotency import IdempotencyMiddleware


def _make_app():
    @asynccontextmanager
    async def lifespan(app):
        pool = create_pool()
        await pool.open()
        app.state.pool = pool
        yield
        await pool.close()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(IdempotencyMiddleware)

    @app.post("/ping")
    async def ping():
        return {"ok": True}

    return app


def test_idempotency_key_rejects_duplicates():
    key = f"KC-TEST-{uuid.uuid4()}"
    app = _make_app()
    with TestClient(app) as c:
        r1 = c.post("/ping", headers={"Idempotency-Key": key})
        assert r1.status_code == 200
        r2 = c.post("/ping", headers={"Idempotency-Key": key})
        assert r2.status_code == 409

    async def cleanup():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM sync_operations WHERE idempotency_key = %s", (key,)
                )
        finally:
            await pool.close()

    asyncio.run(cleanup())
