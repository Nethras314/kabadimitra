CHAIN = [
    "CLASSIFIED",
    "QUOTED",
    "QUOTE_ACCEPTED",
    "PICKUP_OR_DELIVERY",
    "WEIGHT_VERIFIED",
    "HANDOVER_CONFIRMED",
    "PAYMENT_RECORDED",
    "COMPLETED",
]


def _make_txn(client):
    lot = client.post("/api/v1/lots", json={}).json()
    return client.post(f"/api/v1/lots/{lot['id']}/transactions", json={}).json()


def test_transaction_lifecycle(client, collector_principal):
    txn = _make_txn(client)
    assert txn["status"] == "LOT_CREATED"

    for status in CHAIN:
        r = client.post(
            f"/api/v1/transactions/{txn['id']}/transition",
            json={"to_status": status},
        )
        assert r.status_code == 200, status
        assert r.json()["status"] == status

    # COMPLETED is terminal
    r = client.post(
        f"/api/v1/transactions/{txn['id']}/transition",
        json={"to_status": "CLASSIFIED"},
    )
    assert r.status_code == 409


def test_illegal_transition_rejected(client, collector_principal):
    txn = _make_txn(client)
    r = client.post(
        f"/api/v1/transactions/{txn['id']}/transition",
        json={"to_status": "COMPLETED"},
    )
    assert r.status_code == 409


def test_transition_creates_events(client, collector_principal):
    txn = _make_txn(client)
    client.post(
        f"/api/v1/transactions/{txn['id']}/transition",
        json={"to_status": "CLASSIFIED"},
    )
    events = client.get(f"/api/v1/transactions/{txn['id']}/events").json()
    assert len(events) >= 2  # LOT_CREATED + STATUS_CHANGED


def test_weights_and_final_weight(client, collector_principal):
    txn = _make_txn(client)
    declared = client.post(
        f"/api/v1/transactions/{txn['id']}/weights",
        json={"weight_type": "declared", "weight_kg": 10.0},
    ).json()
    assert declared["weight_type"] == "declared"

    client.post(
        f"/api/v1/transactions/{txn['id']}/weights",
        json={"weight_type": "final", "weight_kg": 9.5},
    )
    detail = client.get(f"/api/v1/transactions/{txn['id']}").json()
    assert detail["final_weight_kg"] == 9.5


def test_payment_and_confirmation(client, collector_principal):
    txn = _make_txn(client)
    p = client.post(
        f"/api/v1/transactions/{txn['id']}/payments",
        json={"method": "upi", "amount": 500.0, "reference": "UPI123"},
    ).json()
    assert p["method"] == "upi"
    assert p["status"] == "recorded"

    r = client.post(f"/api/v1/payments/{p['id']}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"
