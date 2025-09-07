"""
Comprehensive tests for SQLAlchemy persistence implementation.
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend.src.recovery.persistence.sqlalchemy_persistence import SQLAlchemyPersistence
from backend.src.recovery.persistence.models import Base, RecoveryStateModel, RetryAttemptModel, ErrorLogModel
from backend.src.recovery.persistence.repository import RecoveryRepository
from backend.src.recovery.types import RecoveryData, RecoveryState


@pytest_asyncio.fixture
async def test_db():
    """Create a test database for each test."""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def persistence(test_db):
    """Create persistence instance with test database."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    persistence = SQLAlchemyPersistence("sqlite+aiosqlite:///:memory:")
    persistence.engine = test_db
    persistence.session_factory = async_sessionmaker(
        test_db,
        class_=AsyncSession,
        expire_on_commit=False
    )
    persistence._initialized = True  # Mark as initialized since test_db already created tables
    yield persistence
    await persistence.close()


@pytest.mark.asyncio
async def test_save_and_load_recovery_data(persistence):
    """Test saving and loading recovery data."""
    # Create test data
    recovery_data = RecoveryData(
        operation_id="test-123",
        function_name="test_function",
        args=(1, 2, 3),
        kwargs={"key": "value"},
        state=RecoveryState.IN_PROGRESS,
        attempt=1,
        metadata={"custom": "data"},
    )
    
    # Save data
    await persistence.save(recovery_data)
    
    # Load data
    loaded = await persistence.load("test-123")
    
    # Verify
    assert loaded is not None
    assert loaded.operation_id == "test-123"
    assert loaded.function_name == "test_function"
    assert loaded.args == (1, 2, 3)  # Repository converts back to tuple
    assert loaded.kwargs == {"key": "value"}
    assert loaded.state == RecoveryState.IN_PROGRESS
    assert loaded.attempt == 1
    assert loaded.metadata == {"custom": "data"}


@pytest.mark.asyncio
async def test_update_existing_recovery_data(persistence):
    """Test updating existing recovery data."""
    # Create and save initial data
    recovery_data = RecoveryData(
        operation_id="test-456",
        function_name="test_function",
        args=(),
        kwargs={},
        state=RecoveryState.PENDING,
        attempt=0,
    )
    await persistence.save(recovery_data)
    
    # Update data
    recovery_data.state = RecoveryState.SUCCESS
    recovery_data.attempt = 3
    recovery_data.metadata = {"result": "success"}
    await persistence.save(recovery_data)
    
    # Load and verify
    loaded = await persistence.load("test-456")
    assert loaded.state == RecoveryState.SUCCESS
    assert loaded.attempt == 3
    assert loaded.metadata == {"result": "success"}


@pytest.mark.asyncio
async def test_delete_recovery_data(persistence):
    """Test deleting recovery data."""
    # Create and save data
    recovery_data = RecoveryData(
        operation_id="test-789",
        function_name="test_function",
        args=(),
        kwargs={},
        state=RecoveryState.PENDING,
    )
    await persistence.save(recovery_data)
    
    # Verify it exists
    assert await persistence.load("test-789") is not None
    
    # Delete it
    await persistence.delete("test-789")
    
    # Verify it's gone
    assert await persistence.load("test-789") is None


@pytest.mark.asyncio
async def test_list_keys(persistence):
    """Test listing all recovery keys."""
    # Save multiple items
    for i in range(5):
        recovery_data = RecoveryData(
            operation_id=f"test-{i}",
            function_name="test_function",
            args=(),
            kwargs={},
            state=RecoveryState.PENDING,
        )
        await persistence.save(recovery_data)
    
    # List keys
    keys = await persistence.list_keys()
    
    # Verify
    assert len(keys) == 5
    assert set(keys) == {f"test-{i}" for i in range(5)}


@pytest.mark.asyncio
async def test_clear_all_data(persistence):
    """Test clearing all recovery data."""
    # Save multiple items
    for i in range(3):
        recovery_data = RecoveryData(
            operation_id=f"test-clear-{i}",
            function_name="test_function",
            args=(),
            kwargs={},
            state=RecoveryState.PENDING,
        )
        await persistence.save(recovery_data)
    
    # Clear all
    await persistence.clear()
    
    # Verify all are gone
    keys = await persistence.list_keys()
    assert len(keys) == 0


@pytest.mark.asyncio
async def test_get_stats(persistence):
    """Test getting persistence statistics."""
    # Create test data with different states
    states = [RecoveryState.PENDING, RecoveryState.IN_PROGRESS, RecoveryState.SUCCESS]
    for i, state in enumerate(states):
        recovery_data = RecoveryData(
            operation_id=f"test-stats-{i}",
            function_name=f"function_{i}",
            args=(),
            kwargs={},
            state=state,
            attempt=i,
        )
        await persistence.save(recovery_data)
    
    # Get stats
    stats = await persistence.get_stats()
    
    # Verify
    assert stats["type"] == "sqlalchemy"
    assert stats["total_states"] == 3
    assert "recent_activity" in stats
    assert len(stats["recent_activity"]) == 3


@pytest.mark.asyncio
async def test_cleanup_old_states(persistence):
    """Test cleaning up old recovery states."""
    # We need to manually create old states since we can't easily mock time
    async with persistence.session_factory() as session:
        # Create an old state (31 days old)
        old_date = datetime.utcnow() - timedelta(days=31)
        old_state = RecoveryStateModel(
            operation_id="old-state",
            function_name="old_function",
            args="[]",
            kwargs="{}",
            state="COMPLETED",
            attempt=1,
            recovery_metadata="{}",
            created_at=old_date,
            updated_at=old_date,
        )
        session.add(old_state)
        
        # Create a recent state
        recent_state = RecoveryStateModel(
            operation_id="recent-state",
            function_name="recent_function",
            args="[]",
            kwargs="{}",
            state="COMPLETED",
            attempt=1,
            recovery_metadata="{}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(recent_state)
        await session.commit()
    
    # Run cleanup (default 30 days)
    deleted = await persistence.cleanup_old_states()
    
    # Verify
    assert deleted == 1
    keys = await persistence.list_keys()
    assert len(keys) == 1
    assert keys[0] == "recent-state"


@pytest.mark.asyncio
async def test_repository_retry_attempts(persistence):
    """Test saving and retrieving retry attempts through repository."""
    async with persistence.session_factory() as session:
        repo = RecoveryRepository(session)
        
        # Save retry attempt
        await repo.save_retry_attempt(
            operation_id="test-retry",
            attempt_number=1,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            success=False,
            error=ValueError("Test error"),
            strategy_name="exponential",
            delay_seconds=1.0,
            context={"test": "context"}
        )
        
        # Retrieve attempts
        attempts = await repo.get_retry_attempts("test-retry")
        
        # Verify
        assert len(attempts) == 1
        attempt = attempts[0]
        assert attempt.operation_id == "test-retry"
        assert attempt.attempt_number == 1
        assert attempt.success is False
        assert attempt.error_type == "ValueError"
        assert attempt.error_message == "Test error"
        assert attempt.strategy_name == "exponential"
        assert attempt.delay_seconds == 1.0


@pytest.mark.asyncio
async def test_repository_error_logs(persistence):
    """Test saving and retrieving error logs through repository."""
    async with persistence.session_factory() as session:
        repo = RecoveryRepository(session)
        
        # Save error log
        await repo.save_error_log(
            operation_id="test-error",
            error=RuntimeError("Critical error"),
            error_category="system",
            severity="high",
            function_name="critical_function",
            attempt_number=3,
            error_subcategory="memory",
            recovery_strategy="exponential",
            can_recover=False,
            system_info={"memory": "low", "cpu": "high"}
        )
        
        # Retrieve error logs
        logs = await repo.get_error_logs("test-error")
        
        # Verify
        assert len(logs) == 1
        log = logs[0]
        assert log.operation_id == "test-error"
        assert log.error_type == "RuntimeError"
        assert log.error_message == "Critical error"
        assert log.error_category == "system"
        assert log.severity == "high"
        assert log.function_name == "critical_function"
        assert log.can_recover is False


@pytest.mark.asyncio
async def test_complex_data_serialization(persistence):
    """Test serialization of complex data types."""
    # Complex test data
    import decimal
    from datetime import date
    
    complex_data = RecoveryData(
        operation_id="complex-test",
        function_name="complex_function",
        args=(
            123,
            "string",
            [1, 2, 3],
            {"nested": {"data": "value"}},
            None,
            True,
            False,
        ),
        kwargs={
            "date": date.today().isoformat(),
            "decimal": str(decimal.Decimal("123.456")),
            "unicode": "日本語テスト",
            "special_chars": "!@#$%^&*()",
        },
        state=RecoveryState.PENDING,
        metadata={
            "large_list": list(range(100)),
            "deep_nesting": {"a": {"b": {"c": {"d": "value"}}}},
        }
    )
    
    # Save and load
    await persistence.save(complex_data)
    loaded = await persistence.load("complex-test")
    
    # Verify data integrity
    assert loaded.args[3]["nested"]["data"] == "value"
    assert loaded.kwargs["unicode"] == "日本語テスト"
    assert len(loaded.metadata["large_list"]) == 100
    assert loaded.metadata["deep_nesting"]["a"]["b"]["c"]["d"] == "value"


@pytest.mark.asyncio
async def test_concurrent_access(persistence):
    """Test concurrent access to persistence."""
    async def save_data(index):
        recovery_data = RecoveryData(
            operation_id=f"concurrent-{index}",
            function_name=f"function_{index}",
            args=(index,),
            kwargs={},
            state=RecoveryState.PENDING,
        )
        await persistence.save(recovery_data)
        return index
    
    # Save 10 items concurrently
    tasks = [save_data(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Verify all were saved
    keys = await persistence.list_keys()
    assert len(keys) == 10
    assert set(keys) == {f"concurrent-{i}" for i in range(10)}


@pytest.mark.asyncio
async def test_error_handling(persistence):
    """Test error handling in persistence operations."""
    # Test loading non-existent data
    result = await persistence.load("non-existent")
    assert result is None
    
    # Test deleting non-existent data (should not raise)
    await persistence.delete("non-existent")
    
    # Test invalid data that can't be serialized
    class UnserializableClass:
        pass
    
    recovery_data = RecoveryData(
        operation_id="unserializable",
        function_name="test",
        args=(UnserializableClass(),),  # This will fail JSON serialization
        kwargs={},
        state=RecoveryState.PENDING,
    )
    
    with pytest.raises(Exception):  # Should raise serialization error
        await persistence.save(recovery_data)


@pytest.mark.asyncio
async def test_database_initialization(persistence):
    """Test that database tables are created on first use."""
    # Reset initialization flag
    persistence._initialized = False
    
    # First operation should trigger initialization
    recovery_data = RecoveryData(
        operation_id="init-test",
        function_name="test",
        args=(),
        kwargs={},
        state=RecoveryState.PENDING,
    )
    await persistence.save(recovery_data)
    
    # Verify initialization happened
    assert persistence._initialized is True
    
    # Verify data was saved
    loaded = await persistence.load("init-test")
    assert loaded is not None