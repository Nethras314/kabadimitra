"""Pluggable AI classification provider.

AI is **assistive**, never authoritative. A provider suggests a category,
subcategory, and a confidence, plus a ranked list of alternative predictions.
The collector always confirms or corrects. Providers MUST NOT claim, from an
ordinary photograph: exact gold/silver/copper content, chemical composition, or
certified hazardousness (FR-AI-10).

The classifier is replaceable: implement ``BaseProvider`` and register it via
``register_provider`` (or ``app.ai.reference`` as an example) — business logic
is unchanged. The default ``none`` provider forces manual classification.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class ConfidenceTier(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def confidence_tier(
    confidence: float, high_threshold: float, low_threshold: float
) -> ConfidenceTier:
    if confidence >= high_threshold:
        return ConfidenceTier.HIGH
    if confidence >= low_threshold:
        return ConfidenceTier.MEDIUM
    return ConfidenceTier.LOW


# Collector-facing action per tier (FR-AI-06/FR-AI-07).
TIER_ACTION: dict[ConfidenceTier, str] = {
    ConfidenceTier.HIGH: "suggest",
    ConfidenceTier.MEDIUM: "alternatives",
    ConfidenceTier.LOW: "manual",
}


@dataclass
class AlternativePrediction:
    category_id: str | None = None
    subcategory_id: str | None = None
    confidence: float = 0.0
    label: str | None = None


@dataclass
class ClassificationResult:
    predicted_category_id: str | None = None
    predicted_subcategory_id: str | None = None
    confidence: float = 0.0
    alternatives: list[AlternativePrediction] = field(default_factory=list)
    detected_material_types: list[str] | None = None
    quality_flags: dict = field(default_factory=dict)
    provider: str = "none"
    model: str | None = None
    model_version: str | None = None


class BaseProvider:
    """Classifier interface. Subclass and implement ``classify``."""

    provider: str = "none"
    model: str | None = None
    model_version: str | None = None

    async def classify(self, item: dict, image_id: str | None) -> ClassificationResult:
        raise NotImplementedError


class NullProvider(BaseProvider):
    """No AI configured: returns an empty suggestion (manual classification)."""

    provider = "none"
    model = None
    model_version = None

    async def classify(self, item: dict, image_id: str | None) -> ClassificationResult:
        return ClassificationResult(
            provider=self.provider,
            model=self.model,
            model_version=self.model_version,
        )


_PROVIDERS: dict[str, type[BaseProvider]] = {
    "none": NullProvider,
}


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    _PROVIDERS[name] = cls


def get_provider(name: str) -> BaseProvider:
    cls = _PROVIDERS.get(name, NullProvider)
    return cls()
