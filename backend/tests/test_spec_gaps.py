"""Tests for the spec-gap endpoints: safety, price board/trends/estimate,
earnings ledger, and handover records."""

import uuid

from tests.conftest import cleanup_collector, provision_collector, query_db

PCB = "20000000-0000-0000-0000-000000000009"  # pcb
BATTERY = "20000000-0000-0000-0000-000000000019"  # lead_acid_battery
COPPER = "20000000-0000-0000-0000-000000000011"  # copper


# ----------------------------------------------------------------- safety


def test_safety_topics_localized(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get("/api/v1/safety/topics", params={"locale": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 10
    codes = {t["code"] for t in body["topics"]}
    assert "no_open_burning" in codes
    # critical severity sorts first
    assert body["topics"][0]["severity"] == "critical"


def test_safety_has_hindi_and_marathi(client, override_principal):
    override_principal(roles=["collector"])
    en = client.get("/api/v1/safety/topics", params={"locale": "en"}).json()
    hi = client.get("/api/v1/safety/topics", params={"locale": "hi"}).json()
    mr = client.get("/api/v1/safety/topics", params={"locale": "mr"}).json()

    assert en["count"] == hi["count"] == mr["count"] == 10
    en_titles = {t["code"]: t["title"] for t in en["topics"]}
    hi_titles = {t["code"]: t["title"] for t in hi["topics"]}
    mr_titles = {t["code"]: t["title"] for t in mr["topics"]}

    # Translations must actually differ (not silently fall back to English).
    assert hi_titles["no_open_burning"] != en_titles["no_open_burning"]
    assert mr_titles["no_open_burning"] != en_titles["no_open_burning"]


def test_safety_topics_have_do_and_dont_and_pictograms(client, override_principal):
    override_principal(roles=["collector"])
    topics = client.get("/api/v1/safety/topics", params={"locale": "en"}).json()["topics"]
    burning = next(t for t in topics if t["code"] == "no_open_burning")
    assert burning["dont_text"]
    assert burning["do_text"]
    assert burning["pictograms"], "pictogram required by spec"
    kinds = {p["kind"] for p in burning["pictograms"]}
    assert kinds == {"do", "dont"}


def test_safety_contextual_for_battery(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get(
        "/api/v1/safety/for-categories",
        params=[("category_ids", BATTERY), ("locale", "en")],
    )
    assert r.status_code == 200
    codes = {t["code"] for t in r.json()["topics"]}
    assert "battery_safe_handling" in codes
    assert "no_open_burning" not in codes


def test_safety_requires_auth(client):
    assert client.get("/api/v1/safety/topics").status_code == 401


# --------------------------------------------------------- price board/trends


def test_price_board_has_data(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get("/api/v1/pricing/board", params={"city": "Pune", "locale": "en"})
    assert r.status_code == 200
    board = r.json()["board"]
    assert len(board) > 0
    pcb_row = next(b for b in board if b["code"] == "pcb")
    assert pcb_row["current_price"] is not None
    assert pcb_row["direction"] in ("rising", "falling", "stable")
    assert pcb_row["icon"]


def test_price_trends_pcb_rising(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get(
        "/api/v1/pricing/trends",
        params={"material_category_id": PCB, "city": "Pune", "days": 120},
    )
    assert r.status_code == 200
    t = r.json()
    assert t["direction"] == "rising"
    assert t["pct_change"] > 0
    assert t["samples"] >= 4
    assert len(t["series"]) >= 4


def test_estimate_value_range(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get(
        "/api/v1/pricing/estimate-value",
        params={"material_category_id": PCB, "weight_kg": 10, "city": "Pune"},
    )
    assert r.status_code == 200
    e = r.json()
    assert e["estimated_value"]["low"] <= e["estimated_value"]["mid"]
    assert e["estimated_value"]["mid"] <= e["estimated_value"]["high"]
    assert e["city_specific"] is True
    assert e["samples"] > 0


def test_estimate_value_scales_with_weight(client, override_principal):
    override_principal(roles=["collector"])
    one = client.get(
        "/api/v1/pricing/estimate-value",
        params={"material_category_id": COPPER, "weight_kg": 1},
    ).json()
    ten = client.get(
        "/api/v1/pricing/estimate-value",
        params={"material_category_id": COPPER, "weight_kg": 10},
    ).json()
    assert abs(ten["estimated_value"]["mid"] - one["estimated_value"]["mid"] * 10) < 1.0


def test_refresh_history_populates_table(client, override_principal):
    override_principal(roles=["collector"])
    r = client.post("/api/v1/pricing/refresh-history")
    assert r.status_code == 200
    assert r.json()["refreshed"] > 0
    rows = query_db("SELECT count(*)::int FROM price_history")
    assert rows[0][0] > 0


# ----------------------------------------------------------------- earnings


def test_earnings_empty_for_new_collector(client, override_principal):
    user_id = str(uuid.uuid4())
    provision_collector(user_id)
    try:
        override_principal(user_id=user_id, roles=["collector"])
        r = client.get("/api/v1/collectors/me/earnings")
        assert r.status_code == 200
        s = r.json()["summary"]
        assert s["total_earned"] == 0
        assert s["total_pending_due"] == 0
    finally:
        cleanup_collector(user_id)


def test_earnings_summary_text_localized(client, override_principal):
    user_id = str(uuid.uuid4())
    provision_collector(user_id)
    try:
        override_principal(user_id=user_id, roles=["collector"])
        en = client.get("/api/v1/collectors/me/earnings/summary-text", params={"locale": "en"}).json()
        mr = client.get("/api/v1/collectors/me/earnings/summary-text", params={"locale": "mr"}).json()
        assert en["text"] != mr["text"]
        assert "rupees" in en["text"]
    finally:
        cleanup_collector(user_id)


# ------------------------------------------------------------------ handover


def test_handover_requires_weight_verified(client, override_principal):
    user_id = str(uuid.uuid4())
    provision_collector(user_id)
    try:
        override_principal(user_id=user_id, roles=["collector"])
        lot = client.post("/api/v1/lots", json={}).json()
        txn = client.post(f"/api/v1/lots/{lot['id']}/transactions", json={}).json()
        # Still LOT_CREATED -> handover must be refused.
        r = client.post(f"/api/v1/transactions/{txn['id']}/handover")
        assert r.status_code == 409
    finally:
        cleanup_collector(user_id)


def test_handover_create_and_lookup(client, override_principal):
    user_id = str(uuid.uuid4())
    provision_collector(user_id)
    try:
        override_principal(user_id=user_id, roles=["collector"])
        lot = client.post(
            "/api/v1/lots", json={"latitude": 18.52, "longitude": 73.85}
        ).json()
        txn = client.post(f"/api/v1/lots/{lot['id']}/transactions", json={}).json()
        for status in (
            "CLASSIFIED",
            "QUOTED",
            "QUOTE_ACCEPTED",
            "PICKUP_OR_DELIVERY",
            "WEIGHT_VERIFIED",
        ):
            r = client.post(
                f"/api/v1/transactions/{txn['id']}/transition", json={"to_status": status}
            )
            assert r.status_code == 200, status

        r = client.post(f"/api/v1/transactions/{txn['id']}/handover")
        assert r.status_code == 201
        ref = r.json()["reference"]
        assert ref.startswith("HO-")

        lookup = client.get(f"/api/v1/handover/{ref}")
        assert lookup.status_code == 200
        data = lookup.json()
        assert data["reference"] == ref
        assert data["recycler_confirmed"] is False
        assert data["location"]["lat"] is not None
    finally:
        cleanup_collector(user_id)


def test_handover_confirm_requires_recycler_role(client, override_principal):
    user_id = str(uuid.uuid4())
    provision_collector(user_id)
    try:
        override_principal(user_id=user_id, roles=["collector"])
        lot = client.post(
            "/api/v1/lots", json={"latitude": 18.52, "longitude": 73.85}
        ).json()
        txn = client.post(f"/api/v1/lots/{lot['id']}/transactions", json={}).json()
        for status in (
            "CLASSIFIED",
            "QUOTED",
            "QUOTE_ACCEPTED",
            "PICKUP_OR_DELIVERY",
            "WEIGHT_VERIFIED",
        ):
            client.post(
                f"/api/v1/transactions/{txn['id']}/transition", json={"to_status": status}
            )
        ref = client.post(f"/api/v1/transactions/{txn['id']}/handover").json()["reference"]

        # Collector cannot confirm their own handover.
        r = client.post(f"/api/v1/handover/{ref}/confirm")
        assert r.status_code == 403
    finally:
        cleanup_collector(user_id)
