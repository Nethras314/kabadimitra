import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import ForbiddenError, register_exception_handlers
from app.core.rate_limit import FixedWindowRateLimiter
from app.core.security import Principal, org_scope, require_role
from app.models.role import Role, effective_roles


def test_super_admin_implies_all_admin_roles():
    roles = effective_roles([Role.SUPER_ADMIN.value])
    assert "operations_admin" in roles
    assert "data_ai_admin" in roles
    assert "support" in roles


def test_operations_admin_implies_support():
    roles = effective_roles([Role.OPERATIONS_ADMIN.value])
    assert "operations_admin" in roles
    assert "support" in roles
    assert "data_ai_admin" not in roles


def test_principal_has_role_via_hierarchy():
    principal = Principal(sub="s", roles=[Role.SUPER_ADMIN.value])
    assert principal.has_role(Role.OPERATIONS_ADMIN.value)
    assert principal.has_role(Role.SUPPORT.value)
    assert principal.is_admin()


def test_collector_is_not_admin():
    principal = Principal(sub="s", roles=[Role.COLLECTOR.value])
    assert principal.is_admin() is False
    assert principal.has_role(Role.COLLECTOR.value)
    assert not principal.has_role(Role.SUPER_ADMIN.value)


def test_require_role_allows_and_denies():
    principal = Principal(sub="s", roles=[Role.SUPPORT.value])
    assert require_role(Role.SUPPORT.value)(principal) is principal
    with pytest.raises(ForbiddenError):
        require_role(Role.SUPER_ADMIN.value)(principal)


def test_org_scope_super_admin_sees_all():
    principal = Principal(sub="s", roles=[Role.SUPER_ADMIN.value])
    where, params = org_scope(principal)
    assert where == "TRUE"
    assert params == []


def test_org_scope_scoped_user():
    principal = Principal(sub="s", roles=[Role.COLLECTOR.value], organization_id="org-1")
    where, params = org_scope(principal)
    assert where == "organization_id = %s"
    assert params == ["org-1"]


def test_org_scope_no_org_sees_nothing():
    principal = Principal(sub="s", roles=[Role.COLLECTOR.value])
    where, _ = org_scope(principal)
    assert where == "FALSE"


def test_rate_limiter_blocks_over_limit():
    limiter = FixedWindowRateLimiter(limit=3, window_seconds=60)
    assert limiter.allow("k", now=0.0)
    assert limiter.allow("k", now=1.0)
    assert limiter.allow("k", now=2.0)
    assert limiter.allow("k", now=3.0) is False


def test_rate_limiter_resets_after_window():
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("k", now=0.0)
    assert limiter.allow("k", now=1.0) is False
    assert limiter.allow("k", now=61.0)  # window expired -> allowed again


def test_validation_error_does_not_leak_input():
    app = FastAPI()
    register_exception_handlers(app)

    class Payload(BaseModel):
        secret: int

    @app.post("/x")
    async def handler(payload: Payload):
        return {"ok": True}

    with TestClient(app) as client:
        r = client.post("/x", json={"secret": "not-an-int"})

    assert r.status_code == 422
    body = r.json()
    assert "not-an-int" not in str(body)
    assert "input" not in body["error"]["details"]["errors"][0]
