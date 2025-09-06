"""
Stub implementation of recovery decorator for issue #5.
This provides minimal functionality when core recovery system is not available.
"""
import time
import functools
from typing import Callable, TypeVar, Optional

F = TypeVar('F', bound=Callable)


def recoverable(
    max_retries: Optional[int] = None,
    initial_delay: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    timeout: Optional[float] = None,
    persistence=None,
    strategy=None,
    circuit_breaker_threshold: Optional[int] = None,
    circuit_breaker_timeout: Optional[float] = None
) -> Callable[[F], F]:
    """
    Stub recovery decorator with basic retry logic.
    
    This is a simplified version that provides basic retry functionality
    when the full recovery system from issue #2 is not available.
    """
    def decorator(func: F) -> F:
        max_attempts = (max_retries or 3) + 1
        delay = initial_delay or 1.0
        factor = backoff_factor or 2.0
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    # Don't retry on final attempt
                    if attempt >= max_attempts - 1:
                        break
                    
                    # Calculate delay
                    retry_delay = delay * (factor ** attempt)
                    
                    print(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                    time.sleep(retry_delay)
            
            # All attempts failed
            raise last_error
        
        return wrapper
    
    return decorator


# Stub classes for compatibility
class RecoveryConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class RecoveryState:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RECOVERING = "recovering"
    EXHAUSTED = "exhausted"


class ErrorCategory:
    NETWORK = "network"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    PERMISSION = "permission"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RecoveryError(Exception):
    pass


class RecoveryExhaustedError(RecoveryError):
    def __init__(self, message, attempts=0, original_error=None):
        super().__init__(message)
        self.attempts = attempts
        self.original_error = original_error


class CircuitBreakerOpenError(RecoveryError):
    pass


class RecoveryTimeoutError(RecoveryError):
    pass


class RecoveryStateError(RecoveryError):
    pass