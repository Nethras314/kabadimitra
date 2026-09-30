"""Command Code provider (vision-capable classification).

Calls the Command Code Provider API (OpenAI Chat Completions compatible) with
the collector's Cloudinary image URL and a schema-constrained prompt.

Guardrails (FR-AI-10): the system prompt forbids claiming exact gold/silver/
copper content, chemical composition, certified hazardousness, or lab-grade
material grade from a photograph. The prompt asks only for *visual category*
identification and an honest confidence.
"""

from __future__ import annotations

import json
import logging

import httpx

from ..config import settings
from .provider import (
    AlternativePrediction,
    BaseProvider,
    ClassificationResult,
    register_provider,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.commandcode.ai/provider/v1"
DEFAULT_MODEL = "google/gemini-3.5-flash-lite"

SYSTEM_PROMPT = """You classify e-waste items for informal waste collectors in India.

From the photograph, identify the single most likely ITEM TYPE from the allowed
category list provided. Base your answer only on what is visible.

STRICT RULES — never violate:
- Never state or estimate exact gold, silver, copper, or other metal content.
- Never state chemical composition, purity percentages, or assay results.
- Never certify hazardousness, regulatory compliance, or lab-grade material
  grade / material composition.
- If the image is unclear, dark, blurry, cropped, or shows multiple items, say so
  via quality_flags and return low confidence.
- If you cannot tell, return the closest match with confidence below 0.4 rather
  than inventing a confident answer.

Respond with JSON only, no prose, matching exactly:
{
  "category_code": "<one code from the allowed list, or null>",
  "confidence": <number between 0 and 1>,
  "detected_material_types": ["<short visual material labels>"],
  "quality_flags": {"blurry": bool, "dark": bool, "cropped": bool,
                    "multiple_items": bool, "unclear": bool},
  "alternatives": [{"category_code": "<code>", "confidence": <0-1>}]
}"""


class CommandCodeProvider(BaseProvider):
    provider = "command_code"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        zdr: bool | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.ai_api_key
        self.model = model or settings.ai_model or DEFAULT_MODEL
        self.base_url = (base_url or settings.ai_base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.ai_timeout_seconds
        self.zdr = settings.ai_zdr if zdr is None else zdr
        self.model_version = None

    async def classify(self, item: dict, image_id: str | None) -> ClassificationResult:
        if not self.api_key:
            logger.warning("CommandCodeProvider: AI_API_KEY not set; falling back to manual")
            return ClassificationResult(provider=self.provider, model=self.model)

        image_url = item.get("image_url")
        if not image_url:
            return ClassificationResult(
                confidence=0.0,
                quality_flags={"no_image": True},
                provider=self.provider,
                model=self.model,
            )

        categories = item.get("categories") or []
        code_to_id = {c["code"]: c["id"] for c in categories if c.get("code")}

        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    "Allowed categories:\n"
                    + "\n".join(f"- {c['code']}: {c['name']} ({c['kind']})" for c in categories)
                    + f"\n\nCollector description: {item.get('description') or '(none)'}"
                ),
            },
            {"type": "image_url", "image_url": {"url": image_url}},
        ]

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "max_tokens": 700,
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.zdr:
            headers["x-cmd-zdr"] = "1"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("CommandCodeProvider HTTP %s", exc.response.status_code)
            return ClassificationResult(
                confidence=0.0,
                quality_flags={"provider_error": f"http_{exc.response.status_code}"},
                provider=self.provider,
                model=self.model,
            )
        except httpx.HTTPError as exc:
            logger.warning("CommandCodeProvider request failed: %s", exc)
            return ClassificationResult(
                confidence=0.0,
                quality_flags={"provider_error": "request_failed"},
                provider=self.provider,
                model=self.model,
            )

        parsed = _parse(data)
        if parsed is None:
            return ClassificationResult(
                confidence=0.0,
                quality_flags={"provider_error": "unparseable_response"},
                provider=self.provider,
                model=self.model,
            )

        code = parsed.get("category_code")
        return ClassificationResult(
            predicted_category_id=code_to_id.get(code) if code else None,
            confidence=_clamp(parsed.get("confidence")),
            alternatives=[
                AlternativePrediction(
                    category_id=code_to_id.get(a.get("category_code")),
                    label=a.get("category_code"),
                    confidence=_clamp(a.get("confidence")),
                )
                for a in (parsed.get("alternatives") or [])
            ][:3],
            detected_material_types=parsed.get("detected_material_types") or None,
            quality_flags=parsed.get("quality_flags") or {},
            provider=self.provider,
            model=self.model,
        )


def _clamp(value, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _parse(data: dict) -> dict | None:
    """Extract the JSON object from a Chat Completions response."""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if not isinstance(content, str):
        return None

    text = content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _factory() -> CommandCodeProvider:
    return CommandCodeProvider()


register_provider("command_code", CommandCodeProvider)
register_provider("commandcode", CommandCodeProvider)
