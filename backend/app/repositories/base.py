"""Base repository: shared data-access surface."""

from psycopg_pool import AsyncConnectionPool


class BaseRepository:
    """Owns access to the connection pool; subclasses implement queries."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.pool = pool
