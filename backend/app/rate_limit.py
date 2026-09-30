"""Rate limiting (fixed window) with a shared-store option.

Two problems with the original in-memory implementation are addressed here:

1. **Multi-instance deployments did not share counters** — every Render instance
   allowed the full limit. If `REDIS_URL` is set, counters live in Redis and are
   shared. Otherwise an in-process store is used (correct for a single instance).

2. **Client IP trusted `request.client.host`, which behind a proxy is the proxy
   itself**, so all traffic collapsed into a single bucket. `resolve_client_ip`
   now honours forwarded headers only when the app is explicitly configured to
   sit behind a proxy, so a client cannot spoof its way past the limiter.
"""

import os
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def resolve_client_ip(request: Request) -> str:
    """Best-effort client IP, safe behind a proxy."""
    direct = request.client.host if request.client else "unknown"
    trusted = os.getenv("TRUST_PROXY_HEADERS", "").lower() in ("1", "true", "yes")
    if not trusted:
        return direct

    try:
        hops = max(1, int(os.getenv("TRUSTED_PROXY_HOPS", "1") or "1"))
    except ValueError:
        hops = 1

    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[max(0, len(parts) - hops)]
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return direct


class _InProcessStore:
    """Fixed-window counters held in this process."""

    def __init__(self, window_seconds: int) -> None:
        self.window = window_seconds
        self._counters: dict[str, tuple[int, float]] = {}

    def hit(self, key: str) -> int:
        now = time.monotonic()
        count, start = self._counters.get(key, (0, now))
        if now - start >= self.window:
            count, start = 0, now
        count += 1
        self._counters[key] = (count, start)
        # Opportunistic cleanup so the dict cannot grow without bound.
        if len(self._counters) > 10_000:
            cutoff = now - self.window
            self._counters = {k: v for k, v in self._counters.items() if v[1] >= cutoff}
        return count


class _RedisStore:
    """Fixed-window counters shared across instances (INCR + EXPIRE)."""

    def __init__(self, redis_url: str, window_seconds: int) -> None:
        import redis  # optional dependency, imported lazily

        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.window = window_seconds

    def hit(self, key: str) -> int:
        bucket = int(time.time() // self.window)
        redis_key = f"ratelimit:{key}:{bucket}"
        pipe = self._redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, self.window)
        return int(pipe.execute()[0])


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        limit: int,
        window_seconds: int,
        exempt_paths: list[str] | None = None,
        redis_url: str | None = None,
    ) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.exempt_paths = set(exempt_paths or [])
        self.store = None
        if redis_url:
            try:
                self.store = _RedisStore(redis_url, window_seconds)
            except Exception:  # noqa: BLE001 - fall back rather than fail closed
                self.store = _InProcessStore(window_seconds)
        else:
            self.store = _InProcessStore(window_seconds)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        key = resolve_client_ip(request)
        count = self.store.hit(key)
        if count > self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": self.window_seconds},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - count))
        return response
