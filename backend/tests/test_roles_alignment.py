"""Regression guard: RBAC must accept the role codes actually seeded in the DB.

Earlier tests overrode the principal with hard-coded role names, so a rename in
the seed (picker -> collector, platform_admin -> super_admin) silently broke
real users while tests stayed green. These tests read the live role table.
"""

import uuid

from tests.conftest import cleanup_collector, provision_collector, query_db


def _role_codes() -> set[str]:
    return {r[0] for r in query_db("SELECT code FROM roles")}


def test_core_roles_are_seeded():
    codes = _role_codes()
    assert {"collector", "kabadiwala", "aggregator", "recycler", "dismantler"} <= codes
    assert codes & {"super_admin", "platform_admin"}, "no admin role seeded"


def test_real_admin_role_passes_rbac(client, override_principal):
    codes = _role_codes()
    admin_role = "super_admin" if "super_admin" in codes else "platform_admin"

    override_principal(roles=[admin_role])
    assert client.get("/api/v1/admin/roles").status_code == 200


def test_real_collector_role_passes_collector_gate(client, override_principal):
    codes = _role_codes()
    collector_role = "collector" if "collector" in codes else "picker"

    user_id = str(uuid.uuid4())
    provision_collector(user_id)
    try:
        override_principal(user_id=user_id, roles=[collector_role])
        r = client.post("/api/v1/lots", json={"title": "role-alignment"})
        assert r.status_code == 201, r.text
    finally:
        cleanup_collector(user_id)


def test_org_scope_recognises_real_admin_role():
    from app.auth import Principal
    from app.dependencies import org_scope

    codes = _role_codes()
    admin_role = "super_admin" if "super_admin" in codes else "platform_admin"
    principal = Principal(sub="x", roles=[admin_role])

    where, _ = org_scope(principal)
    assert where == "TRUE", "admin role must not be org-scoped"
