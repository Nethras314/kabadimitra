PCB = "20000000-0000-0000-0000-000000000009"  # pcb (recovered_material)


def test_price_observation_requires_auth(client):
    assert client.post("/api/v1/price-observations", json={}).status_code == 401


def test_invalid_source_rejected(client, user_principal):
    r = client.post(
        "/api/v1/price-observations",
        json={"material_category_id": PCB, "observed_price_per_kg": 100, "source": "bogus"},
    )
    assert r.status_code == 422


def test_collector_entry_is_unverified(client, user_principal):
    r = client.post(
        "/api/v1/price-observations",
        json={
            "material_category_id": PCB,
            "observed_price_per_kg": 120.5,
            "city": "Mumbai",
            "source": "collector_entry",
        },
    )
    assert r.status_code == 201
    obs = r.json()
    assert obs["verification_status"] == "unverified"
    assert obs["source"] == "collector_entry"


def test_verification_source_is_verified(client, user_principal):
    r = client.post(
        "/api/v1/price-observations",
        json={
            "material_category_id": PCB,
            "observed_price_per_kg": 150.0,
            "source": "verification",
        },
    )
    assert r.json()["verification_status"] == "verified"


def test_estimate_is_computed_from_observations(client, user_principal):
    client.post(
        "/api/v1/price-observations",
        json={"material_category_id": PCB, "observed_price_per_kg": 100.0, "city": "Pune"},
    )
    client.post(
        "/api/v1/price-observations",
        json={"material_category_id": PCB, "observed_price_per_kg": 200.0, "city": "Pune"},
    )

    r = client.get(
        "/api/v1/pricing/estimate",
        params={"material_category_id": PCB, "city": "Pune"},
    )
    assert r.status_code == 200
    est = r.json()
    assert est["summary"]["sample_count"] >= 2
    # No hard-coded price: the estimate is an aggregate of stored observations.
    assert est["summary"]["average_price_per_kg"] is not None
    assert est["summary"]["min_price_per_kg"] <= est["summary"]["max_price_per_kg"]
