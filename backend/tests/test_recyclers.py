from datetime import date, timedelta


def _create(client, name, expiry_days, status="verified"):
    return client.post(
        "/api/v1/recycler/organizations",
        json={
            "name": name,
            "authorization_number": f"AUTH-{name}",
            "issuing_authority": "CPCB",
            "expiry_date": (date.today() + timedelta(days=expiry_days)).isoformat(),
            "status": status,
        },
    )


def test_create_recycler_requires_admin(client, override_principal):
    override_principal(roles=["collector"])
    assert client.post("/api/v1/recycler/organizations", json={"name": "X"}).status_code == 403


def test_create_verified_recycler(client, admin_principal):
    r = _create(client, "KBTEST-Recycler A", expiry_days=30)
    assert r.status_code == 201
    body = r.json()
    assert body["verified"] is True
    assert body["status"] == "verified"


def test_expired_authorization_not_verified(client, admin_principal):
    r = _create(client, "KBTEST-Recycler B", expiry_days=-1)
    assert r.status_code == 201
    body = r.json()
    assert body["verified"] is False
    assert body["status"] == "expired"


def test_pending_authorization_not_verified(client, admin_principal):
    r = client.post(
        "/api/v1/recycler/organizations",
        json={
            "name": "KBTEST-Recycler C",
            "authorization_number": "AUTH-C",
            "expiry_date": (date.today() + timedelta(days=30)).isoformat(),
            "status": "pending",
        },
    )
    assert r.status_code == 201
    assert r.json()["verified"] is False


def test_verified_list_excludes_expired(client, admin_principal):
    _create(client, "KBTEST-Verified", expiry_days=30)
    _create(client, "KBTEST-Expired", expiry_days=-1)

    r = client.get("/api/v1/recycler/verified")
    assert r.status_code == 200
    names = {x["name"] for x in r.json()}
    assert "KBTEST-Verified" in names
    assert "KBTEST-Expired" not in names
