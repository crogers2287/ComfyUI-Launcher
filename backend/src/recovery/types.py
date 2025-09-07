"""
Shared type definitions for the recovery system.
"""
from typing import Any, Callable, Dict, Optional, Protocol, TypeVar, Union
from enum import Enum
import asyncio
from datetime import datetime, timezone


# Type variables
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class RecoveryState(Enum):
    """States for recovery operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RECOVERING = "recovering"
    EXHAUSTED = "exhausted"  # All retries exhausted


class ErrorCategory(Enum):
    """Categories for classifying errors."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    PERMISSION = "permission"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RecoveryStrategy(Protocol):
    """Protocol for recovery strategies."""
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt."""
        ...
    
    def should_retry(self, error: Exception, attempt: int, max_attempts: int) -> bool:
        """Determine if operation should be retried."""
        ...
    
    @property
    def name(self) -> str:
        """Strategy name for logging."""
        ...


class RecoveryData:
    """Data structure for recovery state persistence."""
    
    def __init__(
        self,
        operation_id: str,
        function_name: str,
        args: tuple,
        kwargs: dict,
        state: RecoveryState = RecoveryState.PENDING,
        attempt: int = 0,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.operation_id = operation_id
        self.function_name = function_name
        self.args = args
        self.kwargs = kwargs
        self.state = state
        self.attempt = attempt
        self.error = error
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "operation_id": self.operation_id,
            "function_name": self.function_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "state": self.state.value,
            "attempt": self.attempt,
            "error": str(self.error) if self.error else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RecoveryData':
        """Create from dictionary."""
        data = data.copy()
        if 'state' in data and isinstance(data['state'], str):
            data['state'] = RecoveryState(data['state'])
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


class StatePersistence(Protocol):
    """Protocol for state persistence implementations."""
    
    async def save(self, recovery_data: RecoveryData) -> None:
        """Save recovery data."""
        ...
    
    async def load(self, operation_id: str) -> Optional[RecoveryData]:
        """Load recovery data by operation ID."""
        ...
    
    async def delete(self, operation_id: str) -> None:
        """Delete recovery data."""
        ...
    
    async def list_by_state(self, state: RecoveryState) -> list[RecoveryData]:
        """List all recovery data with given state."""
        ...
    
    async def cleanup_old(self, days: int = 7) -> int:
        """Clean up old recovery data. Returns number of items deleted."""
        ...


class RecoveryConfig:
    """Configuration for recovery behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        timeout: Optional[float] = None,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 300.0,
        persistence: Optional[StatePersistence] = None,
        strategy: Optional[RecoveryStrategy] = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.timeout = timeout
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.persistence = persistence
        self.strategy = strategy