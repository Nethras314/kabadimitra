from datetime import date, timedelta

from app.models.recycler import AuthorizationRecord, effective_authorization


def test_verified_non_expired_authorized():
    future = date.today() + timedelta(days=30)
    status, authorized = effective_authorization(
        [AuthorizationRecord(status="verified", expiry_date=future)]
    )
    assert status == "verified"
    assert authorized is True


def test_verified_without_expiry_authorized():
    status, authorized = effective_authorization(
        [AuthorizationRecord(status="verified", expiry_date=None)]
    )
    assert status == "verified"
    assert authorized is True


def test_expired_not_authorized():
    past = date.today() - timedelta(days=1)
    status, authorized = effective_authorization(
        [AuthorizationRecord(status="verified", expiry_date=past)]
    )
    assert status == "expired"
    assert authorized is False


def test_suspended_not_authorized():
    future = date.today() + timedelta(days=30)
    status, authorized = effective_authorization(
        [AuthorizationRecord(status="suspended", expiry_date=future)]
    )
    assert status == "suspended"
    assert authorized is False


def test_no_authorization_not_authorized():
    status, authorized = effective_authorization([])
    assert status == "pending"
    assert authorized is False


def test_pending_not_authorized():
    status, authorized = effective_authorization(
        [AuthorizationRecord(status="pending", expiry_date=None)]
    )
    assert status == "pending"
    assert authorized is False
