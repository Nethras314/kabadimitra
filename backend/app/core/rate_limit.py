"""Fixed-window rate limiting (pure limiter + FastAPI middleware)."""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class FixedWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._counters: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        current = now if now is not None else time.monotonic()
        hits = [t for t in self._counters.get(key, []) if current - t < self.window_seconds]
        if len(hits) >= self.limit:
            self._counters[key] = hits
            return False
        hits.append(current)
        self._counters[key] = hits
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        limit: int,
        window_seconds: float,
        exempt_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._limiter = FixedWindowRateLimiter(limit, window_seconds)
        self._exempt = set(exempt_paths or [])

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exempt:
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        if not self._limiter.allow(key):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Rate limit exceeded",
                        "details": {},
                    }
                },
            )
        return await call_next(request)
