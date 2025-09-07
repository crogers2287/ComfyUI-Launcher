"""Main recovery decorator implementation.
"""
import asyncio
import functools
import logging
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar, cast

from .exceptions import CircuitBreakerOpenError, RecoveryExhaustedError, RecoveryTimeoutError
from .types import (
    ErrorCategory,
    RecoveryConfig,
    RecoveryData,
    RecoveryState,
    RecoveryStrategy,
    StatePersistence,
)

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, threshold: int = 5, timeout: float = 300.0):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open

    def record_success(self):
        """Record successful execution."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.threshold:
            self.state = "open"

    def can_execute(self) -> tuple[bool, float | None]:
        """Check if execution is allowed."""
        if self.state == "closed":
            return True, None

        if self.state == "open" and self.last_failure_time:
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure >= self.timeout:
                self.state = "half-open"
                return True, None
            timeout_remaining = self.timeout - time_since_failure
            return False, timeout_remaining

        return True, None


# Global circuit breakers per function
_circuit_breakers: dict[str, CircuitBreaker] = {}


def _get_circuit_breaker(func_name: str, config: RecoveryConfig) -> CircuitBreaker:
    """Get or create circuit breaker for function."""
    if func_name not in _circuit_breakers:
        _circuit_breakers[func_name] = CircuitBreaker(
            threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout
        )
    return _circuit_breakers[func_name]


def _classify_error(error: Exception) -> ErrorCategory:
    """Classify error into categories."""
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Network errors
    network_indicators = [
        'connection', 'network', 'socket', 'dns', 'resolve',
        'refused', 'reset', 'unreachable', 'timeout'
    ]
    if any(indicator in error_str or indicator in error_type for indicator in network_indicators):
        return ErrorCategory.NETWORK

    # Timeout errors
    if 'timeout' in error_str or 'timeout' in error_type:
        return ErrorCategory.TIMEOUT

    # Permission errors
    permission_indicators = ['permission', 'denied', 'forbidden', '403', 'unauthorized', '401']
    if any(indicator in error_str or indicator in error_type for indicator in permission_indicators):
        return ErrorCategory.PERMISSION

    # Validation errors
    validation_indicators = ['validation', 'invalid', 'malformed', 'schema', 'format']
    if any(indicator in error_str or indicator in error_type for indicator in validation_indicators):
        return ErrorCategory.VALIDATION

    # Resource errors
    resource_indicators = ['memory', 'disk', 'space', 'quota', 'limit', 'exhausted']
    if any(indicator in error_str or indicator in error_type for indicator in resource_indicators):
        return ErrorCategory.RESOURCE

    return ErrorCategory.UNKNOWN


async def _execute_with_timeout(func: Callable, args: tuple, kwargs: dict, timeout: float | None) -> Any:
    """Execute function with optional timeout."""
    if timeout is None:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
    # For sync functions, run in executor with timeout
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(None, func, *args),
        timeout=timeout
    )


def recoverable(
    max_retries: int | None = None,
    initial_delay: float | None = None,
    backoff_factor: float | None = None,
    max_delay: float | None = None,
    timeout: float | None = None,
    persistence: StatePersistence | None = None,
    strategy: RecoveryStrategy | None = None,
    circuit_breaker_threshold: int | None = None,
    circuit_breaker_timeout: float | None = None
) -> Callable[[F], F]:
    """Decorator to add recovery capabilities to functions.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 1.0)
        backoff_factor: Factor to multiply delay by after each retry (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        timeout: Timeout for each execution attempt in seconds (default: None)
        persistence: State persistence implementation (default: None)
        strategy: Custom recovery strategy (default: None)
        circuit_breaker_threshold: Number of failures before opening circuit (default: 5)
        circuit_breaker_timeout: Time in seconds before circuit closes (default: 300.0)
    
    Returns:
        Decorated function with recovery capabilities

    """
    def decorator(func: F) -> F:
        # Create config with provided values
        config = RecoveryConfig(
            max_retries=max_retries or 3,
            initial_delay=initial_delay or 1.0,
            backoff_factor=backoff_factor or 2.0,
            max_delay=max_delay or 60.0,
            timeout=timeout,
            circuit_breaker_threshold=circuit_breaker_threshold or 5,
            circuit_breaker_timeout=circuit_breaker_timeout or 300.0,
            persistence=persistence,
            strategy=strategy
        )

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Async wrapper for decorated function."""
            operation_id = kwargs.pop('_recovery_operation_id', None) or str(uuid.uuid4())
            func_name = f"{func.__module__}.{func.__qualname__}"
            circuit_breaker = _get_circuit_breaker(func_name, config)

            # Check circuit breaker
            can_execute, timeout_remaining = circuit_breaker.can_execute()
            if not can_execute:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open for {func_name}",
                    timeout_remaining or 0
                )

            # Initialize recovery data
            recovery_data = RecoveryData(
                operation_id=operation_id,
                function_name=func_name,
                args=args,
                kwargs=kwargs,
                state=RecoveryState.IN_PROGRESS
            )

            # Save initial state if persistence is configured
            if config.persistence:
                await config.persistence.save(recovery_data)

            attempt = 0
            last_error: Exception | None = None

            while attempt <= config.max_retries:
                try:
                    # Log attempt
                    logger.info(f"Attempting {func_name} (attempt {attempt + 1}/{config.max_retries + 1})")

                    # Execute with timeout
                    result = await _execute_with_timeout(func, args, kwargs, config.timeout)

                    # Success - update state
                    circuit_breaker.record_success()
                    recovery_data.attempt = attempt
                    recovery_data.state = RecoveryState.SUCCESS
                    recovery_data.updated_at = datetime.utcnow()

                    if config.persistence:
                        await config.persistence.save(recovery_data)

                    logger.info(f"Successfully executed {func_name} after {attempt + 1} attempts")
                    return result

                except TimeoutError:
                    last_error = RecoveryTimeoutError(
                        f"Operation timed out after {config.timeout}s",
                        config.timeout or 0
                    )
                    logger.error(f"Timeout in {func_name}: {last_error}")

                except Exception as e:
                    last_error = e
                    logger.error(f"Error in {func_name}: {e}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")

                # Record failure
                circuit_breaker.record_failure()

                # Check if we should retry
                error_category = _classify_error(last_error)

                # Update recovery data
                recovery_data.attempt = attempt
                recovery_data.error = last_error
                recovery_data.state = RecoveryState.RECOVERING
                recovery_data.updated_at = datetime.utcnow()
                recovery_data.metadata['error_category'] = error_category.value

                if config.persistence:
                    await config.persistence.save(recovery_data)

                # Determine if we should retry
                if config.strategy:
                    should_retry = config.strategy.should_retry(last_error, attempt, config.max_retries)
                else:
                    # Default retry logic - don't retry permission/validation errors
                    should_retry = error_category not in [ErrorCategory.PERMISSION, ErrorCategory.VALIDATION]

                if not should_retry or attempt >= config.max_retries:
                    break

                # Calculate delay
                if config.strategy:
                    delay = config.strategy.calculate_delay(attempt)
                else:
                    # Default exponential backoff
                    delay = min(
                        config.initial_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )

                logger.info(f"Retrying {func_name} after {delay}s delay")
                await asyncio.sleep(delay)
                attempt += 1

            # All retries exhausted
            recovery_data.state = RecoveryState.EXHAUSTED
            recovery_data.updated_at = datetime.utcnow()

            if config.persistence:
                await config.persistence.save(recovery_data)

            raise RecoveryExhaustedError(
                f"Recovery exhausted for {func_name} after {attempt + 1} attempts",
                attempts=attempt + 1,
                original_error=last_error
            )

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper for decorated function."""
            # Run async wrapper in event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(async_wrapper(*args, **kwargs))

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator
