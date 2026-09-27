from datetime import date, timedelta

PCB = "20000000-0000-0000-0000-000000000009"  # pcb (recovered_material)


def _onboard_recycler(client, name, expiry_days, accept=True):
    ro = client.post(
        "/api/v1/recycler/organizations",
        json={
            "name": name,
            "authorization_number": f"AUTH-{name}",
            "expiry_date": (date.today() + timedelta(days=expiry_days)).isoformat(),
            "status": "verified",
            "facility_name": "Plant",
            "facility_latitude": 19.01,
            "facility_longitude": 73.0,
        },
    ).json()
    if accept:
        client.post(
            f"/api/v1/recycler/organizations/{ro['id']}/acceptance",
            json={"material_category_id": PCB},
        )
    return ro


def _make_lot_with_pcb(client):
    lot = client.post(
        "/api/v1/lots", json={"latitude": 19.0, "longitude": 73.0}
    ).json()
    client.post(
        f"/api/v1/lots/{lot['id']}/items",
        json={"material_category_id": PCB},
    )
    return lot


def test_generate_matches_ranks_verified(client, collector_admin_principal):
    ro = _onboard_recycler(client, "KBTEST-Matcher", expiry_days=30)
    lot = _make_lot_with_pcb(client)

    r = client.post(f"/api/v1/lots/{lot['id']}/matches")
    assert r.status_code == 200
    matches = r.json()
    assert len(matches) >= 1
    assert matches[0]["recycler_organization_id"] == ro["id"]
    assert matches[0]["score"] is not None


def test_expired_recycler_not_matched(client, collector_admin_principal):
    ro = _onboard_recycler(client, "KBTEST-ExpiredMatcher", expiry_days=-1)
    lot = _make_lot_with_pcb(client)

    r = client.post(f"/api/v1/lots/{lot['id']}/matches")
    assert r.status_code == 200
    ids = {m["recycler_organization_id"] for m in r.json()}
    assert ro["id"] not in ids


def test_non_accepting_recycler_not_matched(client, collector_admin_principal):
    ro = _onboard_recycler(client, "KBTEST-OtherAccept", expiry_days=30, accept=False)
    # give it acceptance for a DIFFERENT material
    other = "20000000-0000-0000-0000-000000000011"  # copper
    client.post(
        f"/api/v1/recycler/organizations/{ro['id']}/acceptance",
        json={"material_category_id": other},
    )
    lot = _make_lot_with_pcb(client)

    r = client.post(f"/api/v1/lots/{lot['id']}/matches")
    ids = {m["recycler_organization_id"] for m in r.json()}
    assert ro["id"] not in ids
