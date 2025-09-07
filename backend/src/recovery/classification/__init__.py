"""Error classification system for recovery."""
from .categories import (
    ErrorCategory,
    ErrorClassification,
    ErrorPattern,
    ErrorSeverity,
    RecoverabilityScore,
)
from .classifier import ErrorClassifier
from .strategies import RecoveryApproach, StrategyMapper

__all__ = [
    "ErrorClassifier",
    "ErrorCategory",
    "ErrorPattern",
    "ErrorClassification",
    "ErrorSeverity",
    "RecoverabilityScore",
    "StrategyMapper",
    "RecoveryApproach",
]

