import asyncio

import pytest

from app.ai.provider import ConfidenceTier, confidence_tier
from app.ai.reference import ReferenceProvider
from app.core.errors import ConflictError, NotFoundError
from app.repositories.ai import AICorrection, InMemoryAIDecisionRepository, ItemInfo
from app.services.ai import ClassificationService
from app.services.valuation import PricePoint, ValuationRequest, ValuationService


def run(coro):
    return asyncio.run(coro)


def make_service(repo):
    return ClassificationService(repo, ReferenceProvider())


def seed_item(repo, collector_id="c-1", item_id="item-1", **kwargs):
    info = ItemInfo(id=item_id, kind=kwargs.get("kind"), material_category_id=kwargs.get("material_category_id"), description=kwargs.get("description"))
    repo.seed_item(info, collector_id)
    return item_id


# --- confidence tiering ---

def test_confidence_tiers():
    assert confidence_tier(0.95, 0.80, 0.50) == ConfidenceTier.HIGH
    assert confidence_tier(0.80, 0.80, 0.50) == ConfidenceTier.HIGH
    assert confidence_tier(0.60, 0.80, 0.50) == ConfidenceTier.MEDIUM
    assert confidence_tier(0.50, 0.80, 0.50) == ConfidenceTier.MEDIUM
    assert confidence_tier(0.49, 0.80, 0.50) == ConfidenceTier.LOW


# --- classifier is replaceable (reference provider demo) ---

def test_reference_provider_high_confidence():
    result = run(ReferenceProvider().classify({"material_category_id": "PCB_ID", "description": None}, None))
    assert result.confidence == 0.90
    assert result.predicted_category_id == "PCB_ID"
    assert result.model == "reference-classifier"
    assert result.model_version == "0.1.0"
    assert len(result.alternatives) > 0


def test_reference_provider_medium_confidence():
    result = run(ReferenceProvider().classify({"description": "old pcb board"}, None))
    assert result.confidence == 0.60
    assert result.predicted_category_id is not None
    assert len(result.alternatives) > 0


def test_reference_provider_low_confidence():
    result = run(ReferenceProvider().classify({}, None))
    assert result.confidence == 0.20
    assert result.predicted_category_id is None
    assert result.alternatives == []


# --- classification service: decision logging ---

def test_classify_high_confidence_suggests_and_logs_decision():
    repo = InMemoryAIDecisionRepository()
    seed_item(repo, material_category_id="PCB_ID", kind="equipment")
    svc = make_service(repo)

    outcome = run(svc.classify("c-1", "item-1"))

    assert outcome.tier == "high"
    assert outcome.suggested_action == "suggest"
    assert outcome.predicted_category_id == "PCB_ID"
    assert outcome.provider == "reference"
    assert outcome.model == "reference-classifier"
    assert outcome.model_version == "0.1.0"

    decision = run(repo.get_decision(outcome.decision_id, "c-1"))
    assert decision is not None
    assert decision.confidence == 0.90
    assert decision.model_version == "0.1.0"
    assert decision.alternatives == outcome.alternatives
    assert decision.lot_item_id == "item-1"


def test_classify_medium_confidence_shows_alternatives():
    repo = InMemoryAIDecisionRepository()
    seed_item(repo, description="cable wire")
    svc = make_service(repo)

    outcome = run(svc.classify("c-1", "item-1"))

    assert outcome.tier == "medium"
    assert outcome.suggested_action == "alternatives"
    assert outcome.predicted_category_id is not None
    assert len(outcome.alternatives) > 0


def test_classify_low_confidence_asks_manual():
    repo = InMemoryAIDecisionRepository()
    seed_item(repo)
    svc = make_service(repo)

    outcome = run(svc.classify("c-1", "item-1"))

    assert outcome.tier == "low"
    assert outcome.suggested_action == "manual"
    assert outcome.predicted_category_id is None


# --- confirmation & correction ---

def test_confirm_applies_prediction():
    repo = InMemoryAIDecisionRepository()
    seed_item(repo, material_category_id="PCB_ID")
    svc = make_service(repo)
    outcome = run(svc.classify("c-1", "item-1"))

    assert run(svc.confirm("c-1", outcome.decision_id)) == {"status": "confirmed"}
    assert run(repo.get_decision(outcome.decision_id, "c-1")).status == "confirmed"
    assert repo.final_for("item-1")["category_id"] == "PCB_ID"
    assert repo.final_for("item-1")["source"] == "ai"


def test_correct_stores_training_candidate_not_ground_truth():
    repo = InMemoryAIDecisionRepository()
    seed_item(repo, description="cable")
    svc = make_service(repo)
    outcome = run(svc.classify("c-1", "item-1"))

    correction = AICorrection(
        corrected_category_id="CABLE_ID",
        correction_type="category",
        corrected_by_user_id="c-1",
        is_training_candidate=False,  # force false to prove the service overrides it
    )
    assert run(svc.correct("c-1", outcome.decision_id, correction)) == {"status": "corrected"}

    corrections = repo.corrections()
    assert len(corrections) == 1
    assert corrections[0].is_training_candidate is True
    assert corrections[0].ai_decision_id == outcome.decision_id
    assert repo.final_for("item-1")["category_id"] == "CABLE_ID"
    assert repo.final_for("item-1")["source"] == "collector"


def test_double_confirm_raises_conflict():
    repo = InMemoryAIDecisionRepository()
    seed_item(repo, material_category_id="PCB_ID")
    svc = make_service(repo)
    outcome = run(svc.classify("c-1", "item-1"))

    run(svc.confirm("c-1", outcome.decision_id))
    with pytest.raises(ConflictError):
        run(svc.confirm("c-1", outcome.decision_id))


def test_classify_foreign_item_not_found():
    repo = InMemoryAIDecisionRepository()
    seed_item(repo, collector_id="c-1")
    svc = make_service(repo)

    with pytest.raises(NotFoundError):
        run(svc.classify("c-2", "item-1"))


# --- valuation (indicative, not guaranteed) ---

def test_valuation_combines_inputs_into_indicative_value():
    svc = ValuationService()
    request = ValuationRequest(
        material_category_id="PCB_ID",
        weight_kg=10.0,
        location="Mumbai",
        observations=[
            PricePoint(price_per_kg=180.0, source="collector_entry"),
            PricePoint(price_per_kg=200.0, source="verification", verified=True),
        ],
        quotes=[PricePoint(price_per_kg=190.0, source="recycler_quote")],
        transport_cost=50.0,
    )

    valuation = svc.estimate(request)

    assert valuation.label == "INDICATIVE VALUE"
    assert valuation.estimated_value == 1850.0  # 10 * median(190) - 50
    assert valuation.value_range == (1750.0, 1950.0)
    assert valuation.basis["weight_kg"] == 10.0
    assert valuation.basis["location"] == "Mumbai"
    assert valuation.basis["verified_count"] == 1
    assert valuation.basis["sample_count"] == 3


def test_valuation_without_data_is_null_but_labeled():
    svc = ValuationService()
    valuation = svc.estimate(ValuationRequest(material_category_id="PCB_ID", weight_kg=10.0))

    assert valuation.label == "INDICATIVE VALUE"
    assert valuation.estimated_value is None
    assert valuation.value_range is None
