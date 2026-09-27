"""Material capture: lots, lot items, and material images (Cloudinary metadata)."""

from fastapi import APIRouter, Depends, HTTPException

from ..audit import record_audit
from ..auth import Principal, get_principal
from ..collectors import require_collector
from ..db import get_db
from ..schemas import (
    LotCreate,
    LotItemCreate,
    LotItemOut,
    LotOut,
    MaterialImageCreate,
    MaterialImageOut,
)

router = APIRouter()


async def _owned_lot_id(conn, lot_id: str, collector_id: str) -> str:
    cur = await conn.execute(
        "SELECT collector_id::text FROM lots WHERE id = %s::uuid", (lot_id,)
    )
    row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lot not found")
    if row[0] != collector_id:
        raise HTTPException(status_code=403, detail="Lot does not belong to you")
    return lot_id


@router.post("/lots", response_model=LotOut, status_code=201)
async def create_lot(
    body: LotCreate,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> LotOut:
    collector_id = await require_collector(conn, principal)

    pickup_location = None
    if body.latitude is not None and body.longitude is not None:
        pickup_location = f"SRID=4326;POINT({body.longitude} {body.latitude})"

    cur = await conn.execute(
        "INSERT INTO lots (collector_id, status, title, notes, pickup_address, pickup_location) "
        "VALUES (%s::uuid, 'draft', %s, %s, %s, %s::geography) "
        "RETURNING id::text, collector_id::text, status, title, notes, pickup_address, created_at",
        (collector_id, body.title, body.notes, body.pickup_address, pickup_location),
    )
    row = await cur.fetchone()
    await record_audit(
        conn,
        action="lot.created",
        actor_user_id=principal.user_id,
        entity_type="lot",
        entity_id=row[0],
        after={"title": body.title},
    )
    return LotOut(
        id=row[0],
        collector_id=row[1],
        status=row[2],
        title=row[3],
        notes=row[4],
        pickup_address=row[5],
        created_at=row[6],
    )


@router.get("/lots", response_model=list[LotOut])
async def list_lots(
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[LotOut]:
    collector_id = await require_collector(conn, principal)
    cur = await conn.execute(
        "SELECT id::text, collector_id::text, status, title, notes, pickup_address, created_at "
        "FROM lots WHERE collector_id = %s::uuid ORDER BY created_at DESC",
        (collector_id,),
    )
    rows = await cur.fetchall()
    return [
        LotOut(
            id=r[0],
            collector_id=r[1],
            status=r[2],
            title=r[3],
            notes=r[4],
            pickup_address=r[5],
            created_at=r[6],
        )
        for r in rows
    ]


@router.get("/lots/{lot_id}", response_model=LotOut)
async def get_lot(
    lot_id: str,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> LotOut:
    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)
    cur = await conn.execute(
        "SELECT id::text, collector_id::text, status, title, notes, pickup_address, created_at "
        "FROM lots WHERE id = %s::uuid",
        (lot_id,),
    )
    r = await cur.fetchone()
    return LotOut(
        id=r[0],
        collector_id=r[1],
        status=r[2],
        title=r[3],
        notes=r[4],
        pickup_address=r[5],
        created_at=r[6],
    )


@router.post("/lots/{lot_id}/items", response_model=LotItemOut, status_code=201)
async def add_item(
    lot_id: str,
    body: LotItemCreate,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> LotItemOut:
    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)

    cur = await conn.execute(
        "INSERT INTO lot_items (lot_id, collector_category_id, material_category_id, "
        "material_subcategory_id, kind, description, quantity, declared_weight_kg, "
        "condition_id, classification_source) "
        "VALUES (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s::uuid, %s) "
        "RETURNING id::text, lot_id::text, collector_category_id::text, material_category_id::text, "
        "material_subcategory_id::text, kind, description, quantity, declared_weight_kg, "
        "condition_id::text, classification_source, created_at",
        (
            lot_id,
            body.collector_category_id,
            body.material_category_id,
            body.material_subcategory_id,
            body.kind,
            body.description,
            body.quantity,
            body.declared_weight_kg,
            body.condition_id,
            body.classification_source,
        ),
    )
    row = await cur.fetchone()
    await record_audit(
        conn,
        action="lot_item.created",
        actor_user_id=principal.user_id,
        entity_type="lot_item",
        entity_id=row[0],
    )
    return LotItemOut(
        id=row[0],
        lot_id=row[1],
        collector_category_id=row[2],
        material_category_id=row[3],
        material_subcategory_id=row[4],
        kind=row[5],
        description=row[6],
        quantity=row[7],
        declared_weight_kg=row[8],
        condition_id=row[9],
        classification_source=row[10],
        created_at=row[11],
    )


@router.post(
    "/lots/{lot_id}/items/{item_id}/images",
    response_model=MaterialImageOut,
    status_code=201,
)
async def attach_image(
    lot_id: str,
    item_id: str,
    body: MaterialImageCreate,
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> MaterialImageOut:
    collector_id = await require_collector(conn, principal)
    await _owned_lot_id(conn, lot_id, collector_id)

    cur = await conn.execute(
        "SELECT lot_id::text FROM lot_items WHERE id = %s::uuid", (item_id,)
    )
    item = await cur.fetchone()
    if item is None or item[0] != lot_id:
        raise HTTPException(status_code=404, detail="Item not found in this lot")

    cur = await conn.execute(
        "INSERT INTO material_images (lot_item_id, lot_id, collector_id, cloudinary_public_id, "
        "cloudinary_url, image_kind, is_primary, mime_type, width, height) "
        "VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s) "
        "RETURNING id::text, lot_item_id::text, lot_id::text, cloudinary_public_id, "
        "cloudinary_url, image_kind, is_primary, created_at",
        (
            item_id,
            lot_id,
            collector_id,
            body.cloudinary_public_id,
            body.cloudinary_url,
            body.image_kind,
            body.is_primary,
            body.mime_type,
            body.width,
            body.height,
        ),
    )
    row = await cur.fetchone()
    return MaterialImageOut(
        id=row[0],
        lot_item_id=row[1],
        lot_id=row[2],
        cloudinary_public_id=row[3],
        cloudinary_url=row[4],
        image_kind=row[5],
        is_primary=row[6],
        created_at=row[7],
    )
