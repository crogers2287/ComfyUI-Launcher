"""
Tests for the recovery decorator.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch
import time

from backend.src.recovery import (
    recoverable, RecoveryExhaustedError, CircuitBreakerOpenError,
    RecoveryTimeoutError, RecoveryState
)
from backend.src.recovery.persistence import MemoryPersistence
from backend.src.recovery.strategies import FixedDelayStrategy


class TestRecoveryDecorator:
    """Test cases for the @recoverable decorator."""
    
    def test_successful_execution_no_retry(self):
        """Test that successful execution doesn't trigger retries."""
        call_count = 0
        
        @recoverable(max_retries=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure(self):
        """Test that function retries on failure."""
        call_count = 0
        
        @recoverable(max_retries=2, initial_delay=0.1)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 3
    
    def test_exhausted_retries(self):
        """Test that exhausted retries raise RecoveryExhaustedError."""
        call_count = 0
        
        @recoverable(max_retries=2, initial_delay=0.1)
        def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")
        
        with pytest.raises(RecoveryExhaustedError) as exc_info:
            always_failing_func()
        
        assert exc_info.value.attempts == 3
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_function_support(self):
        """Test that decorator works with async functions."""
        call_count = 0
        
        @recoverable(max_retries=1, initial_delay=0.1)
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "async success"
        
        result = await async_func()
        assert result == "async success"
        assert call_count == 2
    
    def test_timeout_handling(self):
        """Test that timeout is properly handled."""
        @recoverable(timeout=0.1)
        def slow_func():
            time.sleep(0.5)
            return "should timeout"
        
        with pytest.raises(RecoveryExhaustedError) as exc_info:
            slow_func()
        
        assert isinstance(exc_info.value.original_error, RecoveryTimeoutError)
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        # Reset circuit breakers
        from backend.src.recovery.decorator import _circuit_breakers
        _circuit_breakers.clear()
        
        @recoverable(
            max_retries=0,
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=1.0
        )
        def circuit_test_func():
            raise ConnectionError("Always fails")
        
        # First two calls should fail normally
        for _ in range(2):
            with pytest.raises(RecoveryExhaustedError):
                circuit_test_func()
        
        # Third call should trigger circuit breaker
        with pytest.raises(CircuitBreakerOpenError):
            circuit_test_func()
    
    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """Test that state is persisted correctly."""
        persistence = MemoryPersistence()
        call_count = 0
        
        @recoverable(
            max_retries=2,
            initial_delay=0.1,
            persistence=persistence
        )
        async def persisted_func(arg1, arg2=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Fail first attempt")
            return f"success: {arg1}, {arg2}"
        
        result = await persisted_func("test", arg2="value")
        assert result == "success: test, value"
        
        # Check that state was saved
        all_data = await persistence.get_all()
        assert len(all_data) == 1
        assert all_data[0].state == RecoveryState.SUCCESS
        assert all_data[0].attempt == 1
    
    def test_custom_strategy(self):
        """Test custom recovery strategy."""
        strategy = FixedDelayStrategy(delay=0.05)
        call_count = 0
        
        @recoverable(max_retries=2, strategy=strategy)
        def strategy_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        start_time = time.time()
        result = strategy_func()
        elapsed = time.time() - start_time
        
        assert result == "success"
        assert call_count == 3
        # Should have ~0.1s delay (2 retries * 0.05s)
        assert 0.08 < elapsed < 0.15
    
    def test_non_retryable_errors(self):
        """Test that certain errors are not retried."""
        call_count = 0
        
        @recoverable(max_retries=3)
        def permission_error_func():
            nonlocal call_count
            call_count += 1
            raise PermissionError("Access denied")
        
        with pytest.raises(RecoveryExhaustedError):
            permission_error_func()
        
        # Should only be called once (no retries for permission errors)
        assert call_count == 1
    
    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        call_count = 0
        delays = []
        
        @recoverable(
            max_retries=3,
            initial_delay=0.1,
            backoff_factor=2.0,
            max_delay=1.0
        )
        def backoff_func():
            nonlocal call_count
            if call_count > 0:
                delays.append(time.time())
            call_count += 1
            if call_count <= 3:
                raise ConnectionError("Network error")
            return "success"
        
        start_time = time.time()
        delays.append(start_time)
        
        result = backoff_func()
        assert result == "success"
        assert call_count == 4
        
        # Check delay intervals
        # First retry: ~0.1s, Second: ~0.2s, Third: ~0.4s
        assert 0.08 < delays[1] - delays[0] < 0.12
        assert 0.18 < delays[2] - delays[1] < 0.22
        assert 0.38 < delays[3] - delays[2] < 0.42