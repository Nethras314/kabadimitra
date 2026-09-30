"""Regression tests for JWT verification.

Supabase signs with RS256 (RSA) on older projects and ES256 (EC / P-256) on
newer ones. The original implementation always used `RSAAlgorithm`, so on an
ES256 project `verify_token` raised `InvalidKeyError: Not an RSA key` and EVERY
authenticated endpoint returned 500. These tests pin both key types.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app import auth
from app.auth import verify_token
from fastapi import HTTPException

ISSUER = "https://example.supabase.co"
AUDIENCE = "authenticated"


def _rsa_jwk() -> dict:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update({"kid": "rsa-1", "alg": "RS256", "use": "sig"})
    return jwk


def _ec_jwk() -> dict:
    key = ec.generate_private_key(ec.SECP256R1())
    jwk = jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update({"kid": "ec-1", "alg": "ES256", "use": "sig"})
    return jwk


def _patch(monkeypatch, jwk: dict):
    """Point the verifier at a synthetic JWKS and issuer."""
    monkeypatch.setattr(auth, "_fetch_jwks", lambda: {"keys": [jwk]})
    # jwt_issuer_suffix is appended to supabase_url to build the expected
    # issuer, so patching the suffix is what actually changes the check.
    monkeypatch.setattr(auth.settings, "jwt_issuer_suffix", "")
    monkeypatch.setattr(auth.settings, "supabase_url", ISSUER)


def test_es256_key_is_accepted(monkeypatch):
    """The regression: an EC-signed token must verify, not 500."""
    key = _ec_private()
    pub = jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)
    pub.update({"kid": "ec-1", "alg": "ES256", "use": "sig"})
    _patch(monkeypatch, pub)

    token = jwt.encode(
        {"sub": "test-sub", "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 600},
        key,
        algorithm="ES256",
        headers={"kid": "ec-1"},
    )
    claims = verify_token(token)
    assert claims["sub"] == "test-sub"


_EC_KEYS = {}


def _ec_private():
    if "k" not in _EC_KEYS:
        _EC_KEYS["k"] = ec.generate_private_key(ec.SECP256R1())
    return _EC_KEYS["k"]


def test_rs256_key_is_accepted(monkeypatch):
    jwk = _rsa_jwk()
    _patch(monkeypatch, jwk)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Match the public JWK to this private key so the signature verifies.
    import json

    pub = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    pub.update({"kid": "rsa-1", "alg": "RS256", "use": "sig"})
    monkeypatch.setattr(auth, "_fetch_jwks", lambda: {"keys": [pub]})

    token = jwt.encode(
        {"sub": "rsa-sub", "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 600},
        key,
        algorithm="RS256",
        headers={"kid": "rsa-1"},
    )
    assert verify_token(token)["sub"] == "rsa-sub"


def test_unknown_kid_rejected(monkeypatch):
    jwk = _rsa_jwk()
    jwk["kid"] = "other"
    _patch(monkeypatch, jwk)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {"sub": "x", "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 600},
        key,
        algorithm="RS256",
        headers={"kid": "missing"},
    )
    with pytest.raises(HTTPException) as e:
        verify_token(token)
    assert e.value.status_code == 401


def test_algorithm_confusion_rejected(monkeypatch):
    """A token claiming RS256 must not verify against an EC key."""
    key = _ec_private()
    pub = jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)
    pub.update({"kid": "ec-1", "alg": "ES256", "use": "sig"})
    _patch(monkeypatch, pub)
    token = jwt.encode(
        {"sub": "x", "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 600},
        key,
        algorithm="ES256",
        headers={"kid": "ec-1"},
    )
    # Forge the header so the token claims RS256 while being EC-signed.
    parts = token.split(".")
    import base64
    import json as _json

    def b64(o):
        return base64.urlsafe_b64encode(_json.dumps(o).encode()).rstrip(b"=").decode()

    forged = ".".join(
        [b64({"alg": "RS256", "typ": "JWT", "kid": "ec-1"}), parts[1], parts[2]]
    )
    with pytest.raises(HTTPException) as e:
        verify_token(forged)
    assert e.value.status_code == 401


def test_expired_token_rejected(monkeypatch):
    _patch(monkeypatch, _rsa_jwk())
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    pub.update({"kid": "rsa-1", "alg": "RS256", "use": "sig"})
    monkeypatch.setattr(auth, "_fetch_jwks", lambda: {"keys": [pub]})
    token = jwt.encode(
        {"sub": "x", "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) - 10},
        key,
        algorithm="RS256",
        headers={"kid": "rsa-1"},
    )
    with pytest.raises(HTTPException) as e:
        verify_token(token)
    assert e.value.status_code == 401
