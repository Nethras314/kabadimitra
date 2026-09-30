"""Tests for the 9-factor matching, quote flow, reliability, and rate limiting."""

import uuid
from datetime import date, timedelta

from tests.conftest import cleanup_collector, exec_db, query_db

PCB = "20000000-0000-0000-0000-000000000009"  # pcb
COPPER = "20000000-0000-0000-0000-000000000011"  # copper


def _onboard(client, name, *, lat=19.0, lng=73.0, expiry_days=30, accept=PCB,
             pickup=True, provides_pickup=False, transport_rate=None, service_area=True):
    ro = client.post(
        "/api/v1/recycler/organizations",
        json={
            "name": name,
            "authorization_number": f"AUTH-{name}",
            "expiry_date": (date.today() + timedelta(days=expiry_days)).isoformat(),
            "status": "verified",
            "facility_name": "Plant",
            "facility_latitude": lat,
            "facility_longitude": lng,
        },
    ).json()
    client.post(
        f"/api/v1/recycler/organizations/{ro['id']}/acceptance",
        json={"material_category_id": accept},
    )
    rid = ro["id"]
    exec_db(
        "UPDATE recycler_organizations SET pickup_available = %s, provides_pickup = %s, "
        "transport_rate_per_km = %s WHERE id = %s::uuid",
        (pickup, provides_pickup, transport_rate, rid),
    )
    if service_area:
        exec_db(
            "INSERT INTO recycler_service_areas (recycler_organization_id, name, radius_km, center) "
            "VALUES (%s::uuid, %s, 50, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
            (rid, f"{name} area", lng, lat),
        )
    return ro


def _lot(client, *, lat=19.0, lng=73.0, weight=10.0, category=PCB):
    lot = client.post(
        "/api/v1/lots", json={"latitude": lat, "longitude": lng}
    ).json()
    client.post(
        f"/api/v1/lots/{lot['id']}/items",
        json={"material_category_id": category, "declared_weight_kg": weight},
    )
    return lot


def test_match_exposes_all_nine_factors(client, collector_admin_principal):
    _onboard(client, "KBTEST-Factors")
    lot = _lot(client)
    matches = client.post(f"/api/v1/lots/{lot['id']}/matches").json()
    assert matches
    mid = matches[0]["id"]

    ex = client.get(f"/api/v1/lots/{lot['id']}/matches/{mid}/explanation")
    assert ex.status_code == 200
    factors = ex.json()["factors"]

    for key in (
        "authorization", "material_acceptance", "service_area", "distance",
        "pickup", "transport", "net_earnings", "quote", "reliability",
    ):
        assert key in factors, f"missing factor {key}"
        assert 0 <= factors[key]["score"] <= 100


def test_matches_require_gps(client, collector_admin_principal):
    _onboard(client, "KBTEST-NoGps")
    lot = client.post("/api/v1/lots", json={}).json()
    client.post(f"/api/v1/lots/{lot['id']}/items", json={"material_category_id": PCB})
    r = client.post(f"/api/v1/lots/{lot['id']}/matches")
    assert r.status_code == 400
    assert "location" in r.json()["detail"].lower()


def test_free_pickup_beats_paid_transport(client, collector_admin_principal):
    near_free = _onboard(client, "KBTEST-FreePickup", lat=19.0, lng=73.0,
                         provides_pickup=True)
    _onboard(client, "KBTEST-PaidTransport", lat=19.5, lng=73.5,
             provides_pickup=False, transport_rate=20.0)
    lot = _lot(client, lat=19.0, lng=73.0)

    matches = client.post(f"/api/v1/lots/{lot['id']}/matches").json()
    top = next(m for m in matches if m["recycler_organization_id"] == near_free["id"])
    ex = client.get(f"/api/v1/lots/{lot['id']}/matches/{top['id']}/explanation").json()
    assert ex["factors"]["transport"]["cost"] == 0.0
    assert ex["transport_cost"] == 0.0


def test_net_earnings_exceeds_zero_with_weight(client, collector_admin_principal):
    _onboard(client, "KBTEST-NetEarn")
    lot = _lot(client, weight=25.0)
    matches = client.post(f"/api/v1/lots/{lot['id']}/matches").json()
    ex = client.get(
        f"/api/v1/lots/{lot['id']}/matches/{matches[0]['id']}/explanation"
    ).json()
    # A verified market price exists for PCB, so net earnings should compute.
    assert ex["net_earnings"] is not None
    assert ex["net_earnings"] > 0


def test_reliability_refresh_endpoint(client, admin_principal):
    r = client.post("/api/v1/recycler/reliability/refresh")
    assert r.status_code == 200
    assert "refreshed" in r.json()


def test_rate_limit_headers_present(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get("/api/v1/safety/topics")
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers


def test_forwarded_header_ignored_without_trust(monkeypatch):
    from fastapi import Request

    from app.rate_limit import resolve_client_ip

    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)

    scope = {
        "type": "http",
        "client": ("10.0.0.1", 1234),
        "headers": [(b"x-forwarded-for", b"9.9.9.9")],
    }
    assert resolve_client_ip(Request(scope)) == "10.0.0.1"


def test_forwarded_header_honoured_when_trusted(monkeypatch):
    from fastapi import Request

    from app.rate_limit import resolve_client_ip

    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    scope = {
        "type": "http",
        "client": ("10.0.0.1", 1234),
        "headers": [(b"x-forwarded-for", b"9.9.9.9, 8.8.8.8")],
    }
    assert resolve_client_ip(Request(scope)) == "8.8.8.8"


def test_quote_flow_completes_lifecycle(client, collector_admin_principal):
    ro = _onboard(client, "KBTEST-QuoteFlow")
    lot = _lot(client)
    matches = client.post(f"/api/v1/lots/{lot['id']}/matches").json()
    match = next(m for m in matches if m["recycler_organization_id"] == ro["id"])

    txn = client.post(
        f"/api/v1/lots/{lot['id']}/transactions",
        json={"match_id": match["id"], "recycler_organization_id": ro["id"]},
    ).json()
    assert txn["status"] == "LOT_CREATED"
    client.post(f"/api/v1/transactions/{txn['id']}/transition", json={"to_status": "CLASSIFIED"})
    client.post(f"/api/v1/transactions/{txn['id']}/transition", json={"to_status": "QUOTED"})

    # A recycler-role principal linked to that org submits a quote.
    user_id = str(uuid.uuid4())
    exec_db(
        "INSERT INTO users (id, email, organization_id) VALUES (%s::uuid, %s, %s::uuid)",
        (user_id, f"{user_id[:8]}@test.local", ro["organization_id"]),
    )
    rid_row = query_db("SELECT id::text FROM roles WHERE code = 'recycler'")[0][0]
    exec_db(
        "INSERT INTO user_roles (user_id, role_id, organization_id) "
        "VALUES (%s::uuid, %s, %s::uuid)",
        (user_id, rid_row, ro["organization_id"]),
    )
    from app.auth import Principal, get_principal
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[get_principal] = lambda: Principal(
        sub=user_id, user_id=user_id, roles=["recycler"],
        organization_id=ro["organization_id"],
    )
    quote = client.post(
        "/api/v1/recycler/quotes",
        params={"lot_id": lot["id"]},
        json={"price_per_kg": 175.0, "terms": "net 7"},
    )
    assert quote.status_code == 201, quote.text
    quote_id = quote.json()["id"]

    # Collector side: restore the collector principal the fixture installed.
    fastapi_app.dependency_overrides[get_principal] = lambda: collector_admin_principal
    listed = client.get(f"/api/v1/lots/{lot['id']}/quotes")
    assert listed.status_code == 200
    assert any(q["id"] == quote_id for q in listed.json())

    accepted = client.post(f"/api/v1/quotes/{quote_id}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    after = client.get(f"/api/v1/transactions/{txn['id']}").json()
    assert after["status"] == "QUOTE_ACCEPTED"

    exec_db("DELETE FROM user_roles WHERE user_id = %s::uuid", (user_id,))
    exec_db("DELETE FROM users WHERE id = %s::uuid", (user_id,))


def test_quote_requires_matching(client, collector_admin_principal):
    _onboard(client, "KBTEST-QuoteNoMatch", accept=COPPER)
    lot = _lot(client, category=PCB)
    user_id = str(uuid.uuid4())
    ro = query_db(
        "SELECT ro.id::text, ro.organization_id::text FROM recycler_organizations ro "
        "JOIN organizations o ON o.id = ro.organization_id WHERE o.name = 'KBTEST-QuoteNoMatch'"
    )[0]
    exec_db(
        "INSERT INTO users (id, email, organization_id) VALUES (%s::uuid, %s, %s::uuid)",
        (user_id, f"{user_id[:8]}@t.local", ro[1]),
    )
    rid_row = query_db("SELECT id::text FROM roles WHERE code = 'recycler'")[0][0]
    exec_db(
        "INSERT INTO user_roles (user_id, role_id, organization_id) VALUES (%s::uuid,%s,%s::uuid)",
        (user_id, rid_row, ro[1]),
    )
    from app.auth import Principal, get_principal
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[get_principal] = lambda: Principal(
        sub=user_id, user_id=user_id, roles=["recycler"], organization_id=ro[1]
    )
    r = client.post(
        "/api/v1/recycler/quotes", params={"lot_id": lot["id"]}, json={"price_per_kg": 100}
    )
    assert r.status_code == 403

    fastapi_app.dependency_overrides.pop(get_principal, None)
    exec_db("DELETE FROM user_roles WHERE user_id = %s::uuid", (user_id,))
    exec_db("DELETE FROM users WHERE id = %s::uuid", (user_id,))
