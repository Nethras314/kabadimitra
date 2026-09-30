"""Tests for the Command Code vision provider (no network calls)."""

import asyncio
import json

from app.ai import get_provider
from app.ai.command_code import SYSTEM_PROMPT, CommandCodeProvider, _clamp, _parse

CATEGORIES = [
    {"id": "cat-pcb", "code": "pcb", "name": "PCB / Circuit Board", "kind": "recovered_material"},
    {"id": "cat-cable", "code": "cable_wire", "name": "Cable / Wire", "kind": "recovered_material"},
]


def _response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_provider_registered():
    p = get_provider("command_code")
    assert isinstance(p, CommandCodeProvider)
    assert p.provider == "command_code"


def test_parse_plain_json():
    data = _response(json.dumps({"category_code": "pcb", "confidence": 0.9}))
    parsed = _parse(data)
    assert parsed["category_code"] == "pcb"
    assert parsed["confidence"] == 0.9


def test_parse_stripped_code_fence():
    data = _response('```json\n{"category_code": "cable_wire", "confidence": 0.4}\n```')
    parsed = _parse(data)
    assert parsed["category_code"] == "cable_wire"


def test_parse_content_parts():
    data = _response([{"type": "text", "text": '{"category_code": "pcb", "confidence": 0.7}'}])
    parsed = _parse(data)
    assert parsed["confidence"] == 0.7


def test_parse_handles_garbage():
    assert _parse({"choices": []}) is None
    assert _parse(_response("not json at all")) is None


def test_clamp_bounds():
    assert _clamp(1.7) == 1.0
    assert _clamp(-0.2) == 0.0
    assert _clamp("nope") == 0.0
    assert _clamp(None) == 0.0


def test_classify_without_api_key_is_manual():
    async def _run():
        provider = CommandCodeProvider(api_key="")
        return await provider.classify(
            {"image_url": "https://x/y.jpg", "categories": CATEGORIES}, None
        )

    result = asyncio.run(_run())
    assert result.confidence == 0.0
    assert result.provider == "command_code"


def test_classify_without_image_is_manual():
    async def _run():
        provider = CommandCodeProvider(api_key="test-key")
        return await provider.classify({"image_url": None, "categories": CATEGORIES}, None)

    result = asyncio.run(_run())
    assert result.confidence == 0.0
    assert result.quality_flags.get("no_image") is True


def test_system_prompt_forbids_unsafe_claims():
    lowered = SYSTEM_PROMPT.lower()
    for banned in ("exact gold", "chemical composition", "purity", "assay", "lab-grade"):
        assert banned in lowered, f"guardrail missing: {banned}"


def test_system_prompt_asks_for_json_only():
    assert "JSON only" in SYSTEM_PROMPT
