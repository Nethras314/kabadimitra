import asyncio
import uuid

from app.auth import Principal, get_or_create_user
from app.audit import record_audit
from app.db import create_pool
from app.dependencies import org_scope


def test_org_scope_admin_sees_all():
    p = Principal(sub="x", roles=["platform_admin"])
    where, params = org_scope(p)
    assert where == "TRUE" and params == []


def test_org_scope_scoped_user():
    p = Principal(sub="x", roles=["collector"], organization_id="abc")
    where, params = org_scope(p)
    assert where == "organization_id = %s" and params == ["abc"]


def test_org_scope_no_org_sees_nothing():
    p = Principal(sub="x", roles=["collector"], organization_id=None)
    where, _ = org_scope(p)
    assert where == "FALSE"


def test_get_or_create_user_auto_provisions_and_is_idempotent():
    async def run():
        sub = str(uuid.uuid4())
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                u1 = await get_or_create_user(conn, sub, f"{sub[:8]}@test.local", None)
                assert u1["id"] == sub
                u2 = await get_or_create_user(conn, sub, f"{sub[:8]}@test.local", None)
                assert u2["id"] == sub
                await conn.execute("DELETE FROM users WHERE id = %s::uuid", (sub,))
        finally:
            await pool.close()

    asyncio.run(run())


def test_record_audit_persists_json():
    async def run():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                await record_audit(
                    conn,
                    action="test.action",
                    before={"a": 1},
                    after={"a": 2},
                )
                cur = await conn.execute(
                    "SELECT action, before, after FROM audit_events "
                    "WHERE action = 'test.action' ORDER BY created_at DESC LIMIT 1"
                )
                row = await cur.fetchone()
                assert row[0] == "test.action"
                assert row[1] == {"a": 1}
                assert row[2] == {"a": 2}
                await conn.execute("DELETE FROM audit_events WHERE action = 'test.action'")
        finally:
            await pool.close()

    asyncio.run(run())
