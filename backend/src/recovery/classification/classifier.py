"""Main error classifier implementation."""
import logging
from datetime import UTC, datetime
from typing import Any

from ..types import RecoveryStrategy
from .categories import (
    ErrorCategory,
    ErrorClassification,
    ErrorPattern,
    ErrorSeverity,
    RecoverabilityScore,
)
from .patterns import ALL_PATTERNS, get_custom_patterns
from .strategies import StrategyConfig, StrategyMapper

logger = logging.getLogger(__name__)


class ErrorClassifier:
    """Classifies errors and maps them to recovery strategies."""

    def __init__(
        self,
        custom_patterns: list[ErrorPattern] | None = None,
        custom_strategies: dict[ErrorCategory, StrategyConfig] | None = None,
        confidence_threshold: float = 0.6
    ):
        """Initialize classifier with patterns and strategies.
        
        Args:
            custom_patterns: Additional patterns to use for classification
            custom_strategies: Custom strategy mappings
            confidence_threshold: Minimum confidence for classification (0.0-1.0)

        """
        self.patterns = ALL_PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)
        self.patterns.extend(get_custom_patterns())

        self.strategy_mapper = StrategyMapper(custom_strategies)
        self.confidence_threshold = confidence_threshold
        self._classification_cache: dict[str, ErrorClassification] = {}

    def classify(
        self,
        error: Exception,
        context: dict[str, Any] | None = None
    ) -> ErrorClassification:
        """Classify an error based on patterns.
        
        Args:
            error: The exception to classify
            context: Additional context for classification
            
        Returns:
            Error classification with category, severity, etc.

        """
        # Check cache first
        cache_key = f"{type(error).__name__}:{str(error)}"
        if cache_key in self._classification_cache:
            cached = self._classification_cache[cache_key]
            # Update context and timestamp
            cached.context = context or {}
            cached.timestamp = datetime.now(UTC)
            return cached

        # Find best matching pattern
        best_match: tuple[ErrorPattern, float] | None = None

        for pattern in self.patterns:
            score = pattern.matches(error, context)
            if score > 0 and (best_match is None or score > best_match[1]):
                best_match = (pattern, score)

        # Create classification
        if best_match and best_match[1] >= self.confidence_threshold:
            pattern, confidence = best_match
            classification = ErrorClassification(
                error=error,
                category=pattern.category,
                severity=pattern.severity,
                recoverability=pattern.recoverability,
                confidence=confidence,
                matched_pattern=pattern,
                context=context or {},
                timestamp=datetime.now(UTC)
            )
        else:
            # Default classification for unknown errors
            classification = ErrorClassification(
                error=error,
                category=ErrorCategory.UNKNOWN,
                severity=self._estimate_severity(error),
                recoverability=RecoverabilityScore.POSSIBLE,
                confidence=0.0,
                matched_pattern=None,
                context=context or {},
                timestamp=datetime.now(UTC)
            )

        # Cache the classification
        self._classification_cache[cache_key] = classification

        # Log classification
        logger.debug(
            f"Classified error '{type(error).__name__}' as {classification.category.value} "
            f"with confidence {classification.confidence:.2f}"
        )

        return classification

    def get_recovery_strategy(
        self,
        classification: ErrorClassification
    ) -> tuple[RecoveryStrategy | None, StrategyConfig]:
        """Get recovery strategy for a classification.
        
        Args:
            classification: Error classification
            
        Returns:
            Tuple of (strategy instance, strategy config)

        """
        config = self.strategy_mapper.get_strategy_config(
            classification.category,
            classification.severity,
            classification.recoverability
        )

        strategy = self.strategy_mapper.create_strategy(config)

        return strategy, config

    def should_retry(self, classification: ErrorClassification) -> bool:
        """Determine if an error should be retried based on classification."""
        return classification.is_recoverable and classification.is_transient

    def add_pattern(self, pattern: ErrorPattern) -> None:
        """Add a custom pattern to the classifier."""
        self.patterns.append(pattern)
        # Clear cache when patterns change
        self._classification_cache.clear()

    def clear_cache(self) -> None:
        """Clear the classification cache."""
        self._classification_cache.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Get classification statistics."""
        category_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}
        recoverable_count = 0

        for classification in self._classification_cache.values():
            category = classification.category.value
            severity = classification.severity.value

            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            if classification.is_recoverable:
                recoverable_count += 1

        total = len(self._classification_cache)

        return {
            "total_classifications": total,
            "unique_errors": total,
            "by_category": category_counts,
            "by_severity": severity_counts,
            "recoverable_errors": recoverable_count,
            "recovery_rate": recoverable_count / total if total > 0 else 0.0,
            "patterns_loaded": len(self.patterns),
            "cache_size": total
        }

    def _estimate_severity(self, error: Exception) -> ErrorSeverity:
        """Estimate severity for unknown errors."""
        # Critical errors
        critical_types = {SystemExit, KeyboardInterrupt, MemoryError}
        if type(error) in critical_types:
            return ErrorSeverity.CRITICAL

        # High severity errors
        high_types = {OSError, IOError, RuntimeError}
        if type(error) in high_types:
            return ErrorSeverity.HIGH

        # Medium severity errors
        medium_types = {ValueError, TypeError, KeyError}
        if type(error) in medium_types:
            return ErrorSeverity.MEDIUM

        # Default to low
        return ErrorSeverity.LOW
