def test_me_requires_auth(client):
    r = client.get("/api/v1/me")
    assert r.status_code == 401


def test_me_returns_principal(client, override_principal):
    override_principal(sub="sub-123", roles=["collector"], organization_id="org-1")
    r = client.get("/api/v1/me")
    assert r.status_code == 200
    body = r.json()
    assert body["sub"] == "sub-123"
    assert body["roles"] == ["collector"]
    assert body["organization_id"] == "org-1"


def test_admin_roles_forbidden_for_collector(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get("/api/v1/admin/roles")
    assert r.status_code == 403


def test_admin_roles_ok_for_admin(client, override_principal):
    override_principal(roles=["super_admin"])
    r = client.get("/api/v1/admin/roles")
    assert r.status_code == 200
    roles = r.json()
    codes = {x["code"] for x in roles}
    # Assert the current core roles are exposed (the set grows over time).
    assert {"collector", "kabadiwala", "aggregator", "recycler", "dismantler"} <= codes
    assert codes & {"super_admin", "platform_admin"}
