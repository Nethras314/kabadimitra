"""Collector profile resolution (picker / kabadiwala)."""

from fastapi import HTTPException

from .auth import Principal


async def resolve_collector(conn, principal: Principal) -> str:
    """Return the collector id for the principal, auto-provisioning if needed."""
    cur = await conn.execute(
        "SELECT id::text FROM collectors WHERE user_id = %s::uuid",
        (principal.user_id,),
    )
    row = await cur.fetchone()
    if row is not None:
        return row[0]

    collector_type = "kabadiwala" if "kabadiwala" in principal.roles else "picker"
    # display_name is a placeholder until collector onboarding (Phase 7).
    cur = await conn.execute(
        "INSERT INTO collectors (user_id, collector_type, display_name) "
        "VALUES (%s::uuid, %s, 'Collector') "
        "ON CONFLICT DO NOTHING "
        "RETURNING id::text",
        (principal.user_id, collector_type),
    )
    row = await cur.fetchone()
    if row is not None:
        return row[0]

    cur = await conn.execute(
        "SELECT id::text FROM collectors WHERE user_id = %s::uuid",
        (principal.user_id,),
    )
    row = await cur.fetchone()
    return row[0]


async def require_collector(conn, principal: Principal) -> str:
    # `collector` is the current role code; `picker` is the legacy name kept for
    # compatibility with older tokens/data.
    if not principal.has_role("collector", "kabadiwala", "picker"):
        raise HTTPException(status_code=403, detail="Collector role required")
    return await resolve_collector(conn, principal)
