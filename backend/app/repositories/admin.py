"""Administrative data access (recycler verification, disputes, AI/price review,
user support, audit)."""

from abc import ABC, abstractmethod
from datetime import date, timedelta

from ..models.audit import AuditEvent
from ..models.recycler import AuthorizationRecord


class AdminRepository(ABC):
    @abstractmethod
    async def set_authorization_status(self, recycler_id: str, status: str) -> None: ...

    @abstractmethod
    async def list_authorizations_expiring(
        self, days: int
    ) -> list[tuple[str, AuthorizationRecord]]: ...

    @abstractmethod
    async def resolve_dispute(self, dispute_id: str, resolution: str) -> None: ...

    @abstractmethod
    async def review_ai_decision(self, decision_id: str, corrected_category_id: str) -> None: ...

    @abstractmethod
    async def review_price_observation(
        self, observation_id: str, verification_status: str
    ) -> None: ...

    @abstractmethod
    async def set_user_status(self, user_id: str, status: str) -> None: ...

    @abstractmethod
    async def audit_log(self, entity_id: str | None = None) -> list[AuditEvent]: ...


class InMemoryAdminRepository(AdminRepository):
    def __init__(self, today: date | None = None) -> None:
        self.today = today or date.today()
        self._authorizations: dict[str, list[AuthorizationRecord]] = {}
        self._disputes: dict[str, dict] = {}
        self._ai_decisions: dict[str, dict] = {}
        self._price_observations: dict[str, dict] = {}
        self._users: dict[str, str] = {}
        self._audit: list[AuditEvent] = []

    # --- seed helpers ---
    def seed_authorization(self, recycler_id: str, auth: AuthorizationRecord) -> None:
        self._authorizations.setdefault(recycler_id, []).append(auth)

    def seed_dispute(self, dispute_id: str) -> None:
        self._disputes[dispute_id] = {"status": "open", "resolution": None}

    def seed_ai_decision(self, decision_id: str) -> None:
        self._ai_decisions[decision_id] = {"corrected_category_id": None}

    def seed_price_observation(self, observation_id: str) -> None:
        self._price_observations[observation_id] = {"verification_status": "unverified"}

    def seed_user(self, user_id: str, status: str = "active") -> None:
        self._users[user_id] = status

    def seed_audit(self, event: AuditEvent) -> None:
        self._audit.append(event)

    # --- operations ---
    async def set_authorization_status(self, recycler_id: str, status: str) -> None:
        for auth in self._authorizations.get(recycler_id, []):
            auth.status = status

    async def list_authorizations_expiring(
        self, days: int
    ) -> list[tuple[str, AuthorizationRecord]]:
        result = []
        horizon = self.today + timedelta(days=days)
        for recycler_id, auths in self._authorizations.items():
            for auth in auths:
                if auth.expiry_date is None:
                    continue
                if auth.status == "expired" or auth.expiry_date <= horizon:
                    result.append((recycler_id, auth))
        return result

    async def resolve_dispute(self, dispute_id: str, resolution: str) -> None:
        self._disputes[dispute_id]["status"] = "resolved"
        self._disputes[dispute_id]["resolution"] = resolution

    async def review_ai_decision(self, decision_id: str, corrected_category_id: str) -> None:
        self._ai_decisions[decision_id]["corrected_category_id"] = corrected_category_id

    async def review_price_observation(self, observation_id: str, verification_status: str) -> None:
        self._price_observations[observation_id]["verification_status"] = verification_status

    async def set_user_status(self, user_id: str, status: str) -> None:
        self._users[user_id] = status

    async def audit_log(self, entity_id: str | None = None) -> list[AuditEvent]:
        if entity_id is None:
            return list(self._audit)
        return [a for a in self._audit if a.entity_id == entity_id]

    # --- test helpers ---
    def authorization_status(self, recycler_id: str) -> list[str]:
        return [a.status for a in self._authorizations.get(recycler_id, [])]

    def dispute_status(self, dispute_id: str) -> str:
        return self._disputes[dispute_id]["status"]

    def ai_correction(self, decision_id: str) -> str | None:
        return self._ai_decisions[decision_id]["corrected_category_id"]

    def observation_status(self, observation_id: str) -> str:
        return self._price_observations[observation_id]["verification_status"]

    def user_status(self, user_id: str) -> str:
        return self._users[user_id]
