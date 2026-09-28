"""Foundation application factory.

Demonstrates the layered architecture (route -> service -> repository) on the
health domain and is the template the remaining domains migrate onto.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool

from .api import health
from .core.config import settings
from .core.db import create_pool
from .core.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool: AsyncConnectionPool | None = None
    if settings.database_url:
        pool = create_pool()
        await pool.open()
        app.state.pool = pool
    yield
    if pool is not None:
        await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)
    app.include_router(health.router)
    return app


app = create_app()
