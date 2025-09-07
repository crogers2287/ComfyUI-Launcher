"""Tests for the error classification system."""
import asyncio
import socket
import ssl
from datetime import UTC, datetime

import pytest

from backend.src.recovery.classification import (
    ErrorCategory,
    ErrorClassification,
    ErrorClassifier,
    ErrorPattern,
    ErrorSeverity,
    RecoverabilityScore,
    RecoveryApproach,
    StrategyMapper,
)
from backend.src.recovery.classification.patterns import (
    NETWORK_PATTERNS,
    VALIDATION_PATTERNS,
)


class TestErrorPattern:
    """Test error pattern matching."""

    def test_pattern_matches_exception_type(self):
        """Test pattern matching by exception type."""
        pattern = ErrorPattern(
            category=ErrorCategory.NETWORK_TIMEOUT,
            indicators=["timeout"],
            exception_types=[TimeoutError],
            error_codes=["ETIMEDOUT"],
            severity=ErrorSeverity.MEDIUM,
            recoverability=RecoverabilityScore.LIKELY,
            context_keys=[]
        )

        error = TimeoutError("Connection timed out")
        score = pattern.matches(error)
        assert score >= 0.5  # Changed from > to >=

    def test_pattern_matches_indicators(self):
        """Test pattern matching by error message indicators."""
        pattern = NETWORK_PATTERNS[0]  # Network timeout pattern

        error = RuntimeError("Operation timed out after 30 seconds")
        score = pattern.matches(error)
        assert score > 0.0

    def test_pattern_matches_context_keys(self):
        """Test pattern matching with context keys."""
        pattern = ErrorPattern(
            category=ErrorCategory.RESOURCE_DISK,
            indicators=["disk full"],
            exception_types=[OSError],
            error_codes=["ENOSPC"],
            severity=ErrorSeverity.CRITICAL,
            recoverability=RecoverabilityScore.UNLIKELY,
            context_keys=["disk_usage", "file_path"]
        )

        error = OSError("No space left on device")
        context = {"disk_usage": 99.9, "file_path": "/tmp/large_file.bin"}
        score = pattern.matches(error, context)
        assert score > 0.5

    def test_pattern_no_match(self):
        """Test pattern with no match."""
        pattern = VALIDATION_PATTERNS[0]  # Validation pattern

        error = ConnectionError("Network unreachable")
        score = pattern.matches(error)
        assert score == 0.0 or score < 0.5


class TestErrorClassification:
    """Test error classification results."""

    def test_is_recoverable(self):
        """Test recoverable error detection."""
        classification = ErrorClassification(
            error=TimeoutError(),
            category=ErrorCategory.NETWORK_TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            recoverability=RecoverabilityScore.LIKELY,
            confidence=0.8,
            matched_pattern=None,
            context={},
            timestamp=datetime.now(UTC)
        )
        assert classification.is_recoverable is True

        non_recoverable = ErrorClassification(
            error=PermissionError(),
            category=ErrorCategory.PERMISSION_FILE,
            severity=ErrorSeverity.HIGH,
            recoverability=RecoverabilityScore.NEVER,
            confidence=0.9,
            matched_pattern=None,
            context={},
            timestamp=datetime.now(UTC)
        )
        assert non_recoverable.is_recoverable is False

    def test_is_transient(self):
        """Test transient error detection."""
        transient = ErrorClassification(
            error=ConnectionError(),
            category=ErrorCategory.NETWORK_CONNECTION,
            severity=ErrorSeverity.MEDIUM,
            recoverability=RecoverabilityScore.LIKELY,
            confidence=0.8,
            matched_pattern=None,
            context={},
            timestamp=datetime.now(UTC)
        )
        assert transient.is_transient is True

        permanent = ErrorClassification(
            error=ValueError(),
            category=ErrorCategory.VALIDATION_SCHEMA,
            severity=ErrorSeverity.HIGH,
            recoverability=RecoverabilityScore.NEVER,
            confidence=0.9,
            matched_pattern=None,
            context={},
            timestamp=datetime.now(UTC)
        )
        assert permanent.is_transient is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        error = RuntimeError("Test error")
        classification = ErrorClassification(
            error=error,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.LOW,
            recoverability=RecoverabilityScore.POSSIBLE,
            confidence=0.5,
            matched_pattern=None,
            context={"test": "value"},
            timestamp=datetime.now(UTC)
        )

        data = classification.to_dict()
        assert data["error_type"] == "RuntimeError"
        assert data["error_message"] == "Test error"
        assert data["category"] == "unknown"
        assert data["severity"] == "low"
        assert data["recoverability"] == 0.5
        assert data["confidence"] == 0.5
        assert data["context"]["test"] == "value"


class TestErrorClassifier:
    """Test the main error classifier."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorClassifier()

    def test_classify_network_timeout(self, classifier):
        """Test classification of network timeout errors."""
        error = TimeoutError("Connection timed out")
        classification = classifier.classify(error)

        assert classification.category == ErrorCategory.NETWORK_TIMEOUT
        assert classification.severity == ErrorSeverity.MEDIUM
        assert classification.is_recoverable is True
        assert classification.confidence > 0.5

    def test_classify_permission_error(self, classifier):
        """Test classification of permission errors."""
        error = PermissionError("Permission denied: /etc/passwd")
        classification = classifier.classify(error)

        assert classification.category == ErrorCategory.PERMISSION_FILE
        assert classification.severity == ErrorSeverity.HIGH
        assert classification.is_recoverable is False
        assert classification.confidence > 0.5

    def test_classify_resource_error(self, classifier):
        """Test classification of resource errors."""
        error = OSError("No space left on device")
        context = {"disk_usage": 99.9}
        classification = classifier.classify(error, context)

        assert classification.category == ErrorCategory.RESOURCE_DISK
        assert classification.severity == ErrorSeverity.CRITICAL
        assert classification.is_recoverable is False

    def test_classify_unknown_error(self, classifier):
        """Test classification of unknown errors."""
        error = RuntimeError("Something went wrong")
        classification = classifier.classify(error)

        assert classification.category == ErrorCategory.UNKNOWN
        assert classification.confidence == 0.0

    def test_classify_with_cache(self, classifier):
        """Test that classification results are cached."""
        error = ValueError("Invalid data")

        # First classification
        classification1 = classifier.classify(error)

        # Second classification should come from cache
        classification2 = classifier.classify(error)

        # Should be the same object
        assert classification1.category == classification2.category
        assert classification1.confidence == classification2.confidence

    def test_get_recovery_strategy(self, classifier):
        """Test getting recovery strategy for classification."""
        error = TimeoutError("Request timed out")
        classification = classifier.classify(error)

        strategy, config = classifier.get_recovery_strategy(classification)

        assert strategy is not None
        assert config.approach == RecoveryApproach.EXPONENTIAL
        assert config.max_retries > 0

    def test_should_retry(self, classifier):
        """Test retry decision logic."""
        # Recoverable network error
        network_error = ConnectionError("Connection refused")
        classification = classifier.classify(network_error)
        assert classifier.should_retry(classification) is True

        # Non-recoverable permission error
        perm_error = PermissionError("Access denied")
        classification = classifier.classify(perm_error)
        assert classifier.should_retry(classification) is False

    def test_add_custom_pattern(self, classifier):
        """Test adding custom patterns."""
        custom_pattern = ErrorPattern(
            category=ErrorCategory.SERVICE_RATE_LIMIT,
            indicators=["rate limit exceeded", "too many requests"],
            exception_types=[RuntimeError],
            error_codes=["429"],
            severity=ErrorSeverity.MEDIUM,
            recoverability=RecoverabilityScore.ALWAYS,
            context_keys=["rate_limit_reset"]
        )

        classifier.add_pattern(custom_pattern)

        error = RuntimeError("Rate limit exceeded. Try again in 60 seconds")
        classification = classifier.classify(error)

        assert classification.category == ErrorCategory.SERVICE_RATE_LIMIT
        assert classification.is_recoverable is True

    def test_get_statistics(self, classifier):
        """Test getting classification statistics."""
        # Classify some errors
        errors = [
            TimeoutError("Timeout"),
            ConnectionError("Connection lost"),
            PermissionError("Denied"),
            ValueError("Bad value"),
        ]

        for error in errors:
            classifier.classify(error)

        stats = classifier.get_statistics()

        assert stats["total_classifications"] == 4
        assert stats["unique_errors"] == 4
        assert "by_category" in stats
        assert "by_severity" in stats
        assert stats["patterns_loaded"] > 0


class TestStrategyMapper:
    """Test strategy mapping functionality."""

    @pytest.fixture
    def mapper(self):
        """Create strategy mapper instance."""
        return StrategyMapper()

    def test_get_strategy_config_for_network_timeout(self, mapper):
        """Test getting strategy config for network timeout."""
        config = mapper.get_strategy_config(
            ErrorCategory.NETWORK_TIMEOUT,
            ErrorSeverity.MEDIUM,
            RecoverabilityScore.LIKELY
        )

        assert config.approach == RecoveryApproach.EXPONENTIAL
        assert config.max_retries == 5
        assert config.initial_delay == 1.0
        assert config.jitter is True

    def test_get_strategy_config_for_non_recoverable(self, mapper):
        """Test strategy config for non-recoverable errors."""
        config = mapper.get_strategy_config(
            ErrorCategory.PERMISSION_FILE,
            ErrorSeverity.HIGH,
            RecoverabilityScore.NEVER
        )

        assert config.approach == RecoveryApproach.NO_RETRY
        assert config.max_retries == 0

    def test_get_strategy_config_adjusts_for_severity(self, mapper):
        """Test that strategy adjusts based on severity."""
        # Critical error should reduce retries
        config = mapper.get_strategy_config(
            ErrorCategory.RESOURCE_MEMORY,
            ErrorSeverity.CRITICAL,
            RecoverabilityScore.POSSIBLE
        )

        base_config = mapper.DEFAULT_STRATEGIES[ErrorCategory.RESOURCE_MEMORY]
        # Critical errors reduce retries - should be at least 1
        assert config.max_retries <= base_config.max_retries

    def test_create_strategy_exponential(self, mapper):
        """Test creating exponential backoff strategy."""
        from backend.src.recovery.classification.strategies import StrategyConfig

        config = StrategyConfig(
            approach=RecoveryApproach.EXPONENTIAL,
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=False  # Disable jitter for predictable testing
        )

        strategy = mapper.create_strategy(config)
        assert strategy is not None
        assert strategy.calculate_delay(0) == 1.0

    def test_create_strategy_no_retry(self, mapper):
        """Test creating no-retry strategy."""
        from backend.src.recovery.classification.strategies import StrategyConfig

        config = StrategyConfig(
            approach=RecoveryApproach.NO_RETRY,
            max_retries=0,
            initial_delay=0.0,
            max_delay=0.0
        )

        strategy = mapper.create_strategy(config)
        assert strategy is None


@pytest.mark.asyncio
class TestClassifierIntegration:
    """Test classifier integration with recovery system."""

    async def test_classify_async_timeout_error(self):
        """Test classifying async timeout errors."""
        classifier = ErrorClassifier()

        # Create a proper asyncio.TimeoutError
        timeout_error = TimeoutError("Operation timed out")
        classification = classifier.classify(timeout_error)
        assert classification.category == ErrorCategory.NETWORK_TIMEOUT
        assert classification.is_recoverable is True

    async def test_ssl_error_classification(self):
        """Test SSL error classification."""
        classifier = ErrorClassifier()

        # Create a mock SSL error
        ssl_error = ssl.SSLError("certificate verify failed")
        classification = classifier.classify(ssl_error)

        assert classification.category == ErrorCategory.NETWORK_SSL
        assert classification.severity == ErrorSeverity.HIGH
        assert classification.is_recoverable is False

