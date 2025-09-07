"""Integration tests for decorator with error classification."""
import asyncio
from unittest.mock import patch

import pytest

from backend.src.recovery import recoverable
from backend.src.recovery.classification import ErrorCategory, ErrorClassifier, ErrorPattern
from backend.src.recovery.classification.categories import ErrorSeverity, RecoverabilityScore
from backend.src.recovery.exceptions import RecoveryExhaustedError
from backend.src.recovery.persistence import MemoryPersistence


class TestDecoratorWithClassification:
    """Test recovery decorator with error classification integration."""

    @pytest.mark.asyncio
    async def test_decorator_uses_classifier_for_network_errors(self):
        """Test that decorator uses classifier for network error handling."""
        attempt_count = 0

        @recoverable(
            initial_delay=0.01,
            max_delay=0.1
        )
        async def network_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Connection refused")
            return "success"

        result = await network_operation()

        assert result == "success"
        assert attempt_count == 3  # Should retry network errors

    @pytest.mark.asyncio
    async def test_decorator_respects_non_recoverable_errors(self):
        """Test that decorator doesn't retry non-recoverable errors."""
        attempt_count = 0

        @recoverable(
            initial_delay=0.01
        )
        async def permission_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise PermissionError("Access denied to /etc/passwd")

        with pytest.raises(RecoveryExhaustedError) as exc_info:
            await permission_operation()

        assert attempt_count == 1  # Should not retry permission errors
        assert isinstance(exc_info.value.original_error, PermissionError)

    @pytest.mark.asyncio
    async def test_decorator_with_custom_classifier(self):
        """Test decorator with custom classifier configuration."""
        # Create custom pattern
        custom_pattern = ErrorPattern(
            category=ErrorCategory.SERVICE_RATE_LIMIT,
            indicators=["rate limit", "throttled"],
            exception_types=[RuntimeError],
            error_codes=["429"],
            severity=ErrorSeverity.MEDIUM,
            recoverability=RecoverabilityScore.ALWAYS,
            context_keys=[]
        )

        classifier = ErrorClassifier(custom_patterns=[custom_pattern])
        attempt_count = 0

        @recoverable(
            classifier=classifier,
            initial_delay=0.01,
            max_delay=0.1
        )
        async def rate_limited_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise RuntimeError("API rate limit exceeded")
            return "success"

        result = await rate_limited_operation()

        assert result == "success"
        assert attempt_count == 4  # Should retry rate limit errors

    @pytest.mark.asyncio
    async def test_decorator_saves_classification_metadata(self):
        """Test that classification metadata is saved to persistence."""
        persistence = MemoryPersistence()

        @recoverable(
            persistence=persistence,
            max_retries=1,
            initial_delay=0.01
        )
        async def failing_operation():
            raise TimeoutError("Network timeout")

        with pytest.raises(RecoveryExhaustedError):
            await failing_operation()

        # Check saved metadata
        saved_data = await persistence.get_all()
        assert len(saved_data) == 1

        metadata = saved_data[0].metadata
        assert 'error_category' in metadata
        assert 'error_severity' in metadata
        assert 'error_recoverable' in metadata
        assert 'classification_confidence' in metadata

        # Should be classified as network timeout
        assert metadata['error_category'] == ErrorCategory.NETWORK_TIMEOUT.value
        assert metadata['error_recoverable'] is True

    @pytest.mark.asyncio
    async def test_decorator_uses_classifier_suggested_strategy(self):
        """Test that decorator uses strategy suggested by classifier."""
        attempt_count = 0
        delays = []

        # Mock sleep to track delays
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)  # Minimal actual delay

        @recoverable(
            max_retries=10  # High limit, let classifier decide
        )
        async def resource_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise OSError("No space left on device")

        with patch('asyncio.sleep', mock_sleep):
            with pytest.raises(RecoveryExhaustedError):
                await resource_operation()

        # Should not retry disk space errors
        assert attempt_count == 1
        assert len(delays) == 0

    @pytest.mark.asyncio
    async def test_decorator_adjusts_strategy_based_on_severity(self):
        """Test that strategy adjusts based on error severity."""
        critical_attempts = 0
        low_severity_attempts = 0

        @recoverable(
            initial_delay=0.01,
            max_retries=5
        )
        async def critical_error_operation():
            nonlocal critical_attempts
            critical_attempts += 1
            raise MemoryError("Out of memory")

        @recoverable(
            initial_delay=0.01,
            max_retries=5
        )
        async def low_error_operation():
            nonlocal low_severity_attempts
            low_severity_attempts += 1
            if low_severity_attempts < 3:
                raise RuntimeError("Temporary glitch")
            return "success"

        # Critical error - fewer retries
        with pytest.raises(RecoveryExhaustedError):
            await critical_error_operation()

        # Low severity - more retries
        result = await low_error_operation()

        assert critical_attempts <= 3  # Reduced for critical errors
        assert low_severity_attempts == 3
        assert result == "success"

    def test_sync_function_with_classification(self):
        """Test sync function decoration with classification."""
        attempt_count = 0

        @recoverable(
            initial_delay=0.01
        )
        def sync_network_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise OSError("Connection reset")
            return "success"

        result = sync_network_operation()

        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_classification_context_includes_function_info(self):
        """Test that classification context includes function information."""
        classifier = ErrorClassifier()
        classified_context = None

        # Patch classify to capture context
        original_classify = classifier.classify

        def mock_classify(error, context=None):
            nonlocal classified_context
            classified_context = context
            return original_classify(error, context)

        classifier.classify = mock_classify

        @recoverable(
            classifier=classifier,
            max_retries=0
        )
        async def test_function(arg1, kwarg1=None):
            raise ValueError("Test error")

        with pytest.raises(RecoveryExhaustedError):
            await test_function("test_arg", kwarg1="test_kwarg")

        assert classified_context is not None
        assert 'function_name' in classified_context
        assert 'test_function' in classified_context['function_name']
        assert classified_context['args'] == ("test_arg",)
        assert classified_context['kwargs'] == {"kwarg1": "test_kwarg"}

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_classification(self):
        """Test circuit breaker integration with classification."""
        from backend.src.recovery.exceptions import CircuitBreakerOpenError

        attempt_count = 0

        @recoverable(
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=0.1,
            initial_delay=0.01
        )
        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise ConnectionError("Service unavailable")

        # First call should exhaust retries and open circuit
        with pytest.raises(RecoveryExhaustedError):
            await flaky_operation()

        first_attempts = attempt_count

        # Second call should fail immediately with circuit open
        with pytest.raises(CircuitBreakerOpenError):
            await flaky_operation()

        # No additional attempts when circuit is open
        assert attempt_count == first_attempts

    @pytest.mark.asyncio
    async def test_timeout_classification(self):
        """Test that timeouts are properly classified."""
        @recoverable(
            timeout=0.001,
            initial_delay=0.01,
            max_retries=2
        )
        async def slow_operation():
            await asyncio.sleep(1)  # Will timeout
            return "done"

        with pytest.raises(RecoveryExhaustedError) as exc_info:
            await slow_operation()

        # Should have retried the timeout
        from backend.src.recovery.exceptions import RecoveryTimeoutError
        assert isinstance(exc_info.value.original_error, RecoveryTimeoutError)

