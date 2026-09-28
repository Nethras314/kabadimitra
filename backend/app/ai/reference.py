"""Deterministic reference classifier.

Not a real model. It maps a small vocabulary of collector signals to a
prediction with a confidence tier and ranked alternatives, so the full assistive
flow can be exercised and tested without a trained model. Real providers are
added the same way — implement ``BaseProvider`` and ``register_provider``.
"""

from .provider import (
    AlternativePrediction,
    BaseProvider,
    ClassificationResult,
    register_provider,
)

# Reference vocabulary: (label, category_id) for alternatives.
_REFERENCE_ALTERNATIVES = [
    ("PCB / Board", "20000000-0000-0000-0000-000000000009"),
    ("Cable / Wire", "20000000-0000-0000-0000-000000000010"),
    ("Mixed Metal", "20000000-0000-0000-0000-000000000014"),
]

_HINT_CATEGORIES = {
    "pcb": "20000000-0000-0000-0000-000000000009",
    "board": "20000000-0000-0000-0000-000000000009",
    "cable": "20000000-0000-0000-0000-000000000010",
    "wire": "20000000-0000-0000-0000-000000000010",
    "metal": "20000000-0000-0000-0000-000000000014",
}


class ReferenceProvider(BaseProvider):
    provider = "reference"
    model = "reference-classifier"
    model_version = "0.1.0"

    async def classify(self, item: dict, image_id: str | None) -> ClassificationResult:
        category_id = item.get("material_category_id")
        description = str(item.get("description") or "").lower()

        # Strong signal: the item already carries a backend category.
        if category_id:
            return ClassificationResult(
                predicted_category_id=category_id,
                confidence=0.90,
                alternatives=self._alternatives(exclude=category_id),
                provider=self.provider,
                model=self.model,
                model_version=self.model_version,
            )

        # Medium signal: a recognizable description keyword.
        hinted = self._hint_from(description)
        if hinted:
            return ClassificationResult(
                predicted_category_id=hinted,
                confidence=0.60,
                alternatives=self._alternatives(exclude=hinted),
                provider=self.provider,
                model=self.model,
                model_version=self.model_version,
            )

        # Weak signal: no usable information -> low confidence.
        return ClassificationResult(
            confidence=0.20,
            alternatives=[],
            provider=self.provider,
            model=self.model,
            model_version=self.model_version,
        )

    def _hint_from(self, description: str) -> str | None:
        for keyword, category_id in _HINT_CATEGORIES.items():
            if keyword in description:
                return category_id
        return None

    def _alternatives(self, exclude: str | None) -> list[AlternativePrediction]:
        return [
            AlternativePrediction(category_id=cid, label=label, confidence=0.45)
            for label, cid in _REFERENCE_ALTERNATIVES
            if cid != exclude
        ][:2]


register_provider("reference", ReferenceProvider)
