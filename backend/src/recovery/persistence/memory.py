"""In-memory implementation of state persistence."""
import asyncio
from datetime import datetime

from ..types import RecoveryData, RecoveryState
from .base import BasePersistence


class MemoryPersistence(BasePersistence):
    """In-memory implementation of state persistence.
    
    Useful for testing and scenarios where persistence across restarts
    is not required.
    """

    def __init__(self):
        super().__init__()
        self._storage: dict[str, RecoveryData] = {}
        self._lock = asyncio.Lock()

    async def _setup(self) -> None:
        """No setup needed for memory persistence."""
        pass

    async def save(self, recovery_data: RecoveryData) -> None:
        """Save recovery data to memory."""
        async with self._lock:
            recovery_data.updated_at = datetime.utcnow()
            self._storage[recovery_data.operation_id] = recovery_data

    async def load(self, operation_id: str) -> RecoveryData | None:
        """Load recovery data from memory."""
        async with self._lock:
            return self._storage.get(operation_id)

    async def delete(self, operation_id: str) -> None:
        """Delete recovery data from memory."""
        async with self._lock:
            self._storage.pop(operation_id, None)

    async def list_by_state(self, state: RecoveryState) -> list[RecoveryData]:
        """List all recovery data with given state."""
        async with self._lock:
            return [
                data for data in self._storage.values()
                if data.state == state
            ]

    async def clear(self) -> None:
        """Clear all stored data. Useful for testing."""
        async with self._lock:
            self._storage.clear()

    async def get_all(self) -> list[RecoveryData]:
        """Get all stored recovery data. Useful for testing."""
        async with self._lock:
            return list(self._storage.values())

