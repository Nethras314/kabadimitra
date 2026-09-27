"""Idempotency guard middleware.

For mutating requests carrying an `Idempotency-Key` header, the key is recorded
in `sync_operations` (which has a UNIQUE constraint on `idempotency_key`). A
duplicate key therefore rejects with 409, guaranteeing repeated sync requests
cannot create duplicate lots/transactions. The full response-replay + entity
mapping belongs to the offline-sync phase (Phase 6).
"""

from fastapi import Request, Response
from psycopg.errors import UniqueViolation
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_METHOD_TO_OPERATION = {"POST": "create", "PUT": "update", "PATCH": "update"}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        operation = _METHOD_TO_OPERATION.get(request.method)
        key = request.headers.get("idempotency-key") or request.headers.get("Idempotency-Key")

        if operation is None or not key:
            return await call_next(request)

        pool = request.app.state.pool
        async with pool.connection() as conn:
            try:
                await conn.execute(
                    "INSERT INTO sync_operations (idempotency_key, operation, status) "
                    "VALUES (%s, %s, 'pending')",
                    (key, operation),
                )
            except UniqueViolation:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "Idempotency key has already been used"},
                )

        response = await call_next(request)

        # Best-effort: mark the operation applied. The pending row stays pending
        # if the downstream handler raised (acceptable; the key is still consumed).
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "UPDATE sync_operations SET status = 'applied', synced_at = now() "
                    "WHERE idempotency_key = %s",
                    (key,),
                )
        except Exception:
            pass

        return response
