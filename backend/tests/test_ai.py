from tests.conftest import query_db

PCB_CATEGORY = "20000000-0000-0000-0000-000000000009"  # pcb (recovered_material)


def _make_item(client):
    lot = client.post("/api/v1/lots", json={}).json()
    item = client.post(f"/api/v1/lots/{lot['id']}/items", json={}).json()
    return item


def test_classify_requires_auth(client):
    assert client.post("/api/v1/lot-items/00000000-0000-0000-0000-000000000000/classify").status_code == 401


def test_classify_null_provider_is_manual(client, collector_principal):
    item = _make_item(client)
    r = client.post(f"/api/v1/lot-items/{item['id']}/classify", json={})
    assert r.status_code == 200
    out = r.json()
    assert out["provider"] == "none"
    assert out["confidence"] == 0.0
    assert out["suggested_action"] == "manual"
    assert out["predicted_category_id"] is None


def test_confirm_decision(client, collector_principal):
    item = _make_item(client)
    decision = client.post(f"/api/v1/lot-items/{item['id']}/classify", json={}).json()
    r = client.post(f"/api/v1/ai-decisions/{decision['decision_id']}/confirm")
    assert r.status_code == 200
    rows = query_db(
        "SELECT status FROM ai_decisions WHERE id = %s::uuid",
        (decision["decision_id"],),
    )
    assert rows[0][0] == "confirmed"


def test_decision_already_processed(client, collector_principal):
    item = _make_item(client)
    decision = client.post(f"/api/v1/lot-items/{item['id']}/classify", json={}).json()
    assert client.post(f"/api/v1/ai-decisions/{decision['decision_id']}/confirm").status_code == 200
    assert client.post(f"/api/v1/ai-decisions/{decision['decision_id']}/confirm").status_code == 409


def test_correct_decision_stores_training_candidate(client, collector_principal):
    item = _make_item(client)
    decision = client.post(f"/api/v1/lot-items/{item['id']}/classify", json={}).json()
    decision_id = decision["decision_id"]

    r = client.post(
        f"/api/v1/ai-decisions/{decision_id}/correct",
        json={"corrected_category_id": PCB_CATEGORY, "correction_type": "category"},
    )
    assert r.status_code == 200

    rows = query_db(
        "SELECT is_training_candidate, corrected_category_id::text "
        "FROM ai_corrections WHERE ai_decision_id = %s::uuid",
        (decision_id,),
    )
    assert len(rows) == 1
    assert rows[0][0] is True
    assert rows[0][1] == PCB_CATEGORY

    item_rows = query_db(
        "SELECT material_category_id::text, kind, classification_source "
        "FROM lot_items WHERE id = %s::uuid",
        (item["id"],),
    )
    assert item_rows[0][0] == PCB_CATEGORY
    assert item_rows[0][1] == "recovered_material"
    assert item_rows[0][2] == "collector"
