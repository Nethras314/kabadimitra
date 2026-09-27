from datetime import date, timedelta

PCB = "20000000-0000-0000-0000-000000000009"


def _onboard(client, name, lat, lng, expiry_days=30, material=None):
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
    if material:
        client.post(
            f"/api/v1/recycler/organizations/{ro['id']}/acceptance",
            json={"material_category_id": material},
        )
    return ro


def test_nearby_search_finds_verified(client, collector_admin_principal):
    ro = _onboard(client, "KBTEST-Nearby", 19.01, 73.0)
    r = client.get("/api/v1/recycler/nearby", params={"lat": 19.0, "lng": 73.0, "radius_km": 10})
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert ro["id"] in ids


def test_nearby_search_far_is_empty(client, collector_admin_principal):
    ro = _onboard(client, "KBTEST-Nearby-Far", 19.01, 73.0)
    r = client.get("/api/v1/recycler/nearby", params={"lat": 28.6, "lng": 77.2, "radius_km": 10})
    ids = {x["id"] for x in r.json()}
    assert ro["id"] not in ids


def test_nearby_search_material_filter(client, collector_admin_principal):
    accepts_pcb = _onboard(client, "KBTEST-Nearby-PCB", 19.01, 73.0, material=PCB)
    accepts_copper = _onboard(
        client,
        "KBTEST-Nearby-Cu",
        19.01,
        73.0,
        material="20000000-0000-0000-0000-000000000011",  # copper
    )
    r = client.get(
        "/api/v1/recycler/nearby",
        params={"lat": 19.0, "lng": 73.0, "radius_km": 10, "material_category_id": PCB},
    )
    ids = {x["id"] for x in r.json()}
    assert accepts_pcb["id"] in ids
    assert accepts_copper["id"] not in ids
