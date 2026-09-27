"""Admin-only endpoints (RBAC: platform_admin)."""

from fastapi import APIRouter, Depends

from ..auth import Principal
from ..db import get_db
from ..dependencies import require_role
from ..schemas import RoleOut

router = APIRouter()


@router.get("/admin/roles", response_model=list[RoleOut])
async def list_roles(
    principal: Principal = Depends(require_role("platform_admin")),
    conn=Depends(get_db),
) -> list[RoleOut]:
    cur = await conn.execute(
        "SELECT id, code, name, description FROM roles ORDER BY id"
    )
    rows = await cur.fetchall()
    return [RoleOut(id=r[0], code=r[1], name=r[2], description=r[3]) for r in rows]
