"""
SQLite implementation of state persistence.
"""
import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..types import RecoveryData, RecoveryState
from .base import BasePersistence


logger = logging.getLogger(__name__)


class SQLitePersistence(BasePersistence):
    """
    SQLite-based implementation of state persistence.
    
    Provides durable storage that survives application restarts.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        super().__init__()
        if db_path is None:
            # Default to data directory
            data_dir = Path(os.path.expanduser("~/.comfyui-launcher/data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "recovery.db")
        
        self.db_path = db_path
        self._lock = asyncio.Lock()
    
    async def _setup(self) -> None:
        """Create database schema if needed."""
        async with self._lock:
            await self._run_in_thread(self._create_schema)
    
    def _create_schema(self):
        """Create database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recovery_data (
                    operation_id TEXT PRIMARY KEY,
                    function_name TEXT NOT NULL,
                    args TEXT NOT NULL,
                    kwargs TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    error TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recovery_state 
                ON recovery_data(state)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recovery_updated 
                ON recovery_data(updated_at)
            """)
            
            conn.commit()
    
    async def _run_in_thread(self, func, *args):
        """Run blocking database operation in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)
    
    def _save_sync(self, recovery_data: RecoveryData):
        """Synchronous save operation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO recovery_data (
                    operation_id, function_name, args, kwargs, state,
                    attempt, error, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recovery_data.operation_id,
                recovery_data.function_name,
                json.dumps(recovery_data.args),
                json.dumps(recovery_data.kwargs),
                recovery_data.state.value,
                recovery_data.attempt,
                str(recovery_data.error) if recovery_data.error else None,
                json.dumps(recovery_data.metadata),
                recovery_data.created_at.isoformat(),
                recovery_data.updated_at.isoformat()
            ))
            conn.commit()
    
    async def save(self, recovery_data: RecoveryData) -> None:
        """Save recovery data to SQLite."""
        await self.initialize()
        recovery_data.updated_at = datetime.utcnow()
        async with self._lock:
            await self._run_in_thread(self._save_sync, recovery_data)
    
    def _load_sync(self, operation_id: str) -> Optional[RecoveryData]:
        """Synchronous load operation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM recovery_data WHERE operation_id = ?
            """, (operation_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_recovery_data(row)
            return None
    
    async def load(self, operation_id: str) -> Optional[RecoveryData]:
        """Load recovery data from SQLite."""
        await self.initialize()
        async with self._lock:
            return await self._run_in_thread(self._load_sync, operation_id)
    
    def _delete_sync(self, operation_id: str):
        """Synchronous delete operation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM recovery_data WHERE operation_id = ?
            """, (operation_id,))
            conn.commit()
    
    async def delete(self, operation_id: str) -> None:
        """Delete recovery data from SQLite."""
        await self.initialize()
        async with self._lock:
            await self._run_in_thread(self._delete_sync, operation_id)
    
    def _list_by_state_sync(self, state: RecoveryState) -> List[RecoveryData]:
        """Synchronous list by state operation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM recovery_data WHERE state = ?
                ORDER BY updated_at DESC
            """, (state.value,))
            
            return [self._row_to_recovery_data(row) for row in cursor.fetchall()]
    
    async def list_by_state(self, state: RecoveryState) -> List[RecoveryData]:
        """List all recovery data with given state."""
        await self.initialize()
        async with self._lock:
            return await self._run_in_thread(self._list_by_state_sync, state)
    
    def _cleanup_old_sync(self, cutoff_date: datetime) -> int:
        """Synchronous cleanup operation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM recovery_data 
                WHERE updated_at < ?
            """, (cutoff_date.isoformat(),))
            conn.commit()
            return cursor.rowcount
    
    async def cleanup_old(self, days: int = 7) -> int:
        """Clean up old recovery data."""
        await self.initialize()
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with self._lock:
            deleted_count = await self._run_in_thread(
                self._cleanup_old_sync, cutoff_date
            )
        
        logger.info(f"Cleaned up {deleted_count} old recovery items")
        return deleted_count
    
    def _row_to_recovery_data(self, row: sqlite3.Row) -> RecoveryData:
        """Convert database row to RecoveryData object."""
        return RecoveryData(
            operation_id=row['operation_id'],
            function_name=row['function_name'],
            args=tuple(json.loads(row['args'])),
            kwargs=json.loads(row['kwargs']),
            state=RecoveryState(row['state']),
            attempt=row['attempt'],
            error=Exception(row['error']) if row['error'] else None,
            metadata=json.loads(row['metadata']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )