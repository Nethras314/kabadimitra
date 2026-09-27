"""Taxonomy read endpoints (collector-facing, localized)."""

from fastapi import APIRouter, Depends, Query

from ..auth import Principal, get_principal
from ..db import get_db
from ..schemas import CollectorCategoryOut

router = APIRouter()


@router.get("/taxonomy/collector-categories", response_model=list[CollectorCategoryOut])
async def list_collector_categories(
    locale: str = Query("en"),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> list[CollectorCategoryOut]:
    cur = await conn.execute(
        """
        SELECT cc.id::text, cc.code,
               COALESCE(t.value, cc.name) AS name,
               cc.sort_order
        FROM collector_categories cc
        LEFT JOIN translations t
               ON t.entity_type = 'collector_category'
              AND t.entity_id = cc.id
              AND t.field = 'name'
              AND t.locale = %s
        WHERE cc.is_active
        ORDER BY cc.sort_order
        """,
        (locale,),
    )
    rows = await cur.fetchall()
    return [
        CollectorCategoryOut(id=r[0], code=r[1], name=r[2], sort_order=r[3])
        for r in rows
    ]
