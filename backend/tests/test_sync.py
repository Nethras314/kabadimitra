import uuid

from tests.conftest import query_db

PCB = "20000000-0000-0000-0000-000000000009"


def test_sync_creates_lot(client, collector_principal):
    lot_id = str(uuid.uuid4())
    key = f"KC-LOT-{uuid.uuid4()}"
    r = client.post(
        "/api/v1/sync",
        json={
            "operations": [
                {
                    "idempotency_key": key,
                    "entity_type": "lot",
                    "id": lot_id,
                    "payload": {"title": "Offline lot"},
                }
            ]
        },
    )
    assert r.status_code == 200
    result = r.json()["results"][0]
    assert result["status"] == "applied"
    assert result["entity_id"] == lot_id


def test_sync_replays_idempotently(client, collector_principal):
    lot_id = str(uuid.uuid4())
    op = {
        "idempotency_key": f"KC-LOT-{uuid.uuid4()}",
        "entity_type": "lot",
        "id": lot_id,
        "payload": {"title": "Offline lot"},
    }
    r1 = client.post("/api/v1/sync", json={"operations": [op]})
    r2 = client.post("/api/v1/sync", json={"operations": [op]})
    assert r1.json()["results"][0]["status"] == "applied"
    assert r2.json()["results"][0]["status"] == "replayed"
    assert r2.json()["results"][0]["entity_id"] == lot_id

    rows = query_db("SELECT count(*)::int FROM lots WHERE id = %s::uuid", (lot_id,))
    assert rows[0][0] == 1


def test_sync_lot_then_item(client, collector_principal):
    lot_id = str(uuid.uuid4())
    item_id = str(uuid.uuid4())
    r = client.post(
        "/api/v1/sync",
        json={
            "operations": [
                {"idempotency_key": f"KC-LOT-{uuid.uuid4()}", "entity_type": "lot", "id": lot_id, "payload": {}},
                {
                    "idempotency_key": f"KC-ITEM-{uuid.uuid4()}",
                    "entity_type": "lot_item",
                    "id": item_id,
                    "payload": {"lot_id": lot_id, "description": "pcb", "material_category_id": PCB},
                },
            ]
        },
    )
    results = r.json()["results"]
    assert all(x["status"] == "applied" for x in results)


def test_sync_bad_payload_is_error(client, collector_principal):
    r = client.post(
        "/api/v1/sync",
        json={
            "operations": [
                {
                    "idempotency_key": f"KC-{uuid.uuid4()}",
                    "entity_type": "lot",
                    "id": str(uuid.uuid4()),
                    "payload": {"latitude": "not-a-number"},
                }
            ]
        },
    )
    result = r.json()["results"][0]
    assert result["status"] == "error"
    assert result["error"] is not None
