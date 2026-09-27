"""AI classification flow (assistive, not authoritative).

Collector photo -> classify (pluggable provider) -> confidence -> confirm or
correct. Corrections are stored as training candidates, never auto-ground-truth.
"""

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb

from ..ai.provider import get_provider
from ..audit import record_audit
from ..auth import Principal, get_principal
from ..collectors import require_collector
from ..config import settings
from ..db import get_db
from ..schemas import ClassifyOut, ClassifyRequest, CorrectRequest

router = APIRouter()


async def _item_for_collector(conn, item_id: str, collector_id: str):
    cur = await conn.execute(
        "SELECT li.id::text, li.kind, li.material_category_id::text, li.description "
        "FROM lot_items li JOIN lots l ON l.id = li.lot_id "
        "WHERE li.id = %s::uuid AND l.collector_id = %s::uuid",
        (item_id, collector_id),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return row


async def _decision_for_collector(conn, decision_id: str, collector_id: str):
    cur = await conn.execute(
        "SELECT d.id::text, d.status, d.lot_item_id::text, "
        "d.predicted_category_id::text, d.predicted_subcategory_id::text "
        "FROM ai_decisions d "
        "JOIN lot_items li ON li.id = d.lot_item_id "
        "JOIN lots l ON l.id = li.lot_id "
        "WHERE d.id = %s::uuid AND l.collector_id = %s::uuid",
        (decision_id, collector_id),
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    if row[1] != "suggested":
        raise HTTPException(status_code=409, detail="Decision already processed")
    return row


@router.post("/lot-items/{item_id}/classify", response_model=ClassifyOut)
async def classify(
    item_id: str,
    body: ClassifyRequest | None = None,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> ClassifyOut:
    collector_id = await require_collector(conn, principal)
    item = await _item_for_collector(conn, item_id, collector_id)

    provider = get_provider(settings.ai_provider)
    result = await provider.classify(
        {"id": item[0], "kind": item[1], "material_category_id": item[2], "description": item[3]},
        body.image_id if body else None,
    )

    action = (
        "confirm" if result.confidence >= settings.ai_confidence_threshold else "manual"
    )

    cur = await conn.execute(
        "INSERT INTO ai_decisions (ai_model_id, material_image_id, lot_item_id, "
        "predicted_category_id, predicted_subcategory_id, confidence, "
        "detected_material_types, quality_flags, status) "
        "VALUES (NULL, %s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, 'suggested') "
        "RETURNING id::text",
        (
            body.image_id if body else None,
            item_id,
            result.predicted_category_id,
            result.predicted_subcategory_id,
            result.confidence,
            Jsonb(result.detected_material_types)
            if result.detected_material_types is not None
            else None,
            Jsonb(result.quality_flags),
        ),
    )
    decision_id = (await cur.fetchone())[0]
    await record_audit(
        conn,
        action="ai.classified",
        actor_user_id=principal.user_id,
        entity_type="ai_decision",
        entity_id=decision_id,
    )
    return ClassifyOut(
        decision_id=decision_id,
        provider=result.provider,
        confidence=result.confidence,
        predicted_category_id=result.predicted_category_id,
        predicted_subcategory_id=result.predicted_subcategory_id,
        suggested_action=action,
        detected_material_types=result.detected_material_types,
        quality_flags=result.quality_flags,
    )


@router.post("/ai-decisions/{decision_id}/confirm")
async def confirm_decision(
    decision_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
):
    collector_id = await require_collector(conn, principal)
    row = await _decision_for_collector(conn, decision_id, collector_id)
    lot_item_id = row[2]
    predicted_category_id = row[3]
    predicted_subcategory_id = row[4]

    if predicted_category_id is not None:
        await conn.execute(
            "UPDATE lot_items SET "
            "material_category_id = %s::uuid, "
            "material_subcategory_id = %s::uuid, "
            "kind = (SELECT kind FROM material_categories WHERE id = %s::uuid), "
            "classification_source = 'ai' "
            "WHERE id = %s::uuid",
            (predicted_category_id, predicted_subcategory_id, predicted_category_id, lot_item_id),
        )
    await conn.execute(
        "UPDATE ai_decisions SET status = 'confirmed' WHERE id = %s::uuid", (decision_id,)
    )
    await record_audit(
        conn,
        action="ai.decision.confirmed",
        actor_user_id=principal.user_id,
        entity_type="ai_decision",
        entity_id=decision_id,
    )
    return {"status": "confirmed"}


@router.post("/ai-decisions/{decision_id}/correct")
async def correct_decision(
    decision_id: str,
    body: CorrectRequest,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
):
    collector_id = await require_collector(conn, principal)
    row = await _decision_for_collector(conn, decision_id, collector_id)
    lot_item_id = row[2]

    await conn.execute(
        "INSERT INTO ai_corrections (ai_decision_id, corrected_category_id, "
        "corrected_subcategory_id, corrected_by_user_id, correction_type, "
        "is_training_candidate, note) "
        "VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, true, %s)",
        (
            decision_id,
            body.corrected_category_id,
            body.corrected_subcategory_id,
            principal.user_id,
            body.correction_type,
            body.note,
        ),
    )

    if body.corrected_category_id is not None:
        await conn.execute(
            "UPDATE lot_items SET "
            "material_category_id = %s::uuid, "
            "material_subcategory_id = %s::uuid, "
            "kind = (SELECT kind FROM material_categories WHERE id = %s::uuid), "
            "classification_source = 'collector' "
            "WHERE id = %s::uuid",
            (
                body.corrected_category_id,
                body.corrected_subcategory_id,
                body.corrected_category_id,
                lot_item_id,
            ),
        )

    await conn.execute(
        "UPDATE ai_decisions SET status = 'corrected' WHERE id = %s::uuid", (decision_id,)
    )
    await record_audit(
        conn,
        action="ai.decision.corrected",
        actor_user_id=principal.user_id,
        entity_type="ai_decision",
        entity_id=decision_id,
    )
    return {"status": "corrected"}
