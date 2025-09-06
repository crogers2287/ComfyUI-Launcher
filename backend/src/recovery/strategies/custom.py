"""
Custom recovery strategy for specific use cases.
"""
from typing import Callable, Set, Type

from ..types import ErrorCategory
from .base import BaseStrategy


class CustomStrategy(BaseStrategy):
    """
    Custom recovery strategy with user-defined delay function.
    
    Allows complete control over retry behavior.
    """
    
    def __init__(
        self,
        delay_func: Callable[[int], float],
        should_retry_func: Callable[[Exception, int, int], bool] = None,
        name: str = "Custom",
        max_delay: float = 60.0,
        retryable_categories: Set[ErrorCategory] = None,
        non_retryable_exceptions: Set[Type[Exception]] = None
    ):
        super().__init__(max_delay, retryable_categories, non_retryable_exceptions)
        self.delay_func = delay_func
        self.should_retry_func = should_retry_func
        self._name = name
    
    def calculate_delay(self, attempt: int) -> float:
        """Use custom function to calculate delay."""
        delay = self.delay_func(attempt)
        return min(delay, self.max_delay)
    
    def should_retry(self, error: Exception, attempt: int, max_attempts: int) -> bool:
        """Use custom function if provided, otherwise default behavior."""
        if self.should_retry_func:
            return self.should_retry_func(error, attempt, max_attempts)
        return super().should_retry(error, attempt, max_attempts)
    
    @property
    def name(self) -> str:
        return self._name