def test_taxonomy_requires_auth(client):
    r = client.get("/api/v1/taxonomy/collector-categories")
    assert r.status_code == 401


def test_taxonomy_english(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get("/api/v1/taxonomy/collector-categories")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 14
    assert items[0]["name"] == "TV / Monitor"


def test_taxonomy_hindi(client, override_principal):
    override_principal(roles=["collector"])
    r = client.get("/api/v1/taxonomy/collector-categories", params={"locale": "hi"})
    assert r.status_code == 200
    items = r.json()
    assert items[0]["name"] == "टीवी / मॉनिटर"
