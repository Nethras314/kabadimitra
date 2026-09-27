import uuid

from tests.conftest import cleanup_collector, provision_collector


def test_lots_require_auth(client):
    assert client.get("/api/v1/lots").status_code == 401


def test_lots_require_collector_role(client, override_principal):
    override_principal(roles=["recycler"])
    assert client.post("/api/v1/lots", json={}).status_code == 403


def test_create_list_get_lot(client, collector_principal):
    r = client.post(
        "/api/v1/lots",
        json={"title": "Test Lot", "latitude": 19.0760, "longitude": 72.8777},
    )
    assert r.status_code == 201
    lot = r.json()
    assert lot["title"] == "Test Lot"
    assert lot["status"] == "draft"

    listing = client.get("/api/v1/lots")
    assert listing.status_code == 200
    assert lot["id"] in [l["id"] for l in listing.json()]

    detail = client.get(f"/api/v1/lots/{lot['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == lot["id"]


def test_add_item_and_attach_image(client, collector_principal):
    lot = client.post("/api/v1/lots", json={}).json()
    item = client.post(
        f"/api/v1/lots/{lot['id']}/items",
        json={"description": "old monitor", "kind": "equipment"},
    ).json()
    assert item["description"] == "old monitor"
    assert item["kind"] == "equipment"

    img = client.post(
        f"/api/v1/lots/{lot['id']}/items/{item['id']}/images",
        json={
            "cloudinary_public_id": "demo/abc123",
            "cloudinary_url": "https://res.cloudinary.com/demo/image/upload/abc123",
        },
    )
    assert img.status_code == 201
    assert img.json()["cloudinary_public_id"] == "demo/abc123"


def test_cannot_add_item_to_foreign_lot(client, collector_principal, override_principal):
    lot = client.post("/api/v1/lots", json={}).json()

    other_user = str(uuid.uuid4())
    provision_collector(other_user)
    override_principal(user_id=other_user, roles=["picker"])
    try:
        r = client.post(f"/api/v1/lots/{lot['id']}/items", json={})
        assert r.status_code == 403
    finally:
        cleanup_collector(other_user)
