"""AI classification business logic.

Image -> classifier -> prediction -> confidence -> human confirmation -> final
classification. The classifier is injected (replaceable); business logic does
not change when the model does.
"""

from dataclasses import dataclass

from ..ai.provider import TIER_ACTION, BaseProvider, confidence_tier
from ..core.errors import ConflictError, NotFoundError
from ..repositories.ai import AICorrection, AIDecision, AIDecisionRepository, ItemInfo


@dataclass
class ClassificationOutcome:
    decision_id: str
    provider: str
    model: str | None
    model_version: str | None
    confidence: float
    tier: str
    suggested_action: str
    predicted_category_id: str | None
    predicted_subcategory_id: str | None
    alternatives: list[dict]
    detected_material_types: list[str] | None
    quality_flags: dict


class ClassificationService:
    def __init__(
        self,
        repository: AIDecisionRepository,
        provider: BaseProvider,
        high_threshold: float = 0.80,
        low_threshold: float = 0.50,
    ) -> None:
        self._repo = repository
        self._provider = provider
        self._high = high_threshold
        self._low = low_threshold

    async def classify(
        self,
        collector_id: str,
        item_id: str,
        image_id: str | None = None,
    ) -> ClassificationOutcome:
        item = await self._repo.get_item(item_id, collector_id)
        if item is None:
            raise NotFoundError("Item not found")

        result = await self._provider.classify(self._as_item_dict(item), image_id)
        tier = confidence_tier(result.confidence, self._high, self._low)

        decision = AIDecision(
            lot_item_id=item_id,
            material_image_id=image_id,
            predicted_category_id=result.predicted_category_id,
            predicted_subcategory_id=result.predicted_subcategory_id,
            confidence=result.confidence,
            alternatives=[self._alternative_to_dict(a) for a in result.alternatives],
            detected_material_types=result.detected_material_types,
            quality_flags=result.quality_flags,
            provider=result.provider,
            model=result.model,
            model_version=result.model_version,
            status="suggested",
        )
        decision_id = await self._repo.create_decision(decision)

        return ClassificationOutcome(
            decision_id=decision_id,
            provider=result.provider,
            model=result.model,
            model_version=result.model_version,
            confidence=result.confidence,
            tier=tier.value,
            suggested_action=TIER_ACTION[tier],
            predicted_category_id=result.predicted_category_id,
            predicted_subcategory_id=result.predicted_subcategory_id,
            alternatives=decision.alternatives,
            detected_material_types=result.detected_material_types,
            quality_flags=result.quality_flags,
        )

    async def confirm(self, collector_id: str, decision_id: str) -> dict:
        decision = await self._get_processing_decision(collector_id, decision_id)
        await self._repo.confirm(
            decision_id,
            decision.predicted_category_id,
            decision.predicted_subcategory_id,
        )
        return {"status": "confirmed"}

    async def correct(self, collector_id: str, decision_id: str, correction: AICorrection) -> dict:
        await self._get_processing_decision(collector_id, decision_id)
        correction.ai_decision_id = decision_id
        correction.is_training_candidate = True  # never auto-ground-truth (FR-AI-09)
        await self._repo.correct(decision_id, correction)
        return {"status": "corrected"}

    async def _get_processing_decision(self, collector_id: str, decision_id: str) -> AIDecision:
        decision = await self._repo.get_decision(decision_id, collector_id)
        if decision is None:
            raise NotFoundError("Decision not found")
        if decision.status != "suggested":
            raise ConflictError("Decision already processed")
        return decision

    @staticmethod
    def _as_item_dict(item: ItemInfo) -> dict:
        return {
            "id": item.id,
            "kind": item.kind,
            "material_category_id": item.material_category_id,
            "description": item.description,
        }

    @staticmethod
    def _alternative_to_dict(alternative) -> dict:
        return {
            "category_id": alternative.category_id,
            "subcategory_id": alternative.subcategory_id,
            "confidence": alternative.confidence,
            "label": alternative.label,
        }
