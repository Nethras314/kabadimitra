import asyncio

import pytest

from app.core.errors import ServiceUnavailableError
from app.services.health import HealthService


def test_liveness_returns_ok():
    assert HealthService().liveness() == {"status": "ok", "service": "Kabadi Mitra API"}


def test_readiness_raises_without_repository():
    with pytest.raises(ServiceUnavailableError):
        asyncio.run(HealthService().readiness())
