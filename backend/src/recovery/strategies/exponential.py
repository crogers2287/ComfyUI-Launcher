"""
Exponential backoff retry strategy.
"""
import random
from typing import Optional, Set, Type

from ..types import ErrorCategory
from .base import BaseStrategy


class ExponentialBackoffStrategy(BaseStrategy):
    """
    Exponential backoff strategy with optional jitter.
    
    Delay increases exponentially with each attempt:
    delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_range: float = 0.1,
        retryable_categories: Set[ErrorCategory] = None,
        non_retryable_exceptions: Set[Type[Exception]] = None
    ):
        super().__init__(max_delay, retryable_categories, non_retryable_exceptions)
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.jitter_range = jitter_range
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate exponentially increasing delay with optional jitter."""
        # Base exponential calculation
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter and delay > 0:
            jitter_amount = delay * self.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay)  # Ensure positive delay
        
        return delay
    
    @property
    def name(self) -> str:
        return f"ExponentialBackoff(initial={self.initial_delay}, factor={self.backoff_factor})"