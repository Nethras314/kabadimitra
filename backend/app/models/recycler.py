"""Recycler verification domain types and rules."""

from dataclasses import dataclass
from datetime import date


@dataclass
class AuthorizationRecord:
    status: str  # verified | pending | expiring | expired | suspended
    expiry_date: date | None = None


def effective_authorization(
    authorizations: list[AuthorizationRecord], today: date | None = None
) -> tuple[str, bool]:
    """Return (effective_status, authorized).

    Only a ``verified`` authorization that has not expired makes a recycler
    eligible for matching. Suspended or expired authorizations exclude it
    (FR-VERIF-01/FR-VERIF-04).
    """
    today = today or date.today()

    if not authorizations:
        return ("pending", False)

    if any(a.status == "suspended" for a in authorizations):
        return ("suspended", False)

    for authorization in authorizations:
        if authorization.status == "verified" and (
            authorization.expiry_date is None or authorization.expiry_date >= today
        ):
            return ("verified", True)

    if any(a.status == "verified" for a in authorizations):
        return ("expired", False)

    return ("pending", False)
