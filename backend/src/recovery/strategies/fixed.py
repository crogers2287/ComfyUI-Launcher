"""
Fixed delay retry strategy.
"""
from typing import Set, Type

from ..types import ErrorCategory
from .base import BaseStrategy


class FixedDelayStrategy(BaseStrategy):
    """
    Fixed delay strategy.
    
    Same delay between all retry attempts.
    """
    
    def __init__(
        self,
        delay: float = 1.0,
        retryable_categories: Set[ErrorCategory] = None,
        non_retryable_exceptions: Set[Type[Exception]] = None
    ):
        super().__init__(delay, retryable_categories, non_retryable_exceptions)
        self.delay = delay
    
    def calculate_delay(self, attempt: int) -> float:
        """Return fixed delay regardless of attempt number."""
        return self.delay
    
    @property
    def name(self) -> str:
        return f"FixedDelay(delay={self.delay})"