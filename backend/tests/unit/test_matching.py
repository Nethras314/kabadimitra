from app.services.matching import Lot, MatchingService, RecyclerCandidate


def make_lot(materials=None, weight=None):
    return Lot(lot_id="lot-1", material_category_ids=materials or ["PCB"], weight_kg=weight)


def candidate(
    recycler_id="r-1",
    authorized=True,
    accepted=None,
    service_radius=None,
    distance=5.0,
    pickup=False,
    transport=None,
    quote=None,
    reliability=0.5,
    name="Recycler",
):
    return RecyclerCandidate(
        recycler_id=recycler_id,
        name=name,
        authorized=authorized,
        accepted_materials=set(accepted or []),
        service_radius_km=service_radius,
        distance_km=distance,
        pickup_available=pickup,
        transport_cost=transport,
        quote_price_per_kg=quote,
        reliability=reliability,
    )


def test_authorized_recycler_matches():
    svc = MatchingService()
    results = svc.match(make_lot(), [candidate(recycler_id="r-1", authorized=True, accepted={"PCB"})])
    assert len(results) == 1
    assert results[0].recycler_id == "r-1"


def test_expired_recycler_excluded():
    svc = MatchingService()
    results = svc.match(make_lot(), [candidate(recycler_id="r-1", authorized=False)])
    assert results == []


def test_unsupported_material_excluded():
    svc = MatchingService()
    results = svc.match(make_lot(materials=["PCB"]), [candidate(authorized=True, accepted={"METAL"})])
    assert results == []


def test_outside_service_area_excluded():
    svc = MatchingService()
    results = svc.match(
        make_lot(),
        [candidate(authorized=True, accepted={"PCB"}, service_radius=20.0, distance=60.0)],
    )
    assert results == []


def test_inside_service_area_matches():
    svc = MatchingService()
    results = svc.match(
        make_lot(),
        [candidate(authorized=True, accepted={"PCB"}, service_radius=20.0, distance=10.0)],
    )
    assert len(results) == 1


def test_transport_cost_affects_ranking():
    svc = MatchingService()
    low_transport = candidate(recycler_id="low", authorized=True, accepted={"PCB"}, transport=200.0)
    high_transport = candidate(recycler_id="high", authorized=True, accepted={"PCB"}, transport=1000.0)
    results = svc.match(make_lot(), [high_transport, low_transport])
    assert results[0].recycler_id == "low"
    assert results[0].score > results[1].score


def test_quote_affects_ranking_but_not_dominant():
    svc = MatchingService()
    high_quote = candidate(recycler_id="high_quote", authorized=True, accepted={"PCB"}, quote=250.0)
    low_quote = candidate(recycler_id="low_quote", authorized=True, accepted={"PCB"}, quote=150.0)
    results = svc.match(make_lot(), [low_quote, high_quote])

    assert results[0].recycler_id == "high_quote"
    # quoted price is only 10% of the composite score, so a large price gap
    # must not dominate the ranking.
    assert results[0].score - results[1].score <= 10.0


def test_reason_documents_factors_and_net_earnings():
    svc = MatchingService()
    results = svc.match(
        make_lot(weight=10.0),
        [candidate(authorized=True, accepted={"PCB"}, quote=200.0, transport=100.0)],
    )
    reason = results[0].reason
    assert "material_coverage" in reason
    assert "transport_cost" in reason
    assert "quoted_price_per_kg" in reason
    assert reason["expected_net_earnings"] == 1900.0  # 10 * 200 - 100
