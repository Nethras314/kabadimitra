"""Database access: async connection pool + FastAPI dependency."""

from fastapi import Request
from psycopg_pool import AsyncConnectionPool

from .config import settings


def create_pool() -> AsyncConnectionPool:
    return AsyncConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=10,
        open=False,
    )


async def get_db(request: Request):
    """Yield a connection from the app-scoped pool (auto-commit on clean exit)."""
    pool: AsyncConnectionPool = request.app.state.pool
    async with pool.connection() as conn:
        yield conn
