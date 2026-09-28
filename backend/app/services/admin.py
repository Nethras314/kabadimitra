"""Administrative service with role-gated operations."""

from ..core.errors import ForbiddenError
from ..core.security import Principal
from ..models.role import Role
from ..repositories.admin import AdminRepository


class AdminService:
    def __init__(self, repository: AdminRepository) -> None:
        self._repo = repository

    async def verify_recycler(
        self, principal: Principal, recycler_id: str, status: str = "verified"
    ) -> dict:
        self._require(principal, Role.SUPER_ADMIN, Role.OPERATIONS_ADMIN)
        await self._repo.set_authorization_status(recycler_id, status)
        return {"status": status}

    async def expiring_authorizations(self, principal: Principal, days: int = 30) -> list[dict]:
        self._require(principal, Role.SUPER_ADMIN, Role.OPERATIONS_ADMIN)
        rows = await self._repo.list_authorizations_expiring(days)
        return [
            {"recycler_id": rid, "status": auth.status, "expiry_date": str(auth.expiry_date)}
            for rid, auth in rows
        ]

    async def review_dispute(self, principal: Principal, dispute_id: str, resolution: str) -> dict:
        self._require(principal, Role.SUPER_ADMIN, Role.OPERATIONS_ADMIN, Role.SUPPORT)
        await self._repo.resolve_dispute(dispute_id, resolution)
        return {"status": "resolved"}

    async def review_ai_decision(
        self, principal: Principal, decision_id: str, corrected_category_id: str
    ) -> dict:
        self._require(principal, Role.SUPER_ADMIN, Role.DATA_AI_ADMIN)
        await self._repo.review_ai_decision(decision_id, corrected_category_id)
        return {"status": "reviewed"}

    async def review_price_observation(
        self, principal: Principal, observation_id: str, verification_status: str
    ) -> dict:
        self._require(principal, Role.SUPER_ADMIN, Role.DATA_AI_ADMIN, Role.OPERATIONS_ADMIN)
        await self._repo.review_price_observation(observation_id, verification_status)
        return {"verification_status": verification_status}

    async def support_user(self, principal: Principal, user_id: str, status: str) -> dict:
        self._require(principal, Role.SUPER_ADMIN, Role.OPERATIONS_ADMIN, Role.SUPPORT)
        await self._repo.set_user_status(user_id, status)
        return {"status": status}

    async def audit_log(self, principal: Principal, entity_id: str | None = None) -> list[dict]:
        self._require(principal, Role.SUPER_ADMIN)
        events = await self._repo.audit_log(entity_id)
        return [
            {
                "id": e.id,
                "action": e.action,
                "actor_user_id": e.actor_user_id,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
            }
            for e in events
        ]

    @staticmethod
    def _require(principal: Principal, *roles: Role) -> None:
        if not principal.has_role(*(r.value for r in roles)):
            raise ForbiddenError("Insufficient permissions")
