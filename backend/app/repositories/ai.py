"""AI decision data access.

The repository owns SQL (and, in the in-memory variant, the equivalent state)
for recording classification decisions, confirmations, and corrections. Business
rules live in the service layer, never here.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from psycopg_pool import AsyncConnectionPool


@dataclass
class ItemInfo:
    id: str
    kind: str | None
    material_category_id: str | None
    description: str | None


@dataclass
class AIDecision:
    id: str = ""
    lot_item_id: str | None = None
    material_image_id: str | None = None
    predicted_category_id: str | None = None
    predicted_subcategory_id: str | None = None
    confidence: float = 0.0
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    detected_material_types: list[str] | None = None
    quality_flags: dict[str, Any] = field(default_factory=dict)
    provider: str = "none"
    model: str | None = None
    model_version: str | None = None
    status: str = "suggested"
    created_at: str | None = None


@dataclass
class AICorrection:
    ai_decision_id: str = ""
    corrected_category_id: str | None = None
    corrected_subcategory_id: str | None = None
    corrected_by_user_id: str | None = None
    correction_type: str = "category"
    is_training_candidate: bool = True
    note: str | None = None


class AIDecisionRepository(ABC):
    @abstractmethod
    async def create_decision(self, decision: AIDecision) -> str:
        """Persist a decision; return its id."""

    @abstractmethod
    async def get_decision(self, decision_id: str, collector_id: str) -> AIDecision | None:
        """Return a decision owned by the collector, else None."""

    @abstractmethod
    async def get_item(self, item_id: str, collector_id: str) -> ItemInfo | None:
        """Return an item owned by the collector, else None."""

    @abstractmethod
    async def confirm(
        self, decision_id: str, category_id: str | None, subcategory_id: str | None
    ) -> None:
        """Mark a decision confirmed and apply the prediction to its item."""

    @abstractmethod
    async def correct(self, decision_id: str, correction: AICorrection) -> None:
        """Record a human correction and apply it to the item."""


class InMemoryAIDecisionRepository(AIDecisionRepository):
    """Test/reference implementation with no database."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[ItemInfo, str]] = {}
        self._decisions: dict[str, AIDecision] = {}
        self._corrections: list[AICorrection] = []
        self._final: dict[str, dict[str, str | None]] = {}
        self._next_id = 1

    def seed_item(self, item: ItemInfo, collector_id: str) -> None:
        self._items[item.id] = (item, collector_id)

    async def create_decision(self, decision: AIDecision) -> str:
        decision.id = decision.id or str(self._next_id)
        self._next_id += 1
        self._decisions[decision.id] = decision
        return decision.id

    async def get_decision(self, decision_id: str, collector_id: str) -> AIDecision | None:
        decision = self._decisions.get(decision_id)
        if decision is None or decision.lot_item_id is None:
            return None
        if self._owner_for_item(decision.lot_item_id) != collector_id:
            return None
        return decision

    async def get_item(self, item_id: str, collector_id: str) -> ItemInfo | None:
        entry = self._items.get(item_id)
        if entry is None or entry[1] != collector_id:
            return None
        return entry[0]

    async def confirm(
        self, decision_id: str, category_id: str | None, subcategory_id: str | None
    ) -> None:
        decision = self._decisions[decision_id]
        decision.status = "confirmed"
        if decision.lot_item_id is not None:
            self._final[decision.lot_item_id] = {
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "source": "ai",
            }

    async def correct(self, decision_id: str, correction: AICorrection) -> None:
        decision = self._decisions[decision_id]
        decision.status = "corrected"
        self._corrections.append(correction)
        if decision.lot_item_id is not None and correction.corrected_category_id is not None:
            self._final[decision.lot_item_id] = {
                "category_id": correction.corrected_category_id,
                "subcategory_id": correction.corrected_subcategory_id,
                "source": "collector",
            }

    def _owner_for_item(self, item_id: str) -> str | None:
        entry = self._items.get(item_id)
        return entry[1] if entry else None

    # --- test helpers ---
    def corrections(self) -> list[AICorrection]:
        return list(self._corrections)

    def final_for(self, item_id: str) -> dict[str, str | None] | None:
        return self._final.get(item_id)


class PostgresAIDecisionRepository(AIDecisionRepository):
    """Production repository backed by Supabase PostgreSQL."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_decision(self, decision: AIDecision) -> str:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO ai_decisions "
                "(lot_item_id, material_image_id, predicted_category_id, predicted_subcategory_id, "
                "confidence, detected_material_types, quality_flags, status, "
                "provider, model_name, model_version, alternatives) "
                "VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, "
                "'suggested', %s, %s, %s, %s::jsonb) "
                "RETURNING id::text",
                (
                    decision.lot_item_id,
                    decision.material_image_id,
                    decision.predicted_category_id,
                    decision.predicted_subcategory_id,
                    decision.confidence,
                    decision.detected_material_types,
                    decision.quality_flags,
                    decision.provider,
                    decision.model,
                    decision.model_version,
                    decision.alternatives,
                ),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to create AI decision")
            return row[0]

    async def get_decision(self, decision_id: str, collector_id: str) -> AIDecision | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT d.id::text, d.status, d.lot_item_id::text, d.predicted_category_id::text, "
                "d.predicted_subcategory_id::text, d.confidence, d.provider, d.model_name, "
                "d.model_version, d.alternatives "
                "FROM ai_decisions d "
                "JOIN lot_items li ON li.id = d.lot_item_id "
                "JOIN lots l ON l.id = li.lot_id "
                "WHERE d.id = %s::uuid AND l.collector_id = %s::uuid",
                (decision_id, collector_id),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return AIDecision(
                id=row[0],
                status=row[1],
                lot_item_id=row[2],
                predicted_category_id=row[3],
                predicted_subcategory_id=row[4],
                confidence=float(row[5]),
                provider=row[6],
                model=row[7],
                model_version=row[8],
                alternatives=row[9] or [],
            )

    async def get_item(self, item_id: str, collector_id: str) -> ItemInfo | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT li.id::text, li.kind, li.material_category_id::text, li.description "
                "FROM lot_items li JOIN lots l ON l.id = li.lot_id "
                "WHERE li.id = %s::uuid AND l.collector_id = %s::uuid",
                (item_id, collector_id),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return ItemInfo(id=row[0], kind=row[1], material_category_id=row[2], description=row[3])

    async def confirm(
        self, decision_id: str, category_id: str | None, subcategory_id: str | None
    ) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE ai_decisions SET status = 'confirmed' WHERE id = %s::uuid",
                    (decision_id,),
                )
                if category_id is not None:
                    await conn.execute(
                        "UPDATE lot_items SET material_category_id = %s::uuid, "
                        "material_subcategory_id = %s::uuid, "
                        "kind = (SELECT kind FROM material_categories WHERE id = %s::uuid), "
                        "classification_source = 'ai' "
                        "WHERE id = (SELECT lot_item_id FROM ai_decisions WHERE id = %s::uuid)",
                        (category_id, subcategory_id, category_id, decision_id),
                    )

    async def correct(self, decision_id: str, correction: AICorrection) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO ai_corrections (ai_decision_id, corrected_category_id, "
                    "corrected_subcategory_id, corrected_by_user_id, correction_type, "
                    "is_training_candidate, note) "
                    "VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s)",
                    (
                        decision_id,
                        correction.corrected_category_id,
                        correction.corrected_subcategory_id,
                        correction.corrected_by_user_id,
                        correction.correction_type,
                        correction.is_training_candidate,
                        correction.note,
                    ),
                )
                await conn.execute(
                    "UPDATE ai_decisions SET status = 'corrected' WHERE id = %s::uuid",
                    (decision_id,),
                )
                if correction.corrected_category_id is not None:
                    await conn.execute(
                        "UPDATE lot_items SET material_category_id = %s::uuid, "
                        "material_subcategory_id = %s::uuid, "
                        "kind = (SELECT kind FROM material_categories WHERE id = %s::uuid), "
                        "classification_source = 'collector' "
                        "WHERE id = (SELECT lot_item_id FROM ai_decisions WHERE id = %s::uuid)",
                        (
                            correction.corrected_category_id,
                            correction.corrected_subcategory_id,
                            correction.corrected_category_id,
                            decision_id,
                        ),
                    )
