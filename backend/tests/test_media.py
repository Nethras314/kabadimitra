import hashlib


def test_build_upload_signature(monkeypatch):
    from app import media
    from app.config import settings

    monkeypatch.setattr(settings, "cloudinary_api_secret", "s3cr3t")
    sig = media.build_upload_signature({"b": "2", "a": "1"})
    expected = hashlib.sha1("a=1&b=2s3cr3t".encode("utf-8")).hexdigest()
    assert sig == expected


def test_upload_params_503_when_unconfigured(client, override_principal):
    override_principal(roles=["picker"])
    r = client.get("/api/v1/media/upload-params")
    assert r.status_code == 503
