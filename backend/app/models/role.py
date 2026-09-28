"""Role model and hierarchy."""

from enum import StrEnum


class Role(StrEnum):
    COLLECTOR = "collector"
    KABADIWALA = "kabadiwala"
    AGGREGATOR = "aggregator"
    RECYCLER = "recycler"
    DISMANTLER = "dismantler"
    SUPPORT = "support"
    OPERATIONS_ADMIN = "operations_admin"
    DATA_AI_ADMIN = "data_ai_admin"
    SUPER_ADMIN = "super_admin"


FIELD_ROLES = frozenset(
    {Role.COLLECTOR, Role.KABADIWALA, Role.AGGREGATOR, Role.RECYCLER, Role.DISMANTLER}
)
ADMIN_ROLES = frozenset(
    {Role.SUPPORT, Role.OPERATIONS_ADMIN, Role.DATA_AI_ADMIN, Role.SUPER_ADMIN}
)

# Which roles each role implies (including itself). Super admin implies all
# admin roles; operations/data admins imply support.
ROLE_IMPLIES: dict[Role, frozenset[Role]] = {
    Role.SUPER_ADMIN: frozenset(
        {Role.SUPER_ADMIN, Role.OPERATIONS_ADMIN, Role.DATA_AI_ADMIN, Role.SUPPORT}
    ),
    Role.OPERATIONS_ADMIN: frozenset({Role.OPERATIONS_ADMIN, Role.SUPPORT}),
    Role.DATA_AI_ADMIN: frozenset({Role.DATA_AI_ADMIN, Role.SUPPORT}),
    Role.SUPPORT: frozenset({Role.SUPPORT}),
    Role.COLLECTOR: frozenset({Role.COLLECTOR}),
    Role.KABADIWALA: frozenset({Role.KABADIWALA}),
    Role.AGGREGATOR: frozenset({Role.AGGREGATOR}),
    Role.RECYCLER: frozenset({Role.RECYCLER}),
    Role.DISMANTLER: frozenset({Role.DISMANTLER}),
}


def effective_roles(roles: list[str] | set[str]) -> set[str]:
    """Expand a set of role codes to include all implied roles."""
    result = set(roles)
    for role in list(roles):
        try:
            implied = ROLE_IMPLIES[Role(role)]
        except ValueError:
            continue
        result |= {r.value for r in implied}
    return result
