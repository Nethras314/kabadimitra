import asyncio

import pytest

from app.repositories.pricing import InMemoryPriceObservationRepository
from app.services.pricing import PriceKind, PriceObservation, PricingService


def run(coro):
    return asyncio.run(coro)


def make_service():
    return PricingService(InMemoryPriceObservationRepository())


def test_historical_price_aggregates():
    svc = make_service()
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=180.0, source="market")))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=220.0, source="market")))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=200.0, source="verification", verification_status="verified")))

    historical = run(svc.historical("PCB"))

    assert historical.kind == PriceKind.MARKET_OBSERVATION.value
    assert historical.average_price_per_kg == 200.0  # median of [180, 200, 220]
    assert historical.min_price_per_kg == 180.0
    assert historical.max_price_per_kg == 220.0
    assert historical.sample_count == 3
    assert historical.verified_count == 1


def test_price_range():
    svc = make_service()
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=180.0)))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=220.0)))
    assert run(svc.price_range("PCB")) == (180.0, 220.0)


def test_price_range_empty_is_none():
    svc = make_service()
    assert run(svc.price_range("NONE")) is None


def test_historical_empty_is_none():
    svc = make_service()
    historical = run(svc.historical("NONE"))
    assert historical.average_price_per_kg is None
    assert historical.sample_count == 0


def test_location_aware_weighted_average():
    svc = make_service()
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=200.0, latitude=19.0760, longitude=72.8777)))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=180.0, latitude=19.0760, longitude=72.8777)))
    # far away (Delhi) — outside the radius, must be excluded
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=100.0, latitude=28.6, longitude=77.2)))

    result = run(svc.location_aware("PCB", 19.0760, 72.8777, radius_km=50.0))

    assert result.kind == PriceKind.INDICATIVE_VALUE.value
    assert result.sample_count == 2
    assert result.average_price_per_kg == 190.0


def test_compare_existing_buyers_ranked_descending():
    svc = make_service()
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=170.0, source="collector_entry", buyer_type="other")))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=190.0, source="collector_entry", buyer_type="other")))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=210.0, source="recycler_quote")))

    buyers = run(svc.compare_existing_buyers("PCB"))

    assert len(buyers) == 2
    assert all(b.kind == PriceKind.EXISTING_BUYER_PRICE.value for b in buyers)
    assert buyers[0].price_per_kg == 190.0


def test_compare_recycler_quotes_ranked_descending():
    svc = make_service()
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=200.0, source="recycler_quote")))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=180.0, source="recycler_quote")))
    run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=160.0, source="collector_entry")))

    quotes = run(svc.compare_recycler_quotes("PCB"))

    assert len(quotes) == 2
    assert all(q.kind == PriceKind.RECYCLER_QUOTE.value for q in quotes)
    assert quotes[0].price_per_kg == 200.0


def test_record_rejects_non_positive_price():
    svc = make_service()
    with pytest.raises(ValueError):
        run(svc.record(PriceObservation(material_category_id="PCB", price_per_kg=0.0)))
