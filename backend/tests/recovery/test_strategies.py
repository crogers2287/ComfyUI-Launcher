"""
Tests for recovery strategies.
"""
import pytest
from unittest.mock import Mock

from backend.src.recovery.types import ErrorCategory
from backend.src.recovery.strategies import (
    ExponentialBackoffStrategy, LinearBackoffStrategy,
    FixedDelayStrategy, CustomStrategy
)


class TestExponentialBackoffStrategy:
    """Test cases for ExponentialBackoffStrategy."""
    
    def test_exponential_delay_calculation(self):
        """Test exponential delay calculation."""
        strategy = ExponentialBackoffStrategy(
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0,
            jitter=False
        )
        
        assert strategy.calculate_delay(0) == 1.0  # 1 * 2^0
        assert strategy.calculate_delay(1) == 2.0  # 1 * 2^1
        assert strategy.calculate_delay(2) == 4.0  # 1 * 2^2
        assert strategy.calculate_delay(3) == 8.0  # 1 * 2^3
        assert strategy.calculate_delay(4) == 10.0  # capped at max_delay
    
    def test_jitter(self):
        """Test that jitter adds randomness."""
        strategy = ExponentialBackoffStrategy(
            initial_delay=10.0,
            backoff_factor=1.0,
            jitter=True,
            jitter_range=0.5
        )
        
        delays = [strategy.calculate_delay(0) for _ in range(10)]
        
        # All delays should be different (very unlikely to be same with jitter)
        assert len(set(delays)) > 1
        
        # All delays should be within jitter range
        for delay in delays:
            assert 5.0 <= delay <= 15.0  # 10.0 ± 50%
    
    def test_should_retry_logic(self):
        """Test retry decision logic."""
        strategy = ExponentialBackoffStrategy(
            non_retryable_exceptions={ValueError, TypeError}
        )
        
        # Network errors should be retryable
        assert strategy.should_retry(ConnectionError("test"), 0, 3) is True
        
        # Non-retryable exceptions
        assert strategy.should_retry(ValueError("test"), 0, 3) is False
        assert strategy.should_retry(TypeError("test"), 0, 3) is False
        
        # Exceeded max attempts
        assert strategy.should_retry(ConnectionError("test"), 3, 3) is False


class TestLinearBackoffStrategy:
    """Test cases for LinearBackoffStrategy."""
    
    def test_linear_delay_calculation(self):
        """Test linear delay calculation."""
        strategy = LinearBackoffStrategy(
            initial_delay=1.0,
            increment=2.0,
            max_delay=10.0
        )
        
        assert strategy.calculate_delay(0) == 1.0  # 1 + 2*0
        assert strategy.calculate_delay(1) == 3.0  # 1 + 2*1
        assert strategy.calculate_delay(2) == 5.0  # 1 + 2*2
        assert strategy.calculate_delay(3) == 7.0  # 1 + 2*3
        assert strategy.calculate_delay(5) == 10.0  # capped at max_delay


class TestFixedDelayStrategy:
    """Test cases for FixedDelayStrategy."""
    
    def test_fixed_delay(self):
        """Test that delay is always the same."""
        strategy = FixedDelayStrategy(delay=5.0)
        
        for attempt in range(10):
            assert strategy.calculate_delay(attempt) == 5.0


class TestCustomStrategy:
    """Test cases for CustomStrategy."""
    
    def test_custom_delay_function(self):
        """Test custom delay function."""
        # Fibonacci-like delay
        def fib_delay(attempt: int) -> float:
            if attempt == 0:
                return 1.0
            elif attempt == 1:
                return 1.0
            else:
                # Simplified calculation for testing
                return attempt * 2.0
        
        strategy = CustomStrategy(
            delay_func=fib_delay,
            name="Fibonacci"
        )
        
        assert strategy.calculate_delay(0) == 1.0
        assert strategy.calculate_delay(1) == 1.0
        assert strategy.calculate_delay(2) == 4.0
        assert strategy.calculate_delay(3) == 6.0
    
    def test_custom_retry_function(self):
        """Test custom retry decision function."""
        def custom_should_retry(error, attempt, max_attempts):
            # Only retry on specific error message
            return "retry me" in str(error).lower()
        
        strategy = CustomStrategy(
            delay_func=lambda a: 1.0,
            should_retry_func=custom_should_retry
        )
        
        assert strategy.should_retry(ValueError("Retry me please"), 0, 3) is True
        assert strategy.should_retry(ValueError("Do not retry"), 0, 3) is False
    
    def test_max_delay_cap(self):
        """Test that custom delays are capped."""
        strategy = CustomStrategy(
            delay_func=lambda a: a * 100,
            max_delay=50.0
        )
        
        assert strategy.calculate_delay(0) == 0.0
        assert strategy.calculate_delay(1) == 50.0  # capped
        assert strategy.calculate_delay(10) == 50.0  # capped