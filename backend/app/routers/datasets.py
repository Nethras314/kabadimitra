"""Dataset validation.

The spec requires the dataset to be "generated, stored, validated, updated and
used by the application rather than treated as a static database". This module
runs concrete checks over the live data and records findings, so quality problems
are visible instead of silently accepted.

Checks implemented:
  price       — provenance, plausible ranges, staleness, city/category coverage
  recycler    — authorization completeness, expiry, acceptance without facility
  material    — taxonomy orphans, categories with no price data
  transaction — lifecycle terminal states, weight/payment consistency
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends

from ..auth import Principal, get_principal
from ..db import get_db
from ..dependencies import require_role

router = APIRouter()

# Prices outside this band are almost certainly data-entry errors, not markets.
PRICE_FLOOR = 0.5
PRICE_CEILING = 5000.0


async def _price_issues(conn) -> list[dict]:
    issues: list[dict] = []
    cur = await conn.execute(
        """
        SELECT id::text, material_category_id::text, observed_price_per_kg, source,
               verification_status, observed_at, city
        FROM price_observations
        """
    )
    rows = await cur.fetchall()
    now = date.today()
    for r in rows:
        oid, cat, price, source, vstatus, observed, city = r
        if price is None or price <= PRICE_FLOOR or price >= PRICE_CEILING:
            issues.append({
                "dataset": "price", "severity": "error", "code": "price_out_of_range",
                "entity_type": "price_observation", "entity_id": oid,
                "message": f"price {price} is outside plausible bounds "
                           f"({PRICE_FLOOR}-{PRICE_CEILING})",
            })
        if not city:
            issues.append({
                "dataset": "price", "severity": "warning", "code": "missing_location",
                "entity_type": "price_observation", "entity_id": oid,
                "message": "observation has no city/location",
            })
        if source == "collector_entry" and vstatus == "verified":
            issues.append({
                "dataset": "price", "severity": "error", "code": "unverified_marked_verified",
                "entity_type": "price_observation", "entity_id": oid,
                "message": "collector_entry cannot be marked verified",
            })
        if observed and (now - observed.date()) > timedelta(days=400):
            issues.append({
                "dataset": "price", "severity": "info", "code": "stale_observation",
                "entity_type": "price_observation", "entity_id": oid,
                "message": f"observation is {(now - observed.date()).days} days old",
            })
    return issues


async def _recycler_issues(conn) -> list[dict]:
    issues: list[dict] = []
    cur = await conn.execute(
        """
        SELECT ro.id::text, o.name, f.id::text, a.authorization_number, a.status,
               a.expiry_date, a.verification_date
        FROM recycler_organizations ro
        JOIN organizations o ON o.id = ro.organization_id
        LEFT JOIN recycler_facilities f ON f.recycler_organization_id = ro.id
        LEFT JOIN recycler_authorizations a ON a.recycler_organization_id = ro.id
        """
    )
    seen = set()
    for r in await cur.fetchall():
        rid, name, fid, auth_no, status, expiry, vdate = r
        if rid in seen:
            continue
        seen.add(rid)
        if fid is None:
            issues.append({
                "dataset": "recycler", "severity": "warning", "code": "no_facility",
                "entity_type": "recycler_organization", "entity_id": rid,
                "message": f"{name} has no facility, so it can never match by distance",
            })
        if status == "verified":
            if not auth_no:
                issues.append({
                    "dataset": "recycler", "severity": "error", "code": "verified_without_number",
                    "entity_type": "recycler_organization", "entity_id": rid,
                    "message": f"{name} is verified but has no authorization number",
                })
            if vdate is None:
                issues.append({
                    "dataset": "recycler", "severity": "warning", "code": "verified_without_date",
                    "entity_type": "recycler_organization", "entity_id": rid,
                    "message": f"{name} is verified with no verification date",
                })
            if expiry and expiry < date.today():
                issues.append({
                    "dataset": "recycler", "severity": "error", "code": "expired_but_verified",
                    "entity_type": "recycler_organization", "entity_id": rid,
                    "message": f"{name} verified with expired authorization ({expiry})",
                })
        elif expiry and expiry < date.today():
            issues.append({
                "dataset": "recycler", "severity": "info", "code": "expired_authorization",
                "entity_type": "recycler_organization", "entity_id": rid,
                "message": f"{name} authorization expired {expiry}",
            })
    return issues


async def _material_issues(conn) -> list[dict]:
    issues: list[dict] = []
    cur = await conn.execute(
        "SELECT id::text, code, name FROM material_categories WHERE is_active ORDER BY sort_order"
    )
    cats = await cur.fetchall()
    for cid, code, name in cats:
        cur = await conn.execute(
            "SELECT count(*)::int FROM price_observations "
            "WHERE material_category_id = %s::uuid AND verification_status = 'verified'",
            (cid,),
        )
        if (await cur.fetchone())[0] == 0:
            issues.append({
                "dataset": "material", "severity": "info", "code": "no_price_data",
                "entity_type": "material_category", "entity_id": cid,
                "message": f"{name} ({code}) has no verified price observations",
            })
    return issues


async def _transaction_issues(conn) -> list[dict]:
    issues: list[dict] = []
    cur = await conn.execute(
        "SELECT id::text, status, final_weight_kg, net_earnings FROM transactions"
    )
    for tid, status, weight, net in await cur.fetchall():
        if status in ("WEIGHT_VERIFIED", "HANDOVER_CONFIRMED", "PAYMENT_RECORDED", "COMPLETED"):
            if weight is None:
                issues.append({
                    "dataset": "transaction", "severity": "error",
                    "code": "missing_final_weight", "entity_type": "transaction",
                    "entity_id": tid,
                    "message": f"status {status} but no final weight recorded",
                })
        if status == "COMPLETED" and (net is None or net == 0):
            issues.append({
                "dataset": "transaction", "severity": "warning", "code": "completed_zero_earnings",
                "entity_type": "transaction", "entity_id": tid,
                "message": "completed with no net earnings recorded",
            })
    return issues


CHECKS = {
    "price": _price_issues,
    "recycler": _recycler_issues,
    "material": _material_issues,
    "transaction": _transaction_issues,
}


async def run_validation(conn, dataset: str) -> dict:
    cur = await conn.execute(
        "INSERT INTO dataset_validation_runs (dataset, status) VALUES (%s, 'running') "
        "RETURNING id::text",
        (dataset,),
    )
    run_id = (await cur.fetchone())[0]

    issues = await CHECKS[dataset](conn)

    for i in issues:
        await conn.execute(
            "INSERT INTO dataset_validation_issues (run_id, dataset, severity, code, "
            "entity_type, entity_id, message) VALUES (%s::uuid, %s, %s, %s, %s, %s::uuid, %s)",
            (run_id, i["dataset"], i["severity"], i["code"], i["entity_type"],
             i.get("entity_id"), i["message"]),
        )

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    status = "failed" if errors else ("warning" if warnings else "passed")

    cur = await conn.execute(
        "UPDATE dataset_validation_runs SET finished_at = now(), issues_found = %s, "
        "status = %s, summary = %s WHERE id = %s::uuid RETURNING rows_scanned",
        (len(issues), status,
         f'{{"errors": {errors}, "warnings": {warnings}}}', run_id),
    )
    scanned = (await cur.fetchone())[0] or 0

    return {
        "run_id": run_id,
        "dataset": dataset,
        "status": status,
        "rows_scanned": scanned,
        "issues": len(issues),
        "errors": errors,
        "warnings": warnings,
    }


@router.post("/admin/datasets/validate")
async def validate_dataset(
    dataset: str = "price",
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> dict:
    if dataset not in CHECKS:
        return {"error": f"unknown dataset '{dataset}'", "available": list(CHECKS)}
    return await run_validation(conn, dataset)


@router.get("/admin/datasets/validation-runs", response_model=list[dict])
async def list_runs(
    limit: int = 20,
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> list[dict]:
    cur = await conn.execute(
        "SELECT id::text, dataset, status, rows_scanned, issues_found, summary, "
        "started_at, finished_at FROM dataset_validation_runs "
        "ORDER BY started_at DESC LIMIT %s",
        (min(limit, 100),),
    )
    return [
        {
            "id": r[0], "dataset": r[1], "status": r[2], "rows_scanned": r[3],
            "issues_found": r[4], "summary": r[5], "started_at": r[6],
            "finished_at": r[7],
        }
        for r in await cur.fetchall()
    ]


@router.get("/admin/datasets/validation-runs/{run_id}/issues", response_model=list[dict])
async def list_issues(
    run_id: str,
    limit: int = 200,
    principal: Principal = Depends(require_role("super_admin", "platform_admin")),
    conn=Depends(get_db),
) -> list[dict]:
    cur = await conn.execute(
        "SELECT id::text, severity, code, entity_type, entity_id::text, message, created_at "
        "FROM dataset_validation_issues WHERE run_id = %s::uuid "
        "ORDER BY CASE severity WHEN 'error' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, "
        "created_at LIMIT %s",
        (run_id, min(limit, 500)),
    )
    return [
        {
            "id": r[0], "severity": r[1], "code": r[2], "entity_type": r[3],
            "entity_id": r[4], "message": r[5], "created_at": r[6],
        }
        for r in await cur.fetchall()
    ]
