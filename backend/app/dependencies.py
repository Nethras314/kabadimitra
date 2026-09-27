"""Authorization and organization-isolation helpers."""

from fastapi import Depends, HTTPException, status

from .auth import Principal, get_principal


def require_role(*codes: str):
    """Dependency factory: grant access only if the principal has a given role."""

    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_role(*codes):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return principal

    return _dep


def org_scope(principal: Principal) -> tuple[str, list]:
    """Return (where_clause, params) that scopes a query to the principal's org.

    - platform_admin sees everything (no filter).
    - a user with an organization sees only their organization's rows.
    - a user with no organization and no admin role sees nothing.
    """
    if "platform_admin" in principal.roles:
        return "TRUE", []
    if principal.organization_id:
        return "organization_id = %s", [principal.organization_id]
    return "FALSE", []
