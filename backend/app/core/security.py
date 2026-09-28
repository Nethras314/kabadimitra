"""Authentication context, RBAC, and organization isolation.

The identity provider is Supabase Auth (JWT verified against JWKS); the legacy
``app/auth.py`` performs the token verification and will migrate here. This
module defines the ``Principal`` and the authorization helpers that consume an
already-verified identity.
"""

from dataclasses import dataclass, field

from ..models.role import ADMIN_ROLES, Role, effective_roles
from .errors import ForbiddenError


@dataclass
class Principal:
    sub: str
    user_id: str | None = None
    roles: list[str] = field(default_factory=list)
    organization_id: str | None = None
    preferred_locale: str = "en"

    def effective_roles(self) -> set[str]:
        return effective_roles(self.roles)

    def has_role(self, *codes: str) -> bool:
        return bool(self.effective_roles() & set(codes))

    def is_admin(self) -> bool:
        return bool(self.effective_roles() & {r.value for r in ADMIN_ROLES})


def principal_from_claims(
    claims: dict,
    roles: list[str],
    organization_id: str | None = None,
) -> Principal:
    sub = claims.get("sub", "")
    return Principal(
        sub=sub,
        user_id=sub,
        roles=roles,
        organization_id=organization_id,
        preferred_locale=claims.get("preferred_locale", "en"),
    )


def require_role(*codes: str):
    """Dependency/check factory: raise 403 unless the principal holds a role."""

    def _check(principal: Principal) -> Principal:
        if not principal.has_role(*codes):
            raise ForbiddenError("Insufficient permissions")
        return principal

    return _check


def org_scope(principal: Principal) -> tuple[str, list]:
    """Return a SQL filter scoping rows to the principal's organization.

    - super_admin sees everything (no filter).
    - a user with an organization sees only their organization's rows.
    - a user with no organization and no super role sees nothing.
    """
    if principal.has_role(Role.SUPER_ADMIN.value):
        return "TRUE", []
    if principal.organization_id:
        return "organization_id = %s", [principal.organization_id]
    return "FALSE", []
