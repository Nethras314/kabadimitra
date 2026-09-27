"""Audit-event recording (append-only trail for important mutations)."""

from psycopg.types.json import Jsonb


async def record_audit(
    conn,
    *,
    action: str,
    actor_user_id: str | None = None,
    organization_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    ip_address: str | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO audit_events
            (actor_user_id, organization_id, action, entity_type, entity_id, before, after, ip_address)
        VALUES
            (%s::uuid, %s::uuid, %s, %s, %s::uuid, %s, %s, %s::inet)
        """,
        (
            actor_user_id,
            organization_id,
            action,
            entity_type,
            entity_id,
            Jsonb(before) if before is not None else None,
            Jsonb(after) if after is not None else None,
            ip_address,
        ),
    )
