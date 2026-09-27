"""Offline sync endpoint (batch, idempotent)."""

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Principal, get_principal
from ..collectors import require_collector
from ..db import get_db
from ..schemas import SyncRequest, SyncResponse, SyncResult
from ..sync import apply_operation

router = APIRouter()


@router.post("/sync", response_model=SyncResponse)
async def sync(
    body: SyncRequest,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> SyncResponse:
    collector_id = await require_collector(conn, principal)

    results: list[SyncResult] = []
    for op in body.operations:
        try:
            async with conn.transaction():
                result = await apply_operation(conn, principal, collector_id, op)
            results.append(result)
        except HTTPException as exc:
            results.append(
                SyncResult(
                    idempotency_key=op.idempotency_key,
                    status="error",
                    error=exc.detail,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                SyncResult(
                    idempotency_key=op.idempotency_key,
                    status="error",
                    error=str(exc),
                )
            )

    return SyncResponse(results=results)
