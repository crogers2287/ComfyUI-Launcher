"""Recovery strategy mapping based on error classification."""
from dataclasses import dataclass
from enum import Enum

from ..strategies import ExponentialBackoffStrategy, FixedDelayStrategy, LinearBackoffStrategy
from ..types import RecoveryStrategy
from .categories import ErrorCategory, ErrorSeverity, RecoverabilityScore


class RecoveryApproach(Enum):
    """Recovery approach types."""

    IMMEDIATE = "immediate"  # Retry immediately
    EXPONENTIAL = "exponential"  # Exponential backoff
    LINEAR = "linear"  # Linear backoff
    FIXED = "fixed"  # Fixed delay
    CIRCUIT_BREAKER = "circuit_breaker"  # Use circuit breaker
    NO_RETRY = "no_retry"  # Don't retry


@dataclass
class StrategyConfig:
    """Configuration for a recovery strategy."""

    approach: RecoveryApproach
    max_retries: int
    initial_delay: float
    max_delay: float
    backoff_factor: float = 2.0
    jitter: bool = True


class StrategyMapper:
    """Maps error classifications to recovery strategies."""

    # Default strategy configurations by category
    DEFAULT_STRATEGIES: dict[ErrorCategory, StrategyConfig] = {
        # Network errors - aggressive retry with exponential backoff
        ErrorCategory.NETWORK_TIMEOUT: StrategyConfig(
            approach=RecoveryApproach.EXPONENTIAL,
            max_retries=5,
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            jitter=True
        ),
        ErrorCategory.NETWORK_CONNECTION: StrategyConfig(
            approach=RecoveryApproach.EXPONENTIAL,
            max_retries=4,
            initial_delay=2.0,
            max_delay=30.0,
            backoff_factor=2.0,
            jitter=True
        ),
        ErrorCategory.NETWORK_DNS: StrategyConfig(
            approach=RecoveryApproach.LINEAR,
            max_retries=3,
            initial_delay=5.0,
            max_delay=15.0,
            backoff_factor=1.0
        ),
        ErrorCategory.NETWORK_SSL: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),

        # Resource errors - careful retry
        ErrorCategory.RESOURCE_DISK: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),
        ErrorCategory.RESOURCE_MEMORY: StrategyConfig(
            approach=RecoveryApproach.EXPONENTIAL,
            max_retries=2,
            initial_delay=5.0,
            max_delay=30.0,
            backoff_factor=3.0
        ),
        ErrorCategory.RESOURCE_QUOTA: StrategyConfig(
            approach=RecoveryApproach.EXPONENTIAL,
            max_retries=10,
            initial_delay=60.0,
            max_delay=3600.0,
            backoff_factor=2.0
        ),

        # Permission errors - no retry
        ErrorCategory.PERMISSION_FILE: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),
        ErrorCategory.PERMISSION_API: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),

        # Validation errors - no retry
        ErrorCategory.VALIDATION_SCHEMA: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),
        ErrorCategory.VALIDATION_DATA: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),

        # Service errors - aggressive retry
        ErrorCategory.SERVICE_UNAVAILABLE: StrategyConfig(
            approach=RecoveryApproach.EXPONENTIAL,
            max_retries=6,
            initial_delay=5.0,
            max_delay=300.0,
            backoff_factor=2.0,
            jitter=True
        ),
        ErrorCategory.SERVICE_RATE_LIMIT: StrategyConfig(
            approach=RecoveryApproach.FIXED,
            max_retries=20,
            initial_delay=60.0,
            max_delay=60.0
        ),

        # System errors - mostly no retry
        ErrorCategory.SYSTEM_DEPENDENCY: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),
        ErrorCategory.SYSTEM_CONFIGURATION: StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        ),

        # Unknown - conservative retry
        ErrorCategory.UNKNOWN: StrategyConfig(
            approach=RecoveryApproach.EXPONENTIAL,
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0
        ),
    }

    def __init__(self, custom_strategies: dict[ErrorCategory, StrategyConfig] | None = None):
        """Initialize with optional custom strategy mappings."""
        self.strategies = self.DEFAULT_STRATEGIES.copy()
        if custom_strategies:
            self.strategies.update(custom_strategies)

    def get_strategy_config(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        recoverability: RecoverabilityScore
    ) -> StrategyConfig:
        """Get strategy configuration for error classification."""
        # Get base strategy for category
        base_config = self.strategies.get(category, self.strategies[ErrorCategory.UNKNOWN])

        # Adjust based on severity and recoverability
        if recoverability == RecoverabilityScore.NEVER:
            return StrategyConfig(
                approach=RecoveryApproach.NO_RETRY,
                max_retries=0,
                initial_delay=0.0,
                max_delay=0.0
            )

        # Reduce retries for critical errors
        if severity == ErrorSeverity.CRITICAL:
            base_config.max_retries = max(1, base_config.max_retries // 2)

        # Increase retries for highly recoverable errors
        if recoverability == RecoverabilityScore.ALWAYS:
            base_config.max_retries = min(10, base_config.max_retries * 2)

        return base_config

    def create_strategy(self, config: StrategyConfig) -> RecoveryStrategy | None:
        """Create actual strategy instance from configuration."""
        if config.approach == RecoveryApproach.NO_RETRY:
            return None

        if config.approach == RecoveryApproach.EXPONENTIAL:
            return ExponentialBackoffStrategy(
                initial_delay=config.initial_delay,
                max_delay=config.max_delay,
                backoff_factor=config.backoff_factor,
                jitter=config.jitter
            )

        if config.approach == RecoveryApproach.LINEAR:
            return LinearBackoffStrategy(
                initial_delay=config.initial_delay,
                increment=config.initial_delay,
                max_delay=config.max_delay
            )

        if config.approach == RecoveryApproach.FIXED:
            return FixedDelayStrategy(delay=config.initial_delay)

        # Default to exponential
        return ExponentialBackoffStrategy(
            initial_delay=config.initial_delay,
            max_delay=config.max_delay,
            backoff_factor=config.backoff_factor
        )
