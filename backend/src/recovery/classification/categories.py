"""Error category definitions and classification types."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Extended error categories for classification."""

    # Network related
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_CONNECTION = "network_connection"
    NETWORK_DNS = "network_dns"
    NETWORK_SSL = "network_ssl"

    # Resource related
    RESOURCE_DISK = "resource_disk"
    RESOURCE_MEMORY = "resource_memory"
    RESOURCE_CPU = "resource_cpu"
    RESOURCE_QUOTA = "resource_quota"

    # Permission related
    PERMISSION_FILE = "permission_file"
    PERMISSION_API = "permission_api"
    PERMISSION_AUTH = "permission_auth"

    # Validation related
    VALIDATION_SCHEMA = "validation_schema"
    VALIDATION_DATA = "validation_data"
    VALIDATION_FORMAT = "validation_format"

    # Service related
    SERVICE_UNAVAILABLE = "service_unavailable"
    SERVICE_RATE_LIMIT = "service_rate_limit"
    SERVICE_MAINTENANCE = "service_maintenance"

    # System related
    SYSTEM_DEPENDENCY = "system_dependency"
    SYSTEM_CONFIGURATION = "system_configuration"
    SYSTEM_CORRUPTION = "system_corruption"

    # Unknown
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoverabilityScore(Enum):
    """How likely an error is to be recoverable."""

    ALWAYS = 1.0  # Always recoverable with retry
    LIKELY = 0.8  # Usually recoverable
    POSSIBLE = 0.5  # Sometimes recoverable
    UNLIKELY = 0.2  # Rarely recoverable
    NEVER = 0.0  # Never recoverable


@dataclass
class ErrorPattern:
    """Pattern definition for matching errors."""

    category: ErrorCategory
    indicators: list[str]  # Keywords/patterns to match
    exception_types: list[type]  # Exception types to match
    error_codes: list[str]  # HTTP/system error codes
    severity: ErrorSeverity
    recoverability: RecoverabilityScore
    context_keys: list[str]  # Required context keys for classification

    def matches(self, error: Exception, context: dict[str, Any] | None = None) -> float:
        """Calculate match score for error (0.0 to 1.0)."""
        score = 0.0
        factors = 0

        # Check exception type
        if type(error) in self.exception_types:
            score += 1.0
            factors += 1

        # Check error message indicators
        error_str = str(error).lower()
        matched_indicators = sum(1 for ind in self.indicators if ind.lower() in error_str)
        if self.indicators:
            score += matched_indicators / len(self.indicators)
            factors += 1

        # Check error codes if available
        if hasattr(error, 'code') and self.error_codes:
            if str(error.code) in self.error_codes:
                score += 1.0
            factors += 1

        # Check required context keys
        if self.context_keys and context:
            matched_keys = sum(1 for key in self.context_keys if key in context)
            score += matched_keys / len(self.context_keys)
            factors += 1

        return score / factors if factors > 0 else 0.0


@dataclass
class ErrorClassification:
    """Result of error classification."""

    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    recoverability: RecoverabilityScore
    confidence: float  # 0.0 to 1.0
    matched_pattern: ErrorPattern | None
    context: dict[str, Any]
    timestamp: datetime

    @property
    def is_recoverable(self) -> bool:
        """Check if error is considered recoverable."""
        return self.recoverability.value > 0.5

    @property
    def is_transient(self) -> bool:
        """Check if error is likely transient."""
        transient_categories = {
            ErrorCategory.NETWORK_TIMEOUT,
            ErrorCategory.NETWORK_CONNECTION,
            ErrorCategory.SERVICE_UNAVAILABLE,
            ErrorCategory.SERVICE_RATE_LIMIT,
            ErrorCategory.RESOURCE_CPU,
            ErrorCategory.RESOURCE_MEMORY,
        }
        return self.category in transient_categories

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverability": self.recoverability.value,
            "confidence": self.confidence,
            "is_recoverable": self.is_recoverable,
            "is_transient": self.is_transient,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }
