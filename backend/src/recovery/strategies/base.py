"""
Base class for recovery strategies.
"""
from abc import ABC, abstractmethod
from typing import Set, Type

from ..types import ErrorCategory


class BaseStrategy(ABC):
    """Base class for recovery strategies."""
    
    def __init__(
        self,
        max_delay: float = 60.0,
        retryable_categories: Set[ErrorCategory] = None,
        non_retryable_exceptions: Set[Type[Exception]] = None
    ):
        self.max_delay = max_delay
        self.retryable_categories = retryable_categories or {
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RESOURCE,
            ErrorCategory.UNKNOWN
        }
        self.non_retryable_exceptions = non_retryable_exceptions or set()
    
    @abstractmethod
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        pass
    
    def should_retry(self, error: Exception, attempt: int, max_attempts: int) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-indexed)
            max_attempts: Maximum number of attempts allowed
            
        Returns:
            True if should retry, False otherwise
        """
        # Check if we've exceeded max attempts
        if attempt >= max_attempts:
            return False
        
        # Check for non-retryable exceptions
        if type(error) in self.non_retryable_exceptions:
            return False
        
        # Check error category
        from ..decorator import _classify_error
        category = _classify_error(error)
        
        return category in self.retryable_categories
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging."""
        pass