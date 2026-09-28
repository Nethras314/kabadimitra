import asyncio
from datetime import date

import pytest

from app.core.errors import ForbiddenError
from app.core.security import Principal
from app.models.audit import AuditEvent
from app.models.recycler import AuthorizationRecord
from app.repositories.admin import InMemoryAdminRepository
from app.services.admin import AdminService


def run(coro):
    return asyncio.run(coro)


def principal(*roles):
    return Principal(sub="s", roles=list(roles))


def make():
    repo = InMemoryAdminRepository(today=date(2026, 9, 28))
    return repo, AdminService(repo)


def test_verify_recycler_super_admin():
    repo, svc = make()
    repo.seed_authorization("r-1", AuthorizationRecord(status="pending", expiry_date=date(2026, 10, 1)))
    assert run(svc.verify_recycler(principal("super_admin"), "r-1")) == {"status": "verified"}
    assert repo.authorization_status("r-1") == ["verified"]


def test_verify_recycler_forbidden_for_support():
    repo, svc = make()
    repo.seed_authorization("r-1", AuthorizationRecord(status="pending"))
    with pytest.raises(ForbiddenError):
        run(svc.verify_recycler(principal("support"), "r-1"))


def test_expiring_authorizations():
    repo, svc = make()
    repo.seed_authorization("r-1", AuthorizationRecord(status="verified", expiry_date=date(2026, 10, 5)))
    repo.seed_authorization("r-2", AuthorizationRecord(status="verified", expiry_date=date(2027, 1, 1)))
    repo.seed_authorization("r-3", AuthorizationRecord(status="expired", expiry_date=date(2026, 9, 1)))

    rows = run(svc.expiring_authorizations(principal("operations_admin"), days=30))
    ids = {r["recycler_id"] for r in rows}
    assert "r-1" in ids
    assert "r-3" in ids
    assert "r-2" not in ids


def test_review_dispute_support_allowed():
    repo, svc = make()
    repo.seed_dispute("d-1")
    assert run(svc.review_dispute(principal("support"), "d-1", "resolved")) == {"status": "resolved"}
    assert repo.dispute_status("d-1") == "resolved"


def test_review_ai_decision_data_admin_allowed():
    repo, svc = make()
    repo.seed_ai_decision("a-1")
    assert run(svc.review_ai_decision(principal("data_ai_admin"), "a-1", "PCB")) == {"status": "reviewed"}
    assert repo.ai_correction("a-1") == "PCB"


def test_review_ai_decision_operations_admin_forbidden():
    repo, svc = make()
    repo.seed_ai_decision("a-1")
    with pytest.raises(ForbiddenError):
        run(svc.review_ai_decision(principal("operations_admin"), "a-1", "PCB"))


def test_review_price_observation():
    repo, svc = make()
    repo.seed_price_observation("p-1")
    assert run(svc.review_price_observation(principal("data_ai_admin"), "p-1", "verified")) == {
        "verification_status": "verified"
    }
    assert repo.observation_status("p-1") == "verified"


def test_support_user_suspends():
    repo, svc = make()
    repo.seed_user("u-1", "active")
    assert run(svc.support_user(principal("support"), "u-1", "suspended")) == {"status": "suspended"}
    assert repo.user_status("u-1") == "suspended"


def test_audit_log_super_admin_only():
    repo, svc = make()
    repo.seed_audit(AuditEvent(action="transaction.created", entity_id="t-1"))
    logs = run(svc.audit_log(principal("super_admin")))
    assert len(logs) == 1
    assert logs[0]["action"] == "transaction.created"

    with pytest.raises(ForbiddenError):
        run(svc.audit_log(principal("operations_admin")))
