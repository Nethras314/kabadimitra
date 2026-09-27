"""Pluggable AI classification provider.

AI is **assistive**, never authoritative. A provider suggests a category and a
confidence; the collector always confirms or corrects. The default provider is
`none` (no AI), which yields an empty suggestion and forces manual
classification — matching the "low confidence -> collector selects" rule.

Real providers (e.g. OpenAI, Anthropic, self-hosted) are added by implementing
`BaseProvider` and registering it here. They MUST NOT claim exact gold/silver/
copper content, chemical composition, or lab-grade material grade from a photo.
"""

from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    predicted_category_id: str | None = None
    predicted_subcategory_id: str | None = None
    confidence: float = 0.0
    detected_material_types: list[str] | None = None
    quality_flags: dict = field(default_factory=dict)
    provider: str = "none"
    model: str | None = None


class BaseProvider:
    async def classify(self, item: dict, image_id: str | None) -> ClassificationResult:
        raise NotImplementedError


class NullProvider(BaseProvider):
    """No AI configured: returns an empty suggestion (manual classification)."""

    async def classify(self, item: dict, image_id: str | None) -> ClassificationResult:
        return ClassificationResult()


_PROVIDERS: dict[str, type[BaseProvider]] = {
    "none": NullProvider,
}


def get_provider(name: str) -> BaseProvider:
    cls = _PROVIDERS.get(name, NullProvider)
    return cls()
