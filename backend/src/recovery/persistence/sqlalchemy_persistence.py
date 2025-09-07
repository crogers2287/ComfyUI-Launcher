"""SQLAlchemy-based persistence implementation for recovery decorator state."""
import asyncio
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..types import RecoveryData, RecoveryState
from .base import BasePersistence
from .repository import RecoveryRepository


class SQLAlchemyPersistence(BasePersistence):
    """SQLAlchemy-based persistence implementation."""

    def __init__(self, database_url: str | None = None):
        """Initialize SQLAlchemy persistence.
        
        Args:
            database_url: SQLAlchemy database URL. Defaults to SQLite in user data dir.

        """
        if database_url is None:
            # Default to SQLite in user data directory
            data_dir = Path.home() / ".comfyui-launcher" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "recovery.db"
            database_url = f"sqlite+aiosqlite:///{db_path}"

        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_initialized(self):
        """Ensure database tables are created."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            # Import models to ensure they're registered
            from .models import Base

            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._initialized = True

    async def save(self, recovery_data: RecoveryData) -> None:
        """Save recovery data to database."""
        await self._ensure_initialized()

        async with self.session_factory() as session:
            repository = RecoveryRepository(session)
            await repository.save_recovery_state(recovery_data)

    async def load(self, key: str) -> RecoveryData | None:
        """Load recovery data from database."""
        await self._ensure_initialized()

        async with self.session_factory() as session:
            repository = RecoveryRepository(session)
            return await repository.get_recovery_state(key)

    async def delete(self, key: str) -> None:
        """Delete recovery data from database."""
        await self._ensure_initialized()

        async with self.session_factory() as session:
            repository = RecoveryRepository(session)
            await repository.delete_recovery_state(key)

    async def list_keys(self) -> list[str]:
        """List all recovery keys in database."""
        await self._ensure_initialized()

        async with self.session_factory() as session:
            repository = RecoveryRepository(session)
            return await repository.list_recovery_keys()

    async def clear(self) -> None:
        """Clear all recovery data from database."""
        await self._ensure_initialized()

        async with self.session_factory() as session:
            repository = RecoveryRepository(session)
            await repository.clear_all()

    async def get_stats(self) -> dict[str, Any]:
        """Get persistence statistics."""
        await self._ensure_initialized()

        async with self.session_factory() as session:
            repository = RecoveryRepository(session)

            total_states = await repository.count_recovery_states()
            total_retries = await repository.count_retry_attempts()
            total_errors = await repository.count_error_logs()

            # Get recent activity
            recent_states = await repository.get_recent_recovery_states(limit=10)

            return {
                "type": "sqlalchemy",
                "database_url": self.database_url,
                "total_states": total_states,
                "total_retries": total_retries,
                "total_errors": total_errors,
                "recent_activity": [
                    {
                        "key": state.operation_id,
                        "function_name": state.function_name,
                        "created_at": state.created_at.isoformat(),
                        "updated_at": state.updated_at.isoformat(),
                        "retry_count": state.attempt,
                        "status": state.state,
                    }
                    for state in recent_states
                ]
            }

    async def cleanup_old_states(self, days: int = 30) -> int:
        """Clean up old recovery states.
        
        Args:
            days: Number of days to keep. States older than this are deleted.
            
        Returns:
            Number of states deleted.

        """
        await self._ensure_initialized()

        async with self.session_factory() as session:
            repository = RecoveryRepository(session)
            return await repository.cleanup_old_states(days=days)

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
    
    async def _setup(self) -> None:
        """Set up the persistence backend."""
        await self._ensure_initialized()
    
    async def list_by_state(self, state: RecoveryState) -> list[RecoveryData]:
        """List all recovery data with given state."""
        await self._ensure_initialized()
        
        async with self.session_factory() as session:
            repository = RecoveryRepository(session)
            return await repository.list_by_state(state)

