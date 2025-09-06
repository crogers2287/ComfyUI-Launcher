"""
Base implementation for state persistence.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List

from ..types import RecoveryData, RecoveryState, StatePersistence


logger = logging.getLogger(__name__)


class BasePersistence(ABC):
    """Base class for persistence implementations."""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the persistence backend."""
        if not self._initialized:
            await self._setup()
            self._initialized = True
    
    @abstractmethod
    async def _setup(self) -> None:
        """Setup the persistence backend. Override in subclasses."""
        pass
    
    @abstractmethod
    async def save(self, recovery_data: RecoveryData) -> None:
        """Save recovery data."""
        pass
    
    @abstractmethod
    async def load(self, operation_id: str) -> Optional[RecoveryData]:
        """Load recovery data by operation ID."""
        pass
    
    @abstractmethod
    async def delete(self, operation_id: str) -> None:
        """Delete recovery data."""
        pass
    
    @abstractmethod
    async def list_by_state(self, state: RecoveryState) -> List[RecoveryData]:
        """List all recovery data with given state."""
        pass
    
    async def cleanup_old(self, days: int = 7) -> int:
        """
        Clean up old recovery data.
        
        Args:
            days: Number of days to keep data
            
        Returns:
            Number of items deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all items
        all_items = []
        for state in RecoveryState:
            items = await self.list_by_state(state)
            all_items.extend(items)
        
        # Filter and delete old items
        deleted_count = 0
        for item in all_items:
            if item.updated_at < cutoff_date:
                try:
                    await self.delete(item.operation_id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting old recovery data {item.operation_id}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old recovery items")
        return deleted_count
    
    async def get_statistics(self) -> dict:
        """Get statistics about stored recovery data."""
        stats = {
            'total': 0,
            'by_state': {},
            'oldest': None,
            'newest': None
        }
        
        all_items = []
        for state in RecoveryState:
            items = await self.list_by_state(state)
            stats['by_state'][state.value] = len(items)
            stats['total'] += len(items)
            all_items.extend(items)
        
        if all_items:
            sorted_items = sorted(all_items, key=lambda x: x.created_at)
            stats['oldest'] = sorted_items[0].created_at.isoformat()
            stats['newest'] = sorted_items[-1].created_at.isoformat()
        
        return stats