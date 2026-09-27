import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import Principal, get_principal
from app.db import create_pool
from app.main import app


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def override_principal():
    def _set(**kwargs) -> Principal:
        p = Principal(
            sub=kwargs.get("sub", str(uuid.uuid4())),
            user_id=kwargs.get("user_id", str(uuid.uuid4())),
            roles=kwargs.get("roles", []),
            organization_id=kwargs.get("organization_id"),
            preferred_locale=kwargs.get("preferred_locale", "en"),
        )
        app.dependency_overrides[get_principal] = lambda: p
        return p

    return _set


def provision_collector(user_id: str, collector_type: str = "picker") -> None:
    """Create a `users` + `collectors` row so collector endpoints can resolve."""

    async def _run():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "INSERT INTO users (id, email) VALUES (%s::uuid, %s)",
                    (user_id, f"{user_id[:8]}@test.local"),
                )
                await conn.execute(
                    "INSERT INTO collectors (user_id, collector_type, display_name) "
                    "VALUES (%s::uuid, %s, 'Collector')",
                    (user_id, collector_type),
                )
        finally:
            await pool.close()

    asyncio.run(_run())


def cleanup_collector(user_id: str) -> None:
    """Delete everything a test collector created (safe if nothing exists)."""

    async def _run():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM ai_decisions WHERE lot_item_id IN "
                    "(SELECT id FROM lot_items WHERE lot_id IN "
                    "(SELECT id FROM lots WHERE collector_id IN "
                    "(SELECT id FROM collectors WHERE user_id = %s::uuid)))",
                    (user_id,),
                )
                await conn.execute(
                    "DELETE FROM sync_operations WHERE user_id = %s::uuid", (user_id,)
                )
                await conn.execute(
                    "DELETE FROM collectors WHERE user_id = %s::uuid", (user_id,)
                )
                await conn.execute("DELETE FROM users WHERE id = %s::uuid", (user_id,))
                await conn.execute(
                    "DELETE FROM audit_events WHERE actor_user_id = %s::uuid", (user_id,)
                )
        finally:
            await pool.close()

    asyncio.run(_run())


@pytest.fixture
def collector_principal():
    """A picker-role principal with a backing user+collector row; cleans up after."""
    user_id = str(uuid.uuid4())
    p = Principal(
        sub=user_id,
        user_id=user_id,
        roles=["picker"],
        organization_id=None,
        preferred_locale="en",
    )
    app.dependency_overrides[get_principal] = lambda: p
    provision_collector(user_id)
    yield p
    cleanup_collector(user_id)


def query_db(sql: str, params: tuple = ()):
    """Run a read query against the live DB and return rows."""

    async def _run():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                cur = await conn.execute(sql, params)
                return await cur.fetchall()
        finally:
            await pool.close()

    return asyncio.run(_run())


def provision_user(user_id: str) -> None:
    async def _run():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "INSERT INTO users (id, email) VALUES (%s::uuid, %s)",
                    (user_id, f"{user_id[:8]}@test.local"),
                )
        finally:
            await pool.close()

    asyncio.run(_run())


def cleanup_user(user_id: str) -> None:
    async def _run():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM price_observations WHERE source_user_id = %s::uuid",
                    (user_id,),
                )
                await conn.execute(
                    "DELETE FROM audit_events WHERE actor_user_id = %s::uuid", (user_id,)
                )
                await conn.execute("DELETE FROM users WHERE id = %s::uuid", (user_id,))
        finally:
            await pool.close()

    asyncio.run(_run())


def cleanup_test_organizations(prefix: str = "KBTEST-") -> None:
    async def _run():
        pool = create_pool()
        await pool.open()
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM organizations WHERE name LIKE %s", (f"{prefix}%",)
                )
        finally:
            await pool.close()

    asyncio.run(_run())


@pytest.fixture
def user_principal():
    """An authenticated principal with a backing `users` row (no collector)."""
    user_id = str(uuid.uuid4())
    p = Principal(
        sub=user_id,
        user_id=user_id,
        roles=["recycler"],
        organization_id=None,
        preferred_locale="en",
    )
    app.dependency_overrides[get_principal] = lambda: p
    provision_user(user_id)
    yield p
    cleanup_user(user_id)


@pytest.fixture
def collector_admin_principal():
    """A picker + platform_admin principal (for matching: onboard recycler, create lot)."""
    user_id = str(uuid.uuid4())
    p = Principal(
        sub=user_id,
        user_id=user_id,
        roles=["picker", "platform_admin"],
        organization_id=None,
        preferred_locale="en",
    )
    app.dependency_overrides[get_principal] = lambda: p
    provision_collector(user_id)
    yield p
    cleanup_collector(user_id)
    cleanup_test_organizations()


@pytest.fixture
def admin_principal():
    """A platform_admin principal; cleans up KBTEST-* organizations and the user."""
    user_id = str(uuid.uuid4())
    p = Principal(
        sub=user_id,
        user_id=user_id,
        roles=["platform_admin"],
        organization_id=None,
        preferred_locale="en",
    )
    app.dependency_overrides[get_principal] = lambda: p
    provision_user(user_id)
    yield p
    cleanup_test_organizations()
    cleanup_user(user_id)
