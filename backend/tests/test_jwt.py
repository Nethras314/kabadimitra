"""Regression tests for JWT verification.

Supabase signs with RS256 (RSA) on older projects and ES256 (EC / P-256) on
newer ones. The original implementation always used `RSAAlgorithm`, so on an
ES256 project `verify_token` raised `InvalidKeyError: Not an RSA key` and EVERY
authenticated endpoint returned 500. These tests pin both key types.
"""

import asyncio
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app import auth
from app.auth import verify_token, verify_token_async
from fastapi import HTTPException

ISSUER = "https://example.supabase.co"
AUDIENCE = "authenticated"


def run(coro):
    return asyncio.run(coro)


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


# --------------------------------------------------------------- async path
# The async verifier is the one used by every request. It must not block the
# event loop: the original synchronous `httpx.get` stalled the server on each
# cold request, which browsers saw as intermittent "Failed to fetch".


def test_async_verifier_accepts_es256(monkeypatch):
    key = _ec_private()
    pub = jwt.algorithms.ECAlgorithm.to_jwk(key.public_key(), as_dict=True)
    pub.update({"kid": "ec-1", "alg": "ES256", "use": "sig"})
    monkeypatch.setattr(auth.settings, "jwt_issuer_suffix", "")
    monkeypatch.setattr(auth.settings, "supabase_url", ISSUER)
    monkeypatch.setattr(auth, "_JWKS", {"keys": [pub]})
    monkeypatch.setattr(auth, "_JWKS_FETCHED_AT", time.time())

    token = jwt.encode(
        {"sub": "async-sub", "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 600},
        key,
        algorithm="ES256",
        headers={"kid": "ec-1"},
    )
    claims = run(verify_token_async(token))
    assert claims["sub"] == "async-sub"


def test_async_verifier_does_not_block_event_loop(monkeypatch):
    """A slow JWKS fetch must not stop other tasks from running."""

    class _SlowResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"keys": [_ec_jwk()]}

    class _SlowClient:
        async def get(self, *a, **k):
            await asyncio.sleep(0.25)      # simulate network latency
            return _SlowResponse()

    monkeypatch.setattr(auth, "_HTTP", _SlowClient())
    monkeypatch.setattr(auth.settings, "jwt_issuer_suffix", "")
    monkeypatch.setattr(auth.settings, "supabase_url", ISSUER)
    monkeypatch.setattr(auth, "_JWKS", None)
    monkeypatch.setattr(auth, "_JWKS_TASK", None)

    ticks = {"n": 0}

    async def ticker():
        while True:
            await asyncio.sleep(0.01)
            ticks["n"] += 1

    async def scenario():
        t = asyncio.create_task(ticker())
        await auth._fetch_jwks_async()
        t.cancel()

    started = time.monotonic()
    run(scenario())
    elapsed = time.monotonic() - started

    # If the fetch blocked the loop, the ticker would not have ticked at all.
    assert ticks["n"] > 5, f"event loop was blocked (ticks={ticks['n']})"
    assert elapsed < 1.0


def test_concurrent_cold_requests_share_one_fetch(monkeypatch):
    """Single-flight: N concurrent cold requests must trigger one network call."""

    calls = {"n": 0}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"keys": [_ec_jwk()]}

    class _Client:
        async def get(self, *a, **k):
            calls["n"] += 1
            await asyncio.sleep(0.05)
            return _Resp()

    monkeypatch.setattr(auth, "_HTTP", _Client())
    monkeypatch.setattr(auth, "_JWKS", None)
    monkeypatch.setattr(auth, "_JWKS_TASK", None)
    monkeypatch.setattr(auth.settings, "supabase_url", "https://x.supabase.co")

    async def scenario():
        await asyncio.gather(*[auth._fetch_jwks_async() for _ in range(10)])

    run(scenario())
    assert calls["n"] == 1, f"expected 1 fetch, got {calls['n']}"
