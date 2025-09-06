"""
Tests for state persistence implementations.
"""
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
import pytest

from backend.src.recovery.types import RecoveryData, RecoveryState
from backend.src.recovery.persistence import (
    MemoryPersistence, SQLitePersistence
)


class TestMemoryPersistence:
    """Test cases for MemoryPersistence."""
    
    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test saving and loading recovery data."""
        persistence = MemoryPersistence()
        
        # Create test data
        recovery_data = RecoveryData(
            operation_id="test-123",
            function_name="test.func",
            args=("arg1", "arg2"),
            kwargs={"key": "value"},
            state=RecoveryState.IN_PROGRESS,
            attempt=1
        )
        
        # Save
        await persistence.save(recovery_data)
        
        # Load
        loaded = await persistence.load("test-123")
        assert loaded is not None
        assert loaded.operation_id == "test-123"
        assert loaded.function_name == "test.func"
        assert loaded.args == ("arg1", "arg2")
        assert loaded.kwargs == {"key": "value"}
        assert loaded.state == RecoveryState.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting recovery data."""
        persistence = MemoryPersistence()
        
        recovery_data = RecoveryData(
            operation_id="test-456",
            function_name="test.func",
            args=(),
            kwargs={}
        )
        
        await persistence.save(recovery_data)
        assert await persistence.load("test-456") is not None
        
        await persistence.delete("test-456")
        assert await persistence.load("test-456") is None
    
    @pytest.mark.asyncio
    async def test_list_by_state(self):
        """Test listing by state."""
        persistence = MemoryPersistence()
        
        # Create data with different states
        for i, state in enumerate([
            RecoveryState.PENDING,
            RecoveryState.IN_PROGRESS,
            RecoveryState.IN_PROGRESS,
            RecoveryState.SUCCESS,
            RecoveryState.FAILED
        ]):
            data = RecoveryData(
                operation_id=f"test-{i}",
                function_name="test.func",
                args=(),
                kwargs={},
                state=state
            )
            await persistence.save(data)
        
        # Test listing
        in_progress = await persistence.list_by_state(RecoveryState.IN_PROGRESS)
        assert len(in_progress) == 2
        
        success = await persistence.list_by_state(RecoveryState.SUCCESS)
        assert len(success) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_old(self):
        """Test cleanup of old data."""
        persistence = MemoryPersistence()
        
        # Create old and new data
        old_date = datetime.utcnow() - timedelta(days=10)
        new_date = datetime.utcnow()
        
        for i in range(5):
            data = RecoveryData(
                operation_id=f"test-{i}",
                function_name="test.func",
                args=(),
                kwargs={},
                created_at=old_date if i < 3 else new_date,
                updated_at=old_date if i < 3 else new_date
            )
            await persistence.save(data)
        
        # Cleanup
        deleted = await persistence.cleanup_old(days=7)
        assert deleted == 3
        
        # Check remaining
        all_data = await persistence.get_all()
        assert len(all_data) == 2


class TestSQLitePersistence:
    """Test cases for SQLitePersistence."""
    
    @pytest.fixture
    async def persistence(self):
        """Create SQLitePersistence with temp database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
            db_path = tf.name
        
        persistence = SQLitePersistence(db_path)
        await persistence.initialize()
        
        yield persistence
        
        # Cleanup
        os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_save_and_load(self, persistence):
        """Test saving and loading with SQLite."""
        recovery_data = RecoveryData(
            operation_id="sqlite-test-123",
            function_name="test.sqlite_func",
            args=("arg1", 42),
            kwargs={"key": "value", "number": 123},
            state=RecoveryState.RECOVERING,
            attempt=2,
            metadata={"extra": "data"}
        )
        
        await persistence.save(recovery_data)
        
        loaded = await persistence.load("sqlite-test-123")
        assert loaded is not None
        assert loaded.operation_id == "sqlite-test-123"
        assert loaded.function_name == "test.sqlite_func"
        assert loaded.args == ["arg1", 42]  # JSON converts tuple to list
        assert loaded.kwargs == {"key": "value", "number": 123}
        assert loaded.state == RecoveryState.RECOVERING
        assert loaded.attempt == 2
        assert loaded.metadata == {"extra": "data"}
    
    @pytest.mark.asyncio
    async def test_persistence_across_instances(self, persistence):
        """Test that data persists across instances."""
        # Save with first instance
        recovery_data = RecoveryData(
            operation_id="persist-test",
            function_name="test.func",
            args=(),
            kwargs={},
            state=RecoveryState.SUCCESS
        )
        await persistence.save(recovery_data)
        
        # Create new instance with same db
        persistence2 = SQLitePersistence(persistence.db_path)
        await persistence2.initialize()
        
        # Load with second instance
        loaded = await persistence2.load("persist-test")
        assert loaded is not None
        assert loaded.state == RecoveryState.SUCCESS
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, persistence):
        """Test concurrent access to SQLite."""
        async def save_data(op_id: str):
            data = RecoveryData(
                operation_id=op_id,
                function_name="concurrent.func",
                args=(),
                kwargs={},
                state=RecoveryState.IN_PROGRESS
            )
            await persistence.save(data)
        
        # Save multiple items concurrently
        tasks = [save_data(f"concurrent-{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify all saved
        all_items = []
        for state in RecoveryState:
            items = await persistence.list_by_state(state)
            all_items.extend(items)
        
        assert len(all_items) == 10
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, persistence):
        """Test statistics gathering."""
        # Create test data
        states = [
            RecoveryState.PENDING,
            RecoveryState.IN_PROGRESS,
            RecoveryState.IN_PROGRESS,
            RecoveryState.SUCCESS,
            RecoveryState.FAILED,
            RecoveryState.EXHAUSTED
        ]
        
        for i, state in enumerate(states):
            data = RecoveryData(
                operation_id=f"stats-{i}",
                function_name="test.func",
                args=(),
                kwargs={},
                state=state
            )
            await persistence.save(data)
        
        stats = await persistence.get_statistics()
        
        assert stats['total'] == 6
        assert stats['by_state'][RecoveryState.IN_PROGRESS.value] == 2
        assert stats['by_state'][RecoveryState.SUCCESS.value] == 1
        assert stats['oldest'] is not None
        assert stats['newest'] is not None