"""
Exceptions for the recovery system.
"""
from typing import Optional, Any
from .types import ErrorCategory


class RecoveryError(Exception):
    """Base exception for recovery system."""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN):
        super().__init__(message)
        self.category = category


class RecoveryExhaustedError(RecoveryError):
    """Raised when all recovery attempts have been exhausted."""
    
    def __init__(
        self, 
        message: str, 
        attempts: int, 
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.attempts = attempts
        self.original_error = original_error


class CircuitBreakerOpenError(RecoveryError):
    """Raised when circuit breaker is open."""
    
    def __init__(self, message: str, timeout_remaining: float):
        super().__init__(message)
        self.timeout_remaining = timeout_remaining


class RecoveryTimeoutError(RecoveryError):
    """Raised when recovery operation times out."""
    
    def __init__(self, message: str, timeout: float):
        super().__init__(message, ErrorCategory.TIMEOUT)
        self.timeout = timeout


class RecoveryStateError(RecoveryError):
    """Raised when there's an issue with recovery state."""
    
    def __init__(self, message: str, operation_id: str):
        super().__init__(message)
        self.operation_id = operation_id