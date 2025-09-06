"""
Integration tests for recovery system.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch
import tempfile

from backend.src.recovery import recoverable, RecoveryConfig
from backend.src.recovery.persistence import SQLitePersistence
from backend.src.recovery.strategies import ExponentialBackoffStrategy


class TestIntegration:
    """Integration tests for recovery system."""
    
    @pytest.mark.asyncio
    async def test_download_with_recovery(self):
        """Test simulated download with recovery."""
        download_attempts = 0
        
        @recoverable(
            max_retries=3,
            initial_delay=0.1,
            strategy=ExponentialBackoffStrategy(jitter=False)
        )
        async def download_file(url: str, destination: str):
            nonlocal download_attempts
            download_attempts += 1
            
            # Simulate network failures on first two attempts
            if download_attempts < 3:
                raise ConnectionError(f"Network error on attempt {download_attempts}")
            
            # Success on third attempt
            return f"Downloaded {url} to {destination}"
        
        result = await download_file("http://example.com/file.zip", "/tmp/file.zip")
        assert "Downloaded" in result
        assert download_attempts == 3
    
    @pytest.mark.asyncio
    async def test_validation_with_recovery(self):
        """Test validation workflow with recovery."""
        validation_attempts = 0
        
        # Use memory persistence for testing
        from backend.src.recovery.persistence import MemoryPersistence
        persistence = MemoryPersistence()
        
        @recoverable(
            max_retries=2,
            persistence=persistence,
            initial_delay=0.05
        )
        async def validate_workflow(workflow_data: dict):
            nonlocal validation_attempts
            validation_attempts += 1
            
            # Simulate validation errors
            if validation_attempts == 1:
                raise ValueError("Missing required field: model_id")
            elif validation_attempts == 2:
                raise TimeoutError("Validation service timeout")
            
            return {"status": "valid", "workflow": workflow_data}
        
        workflow = {"name": "test_workflow", "nodes": []}
        result = await validate_workflow(workflow)
        
        assert result["status"] == "valid"
        assert validation_attempts == 3
        
        # Check persistence
        all_data = await persistence.get_all()
        assert len(all_data) == 1
        assert all_data[0].attempt == 2
    
    @pytest.mark.asyncio
    async def test_model_download_resume(self):
        """Test model download with resume capability."""
        
        class DownloadProgress:
            def __init__(self):
                self.bytes_downloaded = 0
                self.total_bytes = 1000000
            
            def update(self, bytes_downloaded):
                self.bytes_downloaded = bytes_downloaded
        
        progress = DownloadProgress()
        download_attempts = 0
        
        @recoverable(
            max_retries=3,
            initial_delay=0.1
        )
        async def download_model_with_resume(model_url: str, progress_tracker: DownloadProgress):
            nonlocal download_attempts
            download_attempts += 1
            
            # Simulate partial download failures
            if download_attempts == 1:
                # Download 30% then fail
                progress_tracker.update(300000)
                raise ConnectionError("Connection lost")
            elif download_attempts == 2:
                # Resume from 30%, download to 70% then fail
                progress_tracker.update(700000)
                raise ConnectionError("Connection timeout")
            else:
                # Resume from 70% and complete
                progress_tracker.update(progress_tracker.total_bytes)
                return "Download complete"
        
        result = await download_model_with_resume(
            "http://example.com/model.ckpt",
            progress
        )
        
        assert result == "Download complete"
        assert progress.bytes_downloaded == progress.total_bytes
        assert download_attempts == 3
    
    @pytest.mark.asyncio
    async def test_celery_task_with_recovery(self):
        """Test Celery task integration with recovery."""
        
        # Mock Celery task
        task_executions = []
        
        @recoverable(
            max_retries=2,
            initial_delay=0.05,
            strategy=ExponentialBackoffStrategy(
                non_retryable_exceptions={ValueError}
            )
        )
        async def process_workflow_task(task_id: str, workflow_data: dict):
            task_executions.append(task_id)
            
            if len(task_executions) == 1:
                # First attempt - network error (retryable)
                raise ConnectionError("Redis connection failed")
            elif len(task_executions) == 2:
                # Second attempt - validation error (non-retryable)
                raise ValueError("Invalid workflow format")
            
            return {"task_id": task_id, "status": "completed"}
        
        # Test retryable error followed by non-retryable
        from backend.src.recovery import RecoveryExhaustedError
        
        with pytest.raises(RecoveryExhaustedError) as exc_info:
            await process_workflow_task("task-123", {"workflow": "data"})
        
        # Should have tried twice (once for initial, once for retry of network error)
        # but not retry the ValueError
        assert len(task_executions) == 2
        assert isinstance(exc_info.value.original_error, ValueError)
    
    @pytest.mark.asyncio 
    async def test_websocket_notification_integration(self):
        """Test WebSocket notification during recovery."""
        notifications = []
        
        # Mock WebSocket emit
        async def mock_emit(event, data):
            notifications.append({"event": event, "data": data})
        
        @recoverable(max_retries=2, initial_delay=0.05)
        async def operation_with_notifications(socket_emit):
            attempt = len(notifications)
            
            # Emit recovery status
            await socket_emit("recovery_status", {
                "operation": "download_model",
                "attempt": attempt + 1,
                "max_attempts": 3
            })
            
            if attempt < 2:
                raise ConnectionError("Download failed")
            
            return "Success"
        
        result = await operation_with_notifications(mock_emit)
        assert result == "Success"
        
        # Check notifications were sent
        assert len(notifications) == 3
        assert notifications[0]["data"]["attempt"] == 1
        assert notifications[2]["data"]["attempt"] == 3
    
    @pytest.mark.asyncio
    async def test_full_stack_recovery(self):
        """Test full stack integration with persistence and strategies."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
            db_path = tf.name
        
        persistence = SQLitePersistence(db_path)
        strategy = ExponentialBackoffStrategy(
            initial_delay=0.05,
            backoff_factor=2.0,
            jitter=False
        )
        
        operation_calls = 0
        
        @recoverable(
            max_retries=3,
            persistence=persistence,
            strategy=strategy
        )
        async def complex_operation(data: dict):
            nonlocal operation_calls
            operation_calls += 1
            
            if operation_calls < 3:
                raise ConnectionError(f"Attempt {operation_calls} failed")
            
            return {"result": "processed", "input": data}
        
        # Execute operation
        result = await complex_operation({"test": "data"})
        assert result["result"] == "processed"
        
        # Verify persistence
        stats = await persistence.get_statistics()
        assert stats["total"] == 1
        assert stats["by_state"]["success"] == 1
        
        # Cleanup
        import os
        os.unlink(db_path)