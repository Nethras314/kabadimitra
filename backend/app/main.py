"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import create_pool
from .idempotency import IdempotencyMiddleware
from .rate_limit import RateLimitMiddleware
from .routers import (
    admin,
    ai,
    auth,
    geo,
    health,
    lots,
    matching,
    media,
    pricing,
    recyclers,
    sync,
    taxonomy,
    transactions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = create_pool()
    await pool.open()
    app.state.pool = pool
    yield
    await pool.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(IdempotencyMiddleware)

_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(
    RateLimitMiddleware,
    limit=settings.rate_limit,
    window_seconds=settings.rate_limit_window_seconds,
    exempt_paths=["/health", "/health/ready"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(taxonomy.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(lots.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(pricing.router, prefix="/api/v1")
app.include_router(recyclers.router, prefix="/api/v1")
app.include_router(matching.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
app.include_router(geo.router, prefix="/api/v1")

