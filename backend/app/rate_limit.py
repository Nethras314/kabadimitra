"""Fixed-window rate limiting (in-memory).

For the MVP single-instance backend this is sufficient. A multi-instance
deployment should swap the in-memory counters for Redis (the architecture
already reserves Redis for cache/jobs).
"""

import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        limit: int,
        window_seconds: int,
        exempt_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.exempt_paths = set(exempt_paths or [])
        self._counters: defaultdict[str, list[float]] = defaultdict(lambda: [0, 0.0])

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        count, window_start = self._counters[ip]
        if now - window_start >= self.window_seconds:
            count, window_start = 0, now
        count += 1
        self._counters[ip] = [count, window_start]

        if count > self.limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        return await call_next(request)
