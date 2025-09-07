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
    MemoryPersistence
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

