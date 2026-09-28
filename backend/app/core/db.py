"""Database access: async connection pool (psycopg3)."""

from psycopg_pool import AsyncConnectionPool

from .config import settings


def create_pool() -> AsyncConnectionPool:
    return AsyncConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=10,
        open=False,
    )
