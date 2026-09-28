"""Pluggable AI classification (assistive, never authoritative)."""

from . import reference  # noqa: F401  (registers the reference provider)
from .provider import (
    AlternativePrediction,
    BaseProvider,
    ClassificationResult,
    ConfidenceTier,
    NullProvider,
    confidence_tier,
    get_provider,
    register_provider,
)

__all__ = [
    "AlternativePrediction",
    "BaseProvider",
    "ClassificationResult",
    "ConfidenceTier",
    "NullProvider",
    "confidence_tier",
    "get_provider",
    "register_provider",
]
