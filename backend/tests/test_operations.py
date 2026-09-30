"""Tests for disputes, notifications, AI escalation, analytics, QR, and
dataset validation."""

import uuid
from datetime import date, timedelta

from tests.conftest import exec_db, query_db

PCB = "20000000-0000-0000-0000-000000000009"  # pcb
COPPER = "20000000-0000-0000-0000-000000000011"  # copper


def _txn(client, *, status_to=None):
    lot = client.post(
        "/api/v1/lots", json={"latitude": 19.0, "longitude": 73.0}
    ).json()
    txn = client.post(f"/api/v1/lots/{lot['id']}/transactions", json={}).json()
    if status_to:
        order = ["CLASSIFIED", "QUOTED", "QUOTE_ACCEPTED", "PICKUP_OR_DELIVERY",
                 "WEIGHT_VERIFIED", "HANDOVER_CONFIRMED", "PAYMENT_RECORDED", "COMPLETED"]
        for s in order[: order.index(status_to) + 1]:
            client.post(
                f"/api/v1/transactions/{txn['id']}/transition", json={"to_status": s}
            )
    return lot, txn


# ------------------------------------------------------------------- disputes


def test_collector_can_raise_dispute(client, collector_principal):
    _, txn = _txn(client)
    r = client.post(
        f"/api/v1/transactions/{txn['id']}/disputes",
        json={"reason": "Paid less than agreed", "reason_code": "price"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "open"

    listed = client.get("/api/v1/disputes")
    assert listed.status_code == 200
    assert any(d["id"] == body["id"] for d in listed.json())


def test_dispute_requires_reason(client, collector_principal):
    _, txn = _txn(client)
    r = client.post(f"/api/v1/transactions/{txn['id']}/disputes", json={})
    assert r.status_code == 422


def test_dispute_rejects_invalid_reason_code(client, collector_principal):
    _, txn = _txn(client)
    r = client.post(
        f"/api/v1/transactions/{txn['id']}/disputes",
        json={"reason": "x", "reason_code": "not_a_code"},
    )
    assert r.status_code == 422


def _provision_user(roles: list[str]) -> str:
    """Create a real user (FK targets require it) with the given roles."""
    from tests.conftest import provision_user

    user_id = str(uuid.uuid4())
    provision_user(user_id)
    for code in roles:
        row = query_db("SELECT id::int FROM roles WHERE code = %s", (code,))
        if row:
            exec_db(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s::uuid, %s)",
                (user_id, row[0][0]),
            )
    return user_id


def test_stranger_cannot_dispute_someone_elses_transaction(client, collector_principal):
    _, txn = _txn(client)
    from app.auth import Principal, get_principal
    from app.main import app as fastapi_app

    other = str(uuid.uuid4())
    fastapi_app.dependency_overrides[get_principal] = lambda: Principal(
        sub=other, user_id=other, roles=["collector"]
    )
    r = client.post(
        f"/api/v1/transactions/{txn['id']}/disputes", json={"reason": "spy"}
    )
    assert r.status_code in (401, 403)


def test_admin_resolves_dispute(client, collector_principal):
    _, txn = _txn(client)
    d = client.post(
        f"/api/v1/transactions/{txn['id']}/disputes",
        json={"reason": "Weight mismatch", "reason_code": "weight"},
    ).json()

    from app.auth import Principal, get_principal
    from app.main import app as fastapi_app
    from tests.conftest import cleanup_user

    admin_id = _provision_user(["super_admin"])
    fastapi_app.dependency_overrides[get_principal] = lambda: Principal(
        sub=admin_id, user_id=admin_id, roles=["super_admin"],
    )
    r = client.post(
        f"/api/v1/disputes/{d['id']}/resolve",
        json={"resolution": "Reweighed; adjusted to agreed weight", "status": "resolved"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"

    events = query_db(
        "SELECT event_type FROM dispute_events WHERE dispute_id = %s::uuid ORDER BY created_at",
        (d["id"],),
    )
    assert [e[0] for e in events] == ["RAISED", "RESOLVED"]
    cleanup_user(admin_id)


# -------------------------------------------------------------- notifications


def test_transition_creates_notification(client, collector_principal):
    _, txn = _txn(client)
    r = client.post(
        f"/api/v1/transactions/{txn['id']}/transition", json={"to_status": "CLASSIFIED"}
    )
    assert r.status_code == 200

    notes = client.get("/api/v1/notifications").json()
    assert any(n["entity_id"] == txn["id"] for n in notes)

    count = client.get("/api/v1/notifications/unread-count").json()
    assert count["unread"] >= 1

    nid = next(n["id"] for n in notes if n["entity_id"] == txn["id"])
    assert client.post(f"/api/v1/notifications/{nid}/read").status_code == 200
    after = client.get("/api/v1/notifications?unread_only=true").json()
    assert all(n["id"] != nid for n in after)


# ----------------------------------------------------------------- escalation


def test_escalate_and_resolve_ai_decision(client, collector_principal):
    lot = client.post("/api/v1/lots", json={}).json()
    item = client.post(f"/api/v1/lots/{lot['id']}/items", json={}).json()
    decision = client.post(
        f"/api/v1/lot-items/{item['id']}/classify", json={}
    ).json()["decision_id"]

    esc = client.post(
        f"/api/v1/ai-decisions/{decision}/escalate",
        json={"reason": "not confident", "stage": "recycler"},
    )
    assert esc.status_code == 201, esc.text
    esc_id = esc.json()["id"]
    assert esc.json()["stage"] == "recycler"

    # A reviewer supplies the correct category.
    from app.auth import Principal, get_principal
    from app.main import app as fastapi_app
    from tests.conftest import cleanup_user

    reviewer = _provision_user(["recycler"])
    fastapi_app.dependency_overrides[get_principal] = lambda: Principal(
        sub=reviewer, user_id=reviewer, roles=["recycler"]
    )
    r = client.post(
        f"/api/v1/ai-escalations/{esc_id}/resolve",
        json={"category_id": COPPER, "note": "looked like copper wire"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "resolved"

    # The item now carries the human-reviewed category...
    rows = query_db(
        "SELECT material_category_id::text, classification_source FROM lot_items WHERE id = %s::uuid",
        (item["id"],),
    )
    assert rows[0][0] == COPPER
    assert rows[0][1] == "recycler"

    # ...and the correction is training data, not silently trusted.
    corr = query_db(
        "SELECT is_training_candidate FROM ai_corrections WHERE ai_decision_id = %s::uuid",
        (decision,),
    )
    assert corr[0][0] is True
    cleanup_user(reviewer)


def test_escalation_to_admin(client, collector_principal):
    lot = client.post("/api/v1/lots", json={}).json()
    item = client.post(f"/api/v1/lots/{lot['id']}/items", json={}).json()
    decision = client.post(
        f"/api/v1/lot-items/{item['id']}/classify", json={}
    ).json()["decision_id"]
    esc_id = client.post(
        f"/api/v1/ai-decisions/{decision}/escalate", json={"stage": "recycler"}
    ).json()["id"]

    from app.auth import Principal, get_principal
    from app.main import app as fastapi_app
    from tests.conftest import cleanup_user

    rev = _provision_user(["recycler"])
    fastapi_app.dependency_overrides[get_principal] = lambda: Principal(
        sub=rev, user_id=rev, roles=["recycler"]
    )
    r = client.post(f"/api/v1/ai-escalations/{esc_id}/escalate-to-admin")
    assert r.status_code == 200
    assert r.json()["stage"] == "admin"

    # Cannot escalate again once it has left the recycler stage.
    assert client.post(f"/api/v1/ai-escalations/{esc_id}/escalate-to-admin").status_code == 409
    cleanup_user(rev)


# ------------------------------------------------------------------ analytics


def test_analytics_overview(client, admin_principal):
    r = client.get("/api/v1/admin/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    assert "counts" in body and "money" in body
    assert "completion_rate" in body
    assert body["counts"]["transactions"] >= 0
    assert body["money"]["outstanding"] == round(
        body["money"]["net_earnings_total"] - body["money"]["payments_confirmed_total"], 2
    )


def test_analytics_requires_admin(client, override_principal):
    override_principal(roles=["collector"])
    assert client.get("/api/v1/admin/analytics/overview").status_code == 403


def test_analytics_earnings_per_collector(client, admin_principal):
    r = client.get("/api/v1/admin/analytics/earnings")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ------------------------------------------------------------------------ QR


def test_qr_payload_for_handover(client, collector_principal):
    _, txn = _txn(client, status_to="WEIGHT_VERIFIED")
    ref = client.post(f"/api/v1/transactions/{txn['id']}/handover").json()["reference"]

    r = client.get(f"/api/v1/qr/handover/{ref}")
    assert r.status_code == 200
    body = r.json()
    assert body["reference"] == ref
    assert body["state"] == "pending"
    assert len(body["checksum"]) == 12
    assert ref in body["verify_url"]


def test_qr_unknown_reference_404(client, collector_principal):
    assert client.get("/api/v1/qr/handover/HO-DOESNOTEXIST").status_code == 404


# ------------------------------------------------------------ dataset quality


def test_price_validation_finds_nothing_wrong_with_good_data(client, admin_principal):
    r = client.post("/api/v1/admin/datasets/validate", params={"dataset": "price"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("passed", "warning", "failed")
    assert body["errors"] == 0, "seeded reference data should not contain price errors"


def test_validation_runs_are_recorded(client, admin_principal):
    run = client.post("/api/v1/admin/datasets/validate", params={"dataset": "recycler"}).json()
    runs = client.get("/api/v1/admin/datasets/validation-runs").json()
    assert any(x["id"] == run["run_id"] for x in runs)

    issues = client.get(
        f"/api/v1/admin/datasets/validation-runs/{run['run_id']}/issues"
    ).json()
    assert isinstance(issues, list)


def test_validation_catches_bad_price(client, admin_principal):
    """Insert an out-of-range price and prove the validator flags it."""
    exec_db(
        "INSERT INTO price_observations (material_category_id, observed_price_per_kg, "
        "source, city, verification_status) "
        "VALUES (%s::uuid, 999999, 'market', 'Pune', 'verified')",
        (PCB,),
    )
    try:
        run = client.post("/api/v1/admin/datasets/validate", params={"dataset": "price"}).json()
        assert run["status"] == "failed"
        assert run["errors"] >= 1
        issues = client.get(
            f"/api/v1/admin/datasets/validation-runs/{run['run_id']}/issues"
        ).json()
        assert any(i["code"] == "price_out_of_range" for i in issues)
    finally:
        exec_db(
            "DELETE FROM price_observations WHERE material_category_id = %s::uuid "
            "AND observed_price_per_kg = 999999",
            (PCB,),
        )


def test_validation_unknown_dataset(client, admin_principal):
    r = client.post("/api/v1/admin/datasets/validate", params={"dataset": "nope"})
    assert r.status_code == 200
    assert "available" in r.json()


# ------------------------------------------------------------- safety audio


def test_audio_availability_reports_coverage(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get("/api/v1/safety/audio-availability", params={"locale": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_topics"] == 10
    # No recordings uploaded yet -> coverage must be honestly 0.
    assert body["audio_available"] == 0
    assert body["coverage"] == 0.0
