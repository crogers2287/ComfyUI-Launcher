"""
Linear backoff retry strategy.
"""
from typing import Set, Type

from ..types import ErrorCategory
from .base import BaseStrategy


class LinearBackoffStrategy(BaseStrategy):
    """
    Linear backoff strategy.
    
    Delay increases linearly with each attempt:
    delay = min(initial_delay + (increment * attempt), max_delay)
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 60.0,
        retryable_categories: Set[ErrorCategory] = None,
        non_retryable_exceptions: Set[Type[Exception]] = None
    ):
        super().__init__(max_delay, retryable_categories, non_retryable_exceptions)
        self.initial_delay = initial_delay
        self.increment = increment
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate linearly increasing delay."""
        delay = self.initial_delay + (self.increment * attempt)
        return min(delay, self.max_delay)
    
    @property
    def name(self) -> str:
        return f"LinearBackoff(initial={self.initial_delay}, increment={self.increment})"