"""Recycler verification helpers.

A recycler is "verified" only if it has an authorization with status `verified`
whose expiry date is today or later. Expired authorizations are not verified
(FR-VERIF-04).
"""

from datetime import date


async def effective_verification(conn, recycler_organization_id: str) -> dict:
    cur = await conn.execute(
        "SELECT status, expiry_date, authorization_number, issuing_authority, "
        "authorization_type, verification_source, verification_date "
        "FROM recycler_authorizations "
        "WHERE recycler_organization_id = %s::uuid "
        "ORDER BY expiry_date DESC NULLS LAST",
        (recycler_organization_id,),
    )
    rows = await cur.fetchall()
    if not rows:
        return {"status": "pending", "verified": False, "authorization": None}

    today = date.today()
    verified = False
    effective_status = rows[0][0] or "pending"
    for r in rows:
        status_, expiry_ = r[0], r[1]
        if status_ == "verified":
            if expiry_ is None or expiry_ >= today:
                verified = True
                effective_status = "verified"
                break
            effective_status = "expired"

    latest = rows[0]
    authorization = {
        "authorization_number": latest[2],
        "issuing_authority": latest[3],
        "authorization_type": latest[4],
        "verification_source": latest[5],
        "verification_date": latest[6].isoformat() if latest[6] else None,
        "expiry_date": latest[1].isoformat() if latest[1] else None,
    }
    return {
        "status": effective_status,
        "verified": verified,
        "authorization": authorization,
    }
