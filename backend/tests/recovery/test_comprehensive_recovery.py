"""
Comprehensive backend recovery tests for ComfyUI Launcher Issue #8.

These tests cover all recovery scenarios including:
1. Network interruption during download
2. App crash during installation  
3. Browser refresh during operation
4. Multiple concurrent recoveries
5. Circuit breaker activation and recovery
6. Error classification and retry strategies
"""

import asyncio
import pytest
import tempfile
import json
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
import aiohttp
import requests
from pathlib import Path

from backend.src.recovery import (
    recoverable, RecoveryConfig, RecoveryExhaustedError, 
    CircuitBreakerOpenError, RecoveryTimeoutError
)
from backend.src.recovery.persistence import (
    MemoryPersistence, SQLAlchemyPersistence
)
from backend.src.recovery.strategies import (
    ExponentialBackoffStrategy, LinearBackoffStrategy, 
    FixedDelayStrategy, CustomStrategy
)
from backend.src.recovery.classification import ErrorClassifier, ErrorCategory
from backend.src.recovery.download_manager import DownloadManager
from backend.src.recovery.integration import RecoveryIntegrator
from backend.src.recovery.testing import RecoveryTestSuite, TestScenario, TestResult


class TestNetworkInterruptionRecovery:
    """Test recovery from network interruptions during model downloads."""
    
    @pytest.mark.asyncio
    async def test_network_interruption_download_recovery(self):
        """Test download recovery after network interruption."""
        download_attempts = 0
        download_results = []
        
        @recoverable(
            max_retries=3,
            initial_delay=0.1,
            backoff_factor=2.0,
            timeout=10.0
        )
        async def download_model_with_resume(model_url: str, save_path: str):
            nonlocal download_attempts, download_results
            download_attempts += 1
            
            # Simulate partial download progress
            progress_data = {
                "attempt": download_attempts,
                "downloaded_bytes": 100000 * download_attempts,
                "total_bytes": 1000000,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            download_results.append(progress_data)
            
            # Fail on first two attempts with network errors
            if download_attempts <= 2:
                if download_attempts == 1:
                    raise ConnectionError("Connection reset by peer")
                else:
                    raise aiohttp.ClientError("Request timeout")
            
            # Succeed on third attempt
            return {
                "status": "completed",
                "path": save_path,
                "bytes_downloaded": 1000000,
                "download_time": 2.5
            }
        
        # Test the download with recovery
        result = await download_model_with_resume(
            "https://huggingface.co/test/model.bin",
            "/tmp/test_model.bin"
        )
        
        # Verify recovery worked
        assert result["status"] == "completed"
        assert download_attempts == 3
        assert len(download_results) == 3
        
        # Verify progress was tracked
        assert download_results[0]["downloaded_bytes"] == 100000
        assert download_results[1]["downloaded_bytes"] == 200000
        assert download_results[2]["downloaded_bytes"] == 300000
    
    @pytest.mark.asyncio
    async def test_partial_download_resume_capability(self):
        """Test ability to resume from partial download."""
        class MockDownloadManager:
            def __init__(self):
                self.downloaded_bytes = 0
                self.total_bytes = 5000000
                self.file_exists = False
                self.resume_position = 0
            
            def get_file_size(self, path):
                return self.downloaded_bytes if self.file_exists else 0
            
            def set_resume_position(self, position):
                self.resume_position = position
            
            async def download_chunk(self, start_byte, end_byte):
                # Simulate network interruption
                if start_byte < 1000000:
                    raise ConnectionError("Network connection lost")
                elif start_byte < 2000000:
                    raise TimeoutError("Download timeout")
                else:
                    # Successful download
                    self.downloaded_bytes = end_byte
                    return b"mock_chunk_data"
        
        download_manager = MockDownloadManager()
        download_attempts = 0
        
        @recoverable(
            max_retries=3,
            initial_delay=0.05,
            persistence=MemoryPersistence()
        )
        async def resumable_download(url: str, save_path: str, manager: MockDownloadManager):
            nonlocal download_attempts
            download_attempts += 1
            
            # Check for existing file and resume position
            existing_size = manager.get_file_size(save_path)
            if existing_size > 0:
                manager.set_resume_position(existing_size)
            
            # Simulate download from resume position
            start_byte = manager.resume_position
            end_byte = manager.total_bytes
            
            try:
                chunk = await manager.download_chunk(start_byte, end_byte)
                manager.file_exists = True
                return {
                    "status": "completed",
                    "bytes_downloaded": manager.downloaded_bytes,
                    "resumed_from": start_byte
                }
            except Exception as e:
                # Save progress for recovery
                manager.downloaded_bytes = start_byte + (end_byte - start_byte) * 0.3
                manager.file_exists = True
                raise
        
        result = await resumable_download(
            "https://example.com/large_model.bin",
            "/tmp/large_model.bin",
            download_manager
        )
        
        assert result["status"] == "completed"
        assert download_attempts == 3
        assert result["resumed_from"] > 0
        assert result["bytes_downloaded"] == download_manager.total_bytes
    
    @pytest.mark.asyncio
    async def test_connection_failure_classification(self):
        """Test that connection failures are properly classified for retry."""
        classifier = ErrorClassifier()
        
        # Test various network error types
        network_errors = [
            ConnectionError("Connection refused"),
            ConnectionResetError("Connection reset by peer"),
            TimeoutError("Connection timeout"),
            aiohttp.ClientError("HTTP client error"),
            requests.exceptions.ConnectionError("Network unreachable")
        ]
        
        for error in network_errors:
            context = {"operation": "download", "url": "test_url"}
            classification = classifier.classify(error, context)
            
            assert classification.category == ErrorCategory.NETWORK
            assert classification.is_recoverable is True
    
    @pytest.mark.asyncio
    async def test_bandwidth_throttling_recovery(self):
        """Test recovery from bandwidth throttling scenarios."""
        throttle_count = 0
        
        @recoverable(
            max_retries=2,
            initial_delay=0.1,
            strategy=ExponentialBackoffStrategy(jitter=False)
        )
        async def download_with_throttle_detection(url: str):
            nonlocal throttle_count
            throttle_count += 1
            
            # Simulate throttling by slowing down response
            if throttle_count == 1:
                # Very slow response - simulate throttling
                await asyncio.sleep(0.5)
                raise TimeoutError("Download too slow - possible throttling")
            elif throttle_count == 2:
                # Still slow but within limits
                await asyncio.sleep(0.2)
                return {"status": "completed", "speed": "normal"}
            
            return {"status": "completed", "speed": "fast"}
        
        result = await download_with_throttle_detection("https://throttled-site.com/model.bin")
        assert result["status"] == "completed"
        assert throttle_count == 2


class TestAppCrashRecovery:
    """Test recovery from application crashes during operations."""
    
    @pytest.mark.asyncio
    async def test_workflow_import_crash_recovery(self):
        """Test workflow import recovery after app crash."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
            db_path = tf.name
        
        try:
            persistence = SQLitePersistence(f"sqlite+aiosqlite:///{db_path}")
            
            crash_simulation_count = 0
            import_progress = {}
            
            @recoverable(
                max_retries=1,
                persistence=persistence,
                initial_delay=0.05
            )
            async def import_workflow_with_crash_recovery(workflow_data: dict, project_name: str):
                nonlocal crash_simulation_count, import_progress
                
                crash_simulation_count += 1
                
                # Simulate crash during import
                if crash_simulation_count == 1:
                    # Start import
                    import_progress = {
                        "stage": "validating_nodes",
                        "progress": 25,
                        "total_nodes": len(workflow_data.get("nodes", [])),
                        "validated_nodes": 5
                    }
                    # Simulate crash (don't actually crash)
                    raise SystemError("Simulated application crash")
                
                # Recovery path - continue from where we left off
                if "validated_nodes" in import_progress:
                    import_progress["stage"] = "creating_connections"
                    import_progress["progress"] = 75
                    import_progress["created_connections"] = len(workflow_data.get("links", []))
                
                import_progress["stage"] = "completed"
                import_progress["progress"] = 100
                import_progress["completed_at"] = datetime.now(timezone.utc).isoformat()
                
                return {
                    "status": "completed",
                    "project_name": project_name,
                    "nodes_count": len(workflow_data.get("nodes", [])),
                    "links_count": len(workflow_data.get("links", [])),
                    "recovered_from_crash": crash_simulation_count > 1
                }
            
            # Test crash and recovery
            workflow_data = {
                "nodes": [
                    {"id": "1", "type": "CheckpointLoaderSimple", "inputs": {}},
                    {"id": "2", "type": "CLIPTextEncode", "inputs": {}},
                    {"id": "3", "type": "KSampler", "inputs": {}}
                ],
                "links": [[1, 0, 2, 0], [2, 0, 3, 0]]
            }
            
            result = await import_workflow_with_crash_recovery(
                workflow_data, 
                "crash_test_project"
            )
            
            assert result["status"] == "completed"
            assert result["recovered_from_crash"] is True
            assert crash_simulation_count == 2
            
            # Verify persistence recorded the recovery
            stats = await persistence.get_statistics()
            assert stats["total"] == 1
            assert stats["by_state"]["success"] == 1
            
        finally:
            import os
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_installation_crash_recovery(self):
        """Test installation recovery after app crash."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
            db_path = tf.name
        
        try:
            persistence = SQLitePersistence(f"sqlite+aiosqlite:///{db_path}")
            
            installation_stages = [
                "downloading_comfyui",
                "extracting_archive", 
                "installing_dependencies",
                "configuring_settings",
                "completed"
            ]
            current_stage_index = 0
            
            @recoverable(
                max_retries=2,
                persistence=persistence,
                strategy=LinearBackoffStrategy(delay_increment=0.1)
            )
            async def install_comfyui_with_crash_recovery(project_path: str, version: str):
                nonlocal current_stage_index
                
                # Simulate crash at different stages
                if current_stage_index < 2:  # Crash during download or extract
                    current_stage_index += 1
                    raise RuntimeError(f"Crash during {installation_stages[current_stage_index-1]}")
                
                # Continue from last known stage
                start_stage = current_stage_index
                for i in range(start_stage, len(installation_stages)):
                    stage = installation_stages[i]
                    await asyncio.sleep(0.05)  # Simulate work
                    current_stage_index = i
                
                return {
                    "status": "completed",
                    "project_path": project_path,
                    "version": version,
                    "completed_stages": len(installation_stages),
                    "recovery_required": start_stage > 0
                }
            
            result = await install_comfyui_with_crash_recovery(
                "/tmp/test_project",
                "latest"
            )
            
            assert result["status"] == "completed"
            assert result["recovery_required"] is True
            assert result["completed_stages"] == len(installation_stages)
            
        finally:
            import os
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_process_state_restoration(self):
        """Test restoration of process state after crash."""
        process_states = {}
        
        @recoverable(
            max_retries=1,
            persistence=MemoryPersistence()
        )
        async def long_running_process_with_state(process_id: str, steps: int):
            # Check for existing state
            if process_id in process_states:
                completed_steps = process_states[process_id]["completed_steps"]
                start_step = completed_steps + 1
            else:
                start_step = 1
                process_states[process_id] = {
                    "completed_steps": 0,
                    "results": [],
                    "start_time": datetime.now(timezone.utc).isoformat()
                }
            
            # Simulate crash during processing
            if start_step <= steps // 2 and process_states[process_id]["completed_steps"] == 0:
                process_states[process_id]["completed_steps"] = steps // 2
                raise MemoryError("Process out of memory - crash simulated")
            
            # Continue processing
            for step in range(start_step, steps + 1):
                await asyncio.sleep(0.01)
                process_states[process_id]["results"].append(f"step_{step}_result")
                process_states[process_id]["completed_steps"] = step
            
            process_states[process_id]["end_time"] = datetime.now(timezone.utc).isoformat()
            
            return {
                "process_id": process_id,
                "total_steps": steps,
                "completed_steps": process_states[process_id]["completed_steps"],
                "results": process_states[process_id]["results"],
                "recovered": start_step > 1
            }
        
        # Test crash and recovery
        result = await long_running_process_with_state("test_process", 10)
        
        assert result["completed_steps"] == 10
        assert result["recovered"] is True
        assert len(result["results"]) == 10


class TestBrowserRefreshRecovery:
    """Test recovery from browser refresh/refresh scenarios."""
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_recovery(self):
        """Test recovery after WebSocket disconnection (browser refresh)."""
        connection_states = []
        message_queue = []
        
        class MockWebSocket:
            def __init__(self):
                self.connected = False
                self.message_handlers = {}
            
            async def connect(self):
                self.connected = True
                connection_states.append("connected")
            
            async def disconnect(self):
                self.connected = False
                connection_states.append("disconnected")
            
            async def emit(self, event, data):
                if self.connected:
                    message_queue.append({"event": event, "data": data})
            
            def on(self, event, handler):
                self.message_handlers[event] = handler
        
        mock_socket = MockWebSocket()
        operation_id = None
        
        @recoverable(
            max_retries=2,
            initial_delay=0.1,
            circuit_breaker_threshold=3
        )
        async def operation_with_websocket_notifications(data: dict, socket: MockWebSocket):
            nonlocal operation_id
            
            # Generate operation ID if not exists
            if operation_id is None:
                operation_id = f"op_{datetime.now(timezone.utc).timestamp()}"
            
            try:
                # Simulate browser refresh (disconnect)
                if len(connection_states) == 1 and connection_states[0] == "connected":
                    await socket.disconnect()
                    raise ConnectionError("WebSocket disconnected - browser refresh")
                
                # Reconnect and continue
                if not socket.connected:
                    await socket.connect()
                    await socket.emit("recovery_status", {
                        "operation_id": operation_id,
                        "status": "reconnecting",
                        "message": "Recovering after browser refresh"
                    })
                
                # Continue with operation
                await socket.emit("progress", {
                    "operation_id": operation_id,
                    "progress": 50,
                    "message": "Processing data"
                })
                
                await asyncio.sleep(0.1)
                
                return {
                    "operation_id": operation_id,
                    "status": "completed",
                    "data_processed": len(data),
                    "connection_events": len(connection_states)
                }
                
            except Exception as e:
                await socket.emit("error", {
                    "operation_id": operation_id,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                raise
        
        # Connect socket first
        await mock_socket.connect()
        
        result = await operation_with_websocket_notifications(
            {"item1": "data1", "item2": "data2"},
            mock_socket
        )
        
        assert result["status"] == "completed"
        assert result["connection_events"] >= 2  # At least disconnect + reconnect
        assert mock_socket.connected is True
        
        # Verify recovery notifications were sent
        recovery_messages = [msg for msg in message_queue if msg["event"] == "recovery_status"]
        assert len(recovery_messages) >= 1
    
    @pytest.mark.asyncio
    async def test_session_state_restoration(self):
        """Test session state restoration after browser refresh."""
        session_storage = {}
        
        @recoverable(
            max_retries=1,
            persistence=MemoryPersistence()
        )
        async def session_based_operation(session_id: str, user_data: dict):
            # Check for existing session state
            if session_id in session_storage:
                session_state = session_storage[session_id]
                resume_point = session_state.get("resume_point", 0)
                completed_steps = session_state.get("completed_steps", [])
            else:
                session_storage[session_id] = {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "resume_point": 0,
                    "completed_steps": []
                }
                resume_point = 0
                completed_steps = []
            
            # Simulate browser refresh during operation
            if resume_point == 0 and len(completed_steps) == 0:
                # Save state before "refresh"
                session_storage[session_id]["resume_point"] = 1
                session_storage[session_id]["completed_steps"] = ["step1", "step2"]
                raise ConnectionError("Session expired - browser refresh")
            
            # Continue from saved state
            all_steps = ["step1", "step2", "step3", "step4", "step5"]
            steps_to_complete = [step for step in all_steps if step not in completed_steps]
            
            for step in steps_to_complete:
                await asyncio.sleep(0.02)
                completed_steps.append(step)
                session_storage[session_id]["completed_steps"] = completed_steps
            
            session_storage[session_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            return {
                "session_id": session_id,
                "status": "completed",
                "total_steps": len(all_steps),
                "completed_steps": len(completed_steps),
                "recovered_from_refresh": resume_point > 0,
                "session_data": user_data
            }
        
        # Test session recovery
        result = await session_based_operation(
            "session_123",
            {"user_id": "user_456", "preferences": {"theme": "dark"}}
        )
        
        assert result["status"] == "completed"
        assert result["recovered_from_refresh"] is True
        assert result["completed_steps"] == 5
        
        # Verify session state was preserved
        session_state = session_storage["session_123"]
        assert "completed_at" in session_state
        assert len(session_state["completed_steps"]) == 5
    
    @pytest.mark.asyncio
    async def test_form_data_recovery(self):
        """Test form data recovery after browser refresh."""
        form_submissions = {}
        
        @recoverable(
            max_retries=1,
            persistence=MemoryPersistence()
        )
        async def form_submission_with_recovery(form_id: str, form_data: dict):
            # Check for partially completed form
            if form_id in form_submissions:
                partial_data = form_submissions[form_id]
                remaining_fields = form_data.keys() - partial_data.get("completed_fields", set())
            else:
                partial_data = {
                    "form_id": form_id,
                    "completed_fields": set(),
                    "validation_results": {}
                }
                remaining_fields = set(form_data.keys())
            
            # Simulate browser refresh during validation
            if len(partial_data["completed_fields"]) == 0:
                partial_data["completed_fields"] = {"field1", "field2"}
                form_submissions[form_id] = partial_data
                raise ConnectionError("Form submission interrupted - browser refresh")
            
            # Continue validation from where we left off
            for field in remaining_fields:
                await asyncio.sleep(0.01)
                
                # Validate field
                if field == "email" and "@" not in form_data.get(field, ""):
                    partial_data["validation_results"][field] = "invalid_email"
                else:
                    partial_data["validation_results"][field] = "valid"
                    partial_data["completed_fields"].add(field)
                
                form_submissions[form_id] = partial_data
            
            return {
                "form_id": form_id,
                "status": "completed",
                "validated_fields": len(partial_data["completed_fields"]),
                "validation_results": partial_data["validation_results"],
                "recovered": len(partial_data.get("completed_fields", set())) > 0
            }
        
        form_data = {
            "field1": "value1",
            "field2": "value2", 
            "email": "test@example.com",
            "field4": "value4"
        }
        
        result = await form_submission_with_recovery("form_789", form_data)
        
        assert result["status"] == "completed"
        assert result["validated_fields"] == 4
        assert result["recovered"] is True
        assert result["validation_results"]["email"] == "valid"


class TestConcurrentRecoveries:
    """Test handling of multiple concurrent recovery operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_download_recoveries(self):
        """Test multiple concurrent download recoveries."""
        download_stats = {}
        
        @recoverable(
            max_retries=2,
            initial_delay=0.05,
            strategy=ExponentialBackoffStrategy(jitter=False)
        )
        async def concurrent_download(model_id: str, url: str):
            if model_id not in download_stats:
                download_stats[model_id] = {
                    "attempts": 0,
                    "bytes_downloaded": 0,
                    "status": "pending"
                }
            
            stats = download_stats[model_id]
            stats["attempts"] += 1
            
            # Simulate failure on first attempt
            if stats["attempts"] == 1:
                stats["bytes_downloaded"] = 500000
                raise ConnectionError(f"Download failed for {model_id}")
            
            # Success on retry
            stats["bytes_downloaded"] = 1000000
            stats["status"] = "completed"
            
            return {
                "model_id": model_id,
                "status": "completed",
                "bytes_downloaded": stats["bytes_downloaded"],
                "attempts": stats["attempts"]
            }
        
        # Run multiple concurrent downloads
        models_to_download = [
            ("model_1", "https://example.com/model1.bin"),
            ("model_2", "https://example.com/model2.bin"),
            ("model_3", "https://example.com/model3.bin"),
            ("model_4", "https://example.com/model4.bin")
        ]
        
        tasks = [
            concurrent_download(model_id, url) 
            for model_id, url in models_to_download
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all downloads completed successfully
        successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "completed"]
        assert len(successful_results) == 4
        
        # Verify recovery stats
        for model_id, _ in models_to_download:
            stats = download_stats[model_id]
            assert stats["attempts"] >= 1
            assert stats["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_mixed_operation_concurrent_recoveries(self):
        """Test concurrent recoveries across different operation types."""
        operation_results = {}
        
        @recoverable(max_retries=1, initial_delay=0.05)
        async def download_operation(op_id: str):
            operation_results[op_id] = {"type": "download", "attempts": 0}
            
            if operation_results[op_id]["attempts"] == 0:
                operation_results[op_id]["attempts"] += 1
                raise ConnectionError("Download failed")
            
            operation_results[op_id]["status"] = "completed"
            return {"op_id": op_id, "result": "download_success"}
        
        @recoverable(max_retries=1, initial_delay=0.05)
        async def install_operation(op_id: str):
            operation_results[op_id] = {"type": "install", "attempts": 0}
            
            if operation_results[op_id]["attempts"] == 0:
                operation_results[op_id]["attempts"] += 1
                raise RuntimeError("Installation failed")
            
            operation_results[op_id]["status"] = "completed"
            return {"op_id": op_id, "result": "install_success"}
        
        @recoverable(max_retries=1, initial_delay=0.05)
        async def import_operation(op_id: str):
            operation_results[op_id] = {"type": "import", "attempts": 0}
            
            if operation_results[op_id]["attempts"] == 0:
                operation_results[op_id]["attempts"] += 1
                raise ValueError("Import validation failed")
            
            operation_results[op_id]["status"] = "completed"
            return {"op_id": op_id, "result": "import_success"}
        
        # Run mixed operations concurrently
        tasks = [
            download_operation("download_1"),
            install_operation("install_1"),
            import_operation("import_1"),
            download_operation("download_2"),
            install_operation("install_2")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == 5
        
        # Verify recovery worked for each operation type
        for op_data in operation_results.values():
            assert op_data["attempts"] >= 1
            assert op_data["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_resource_contention_during_concurrent_recovery(self):
        """Test handling of resource contention during concurrent recoveries."""
        resource_lock = asyncio.Lock()
        resource_usage = {}
        
        @recoverable(
            max_retries=2,
            initial_delay=0.1,
            strategy=LinearBackoffStrategy(delay_increment=0.05)
        )
        async def resource_intensive_operation(op_id: str, resource_name: str):
            async with resource_lock:
                if resource_name not in resource_usage:
                    resource_usage[resource_name] = []
                
                resource_usage[resource_name].append({
                    "op_id": op_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "started"
                })
            
            # Simulate resource contention
            await asyncio.sleep(0.1)
            
            # Simulate failure due to resource contention
            if len(resource_usage[resource_name]) <= 2:
                async with resource_lock:
                    resource_usage[resource_name][-1]["status"] = "failed_contention"
                raise RuntimeError(f"Resource contention on {resource_name}")
            
            # Success after retry
            async with resource_lock:
                resource_usage[resource_name][-1]["status"] = "completed"
            
            return {
                "op_id": op_id,
                "resource": resource_name,
                "status": "completed"
            }
        
        # Run multiple operations competing for the same resource
        tasks = [
            resource_intensive_operation(f"op_{i}", "shared_resource")
            for i in range(4)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations eventually completed
        successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "completed"]
        assert len(successful_results) == 4
        
        # Verify resource usage tracking
        usage_records = resource_usage["shared_resource"]
        assert len(usage_records) >= 4
        
        completed_records = [r for r in usage_records if r["status"] == "completed"]
        assert len(completed_records) == 4


class TestCircuitBreakerRecovery:
    """Test circuit breaker activation and recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self):
        """Test circuit breaker activation after threshold failures."""
        failure_count = 0
        
        @recoverable(
            max_retries=1,
            initial_delay=0.01,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=1.0
        )
        async def unreliable_operation(operation_id: str):
            nonlocal failure_count
            failure_count += 1
            
            # Always fail to trigger circuit breaker
            raise ConnectionError(f"Operation {operation_id} failed")
        
        # Execute operations until circuit breaker opens
        results = []
        for i in range(5):
            try:
                result = await unreliable_operation(f"op_{i}")
                results.append({"status": "success", "result": result})
            except CircuitBreakerOpenError as e:
                results.append({"status": "circuit_open", "error": str(e)})
            except Exception as e:
                results.append({"status": "failed", "error": str(e)})
        
        # Verify circuit breaker activated
        circuit_open_count = len([r for r in results if r["status"] == "circuit_open"])
        assert circuit_open_count >= 2  # Should open after threshold and stay open
        
        # Wait for circuit breaker timeout
        await asyncio.sleep(1.5)
        
        # Test that circuit breaker resets after timeout
        try:
            result = await unreliable_operation("op_after_timeout")
        except CircuitBreakerOpenError:
            # Circuit should be closed now
            assert False, "Circuit breaker should have reset after timeout"
        except Exception:
            # Expected to fail but circuit should be closed
            pass
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state behavior."""
        call_count = 0
        
        @recoverable(
            max_retries=0,
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=0.5
        )
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            
            # Succeed on every third call in half-open state
            if call_count % 3 == 0:
                return {"status": "success", "call": call_count}
            
            raise ConnectionError("Operation failed")
        
        # Trigger circuit breaker
        for i in range(2):
            try:
                await flaky_operation()
            except Exception:
                pass
        
        # Circuit should be open now
        try:
            await flaky_operation()
            assert False, "Should have raised CircuitBreakerOpenError"
        except CircuitBreakerOpenError:
            pass  # Expected
        
        # Wait for timeout
        await asyncio.sleep(0.6)
        
        # Should be in half-open state now - try and succeed
        result = await flaky_operation()
        assert result["status"] == "success"
        
        # Circuit should be closed again
        try:
            await flaky_operation()
        except CircuitBreakerOpenError:
            assert False, "Circuit should be closed after success in half-open"
        except Exception:
            pass  # Regular failure is OK
    
    @pytest.mark.asyncio
    async def test_multiple_circuit_breakers(self):
        """Test multiple independent circuit breakers."""
        circuit_states = {}
        
        @recoverable(
            max_retries=0,
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=0.3
        )
        async def operation_a():
            if "a" not in circuit_states:
                circuit_states["a"] = 0
            circuit_states["a"] += 1
            
            if circuit_states["a"] <= 2:
                raise ConnectionError("Service A down")
            
            return {"service": "A", "status": "success"}
        
        @recoverable(
            max_retries=0,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=0.3
        )
        async def operation_b():
            if "b" not in circuit_states:
                circuit_states["b"] = 0
            circuit_states["b"] += 1
            
            if circuit_states["b"] <= 3:
                raise ConnectionError("Service B down")
            
            return {"service": "B", "status": "success"}
        
        # Test service A circuit breaker
        for i in range(3):
            try:
                await operation_a()
            except CircuitBreakerOpenError:
                break
            except Exception:
                pass
        
        # Test service B circuit breaker  
        for i in range(4):
            try:
                await operation_b()
            except CircuitBreakerOpenError:
                break
            except Exception:
                pass
        
        # Verify both circuit breakers are independent
        # Service A should be open, service B should be open
        
        # Wait for timeouts
        await asyncio.sleep(0.4)
        
        # Test that both circuits reset independently
        result_a = await operation_a()
        result_b = await operation_b()
        
        assert result_a["service"] == "A"
        assert result_b["service"] == "B"


class TestErrorClassificationAndStrategies:
    """Test error classification and retry strategy selection."""
    
    @pytest.mark.asyncio
    async def test_intelligent_error_classification(self):
        """Test intelligent error classification for different scenarios."""
        classifier = ErrorClassifier()
        
        test_errors = [
            # Network errors (should retry)
            (ConnectionError("Connection refused"), ErrorCategory.NETWORK, True),
            (TimeoutError("Request timeout"), ErrorCategory.TIMEOUT, True),
            (aiohttp.ClientError("HTTP error"), ErrorCategory.NETWORK, True),
            
            # Permission errors (should not retry)
            (PermissionError("Access denied"), ErrorCategory.PERMISSION, False),
            (ValueError("Invalid API key"), ErrorCategory.VALIDATION, False),
            
            # Resource errors (should retry)
            (MemoryError("Out of memory"), ErrorCategory.RESOURCE, True),
            (OSError("Disk full"), ErrorCategory.RESOURCE, True),
        ]
        
        for error, expected_category, expected_recoverable in test_errors:
            context = {"operation": "test", "timestamp": datetime.now(timezone.utc).isoformat()}
            classification = classifier.classify(error, context)
            
            assert classification.category == expected_category
            assert classification.is_recoverable == expected_recoverable
    
    @pytest.mark.asyncio
    async def test_strategy_selection_based_on_error(self):
        """Test selection of appropriate retry strategies based on error type."""
        classifier = ErrorClassifier()
        
        @recoverable(
            max_retries=3,
            classifier=classifier
        )
        async def operation_with_intelligent_retry(error_type: str):
            if error_type == "network":
                raise ConnectionError("Network failure")
            elif error_type == "timeout":
                raise TimeoutError("Operation timeout")
            elif error_type == "permission":
                raise PermissionError("Access denied")
            else:
                return {"status": "success"}
        
        # Test network error - should retry with exponential backoff
        try:
            await operation_with_intelligent_retry("network")
            assert False, "Should have failed after retries"
        except RecoveryExhaustedError:
            pass  # Expected
        
        # Test permission error - should not retry
        try:
            await operation_with_intelligent_retry("permission")
            assert False, "Should not retry permission errors"
        except RecoveryExhaustedError as e:
            assert e.attempts == 1  # Should only attempt once
        
        # Test successful operation
        result = await operation_with_intelligent_retry("success")
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_custom_retry_strategies(self):
        """Test custom retry strategies for specific scenarios."""
        
        def fibonacci_delay(attempt):
            if attempt <= 1:
                return 1.0
            a, b = 1, 1
            for _ in range(2, attempt + 1):
                a, b = b, a + b
            return min(b / 10.0, 10.0)  # Scale down and cap at 10s
        
        fibonacci_strategy = CustomStrategy(
            delay_func=fibonacci_delay,
            name="Fibonacci"
        )
        
        attempt_times = []
        
        @recoverable(
            max_retries=3,
            strategy=fibonacci_strategy
        )
        async def operation_with_fibonacci_retry():
            attempt_times.append(time.time())
            if len(attempt_times) <= 3:
                raise ConnectionError("Simulated failure")
            return {"status": "success"}
        
        start_time = time.time()
        try:
            await operation_with_fibonacci_retry()
        except RecoveryExhaustedError:
            pass
        
        # Verify Fibonacci-like delays
        if len(attempt_times) >= 2:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            # Second delay should be longer than first (Fibonacci pattern)
            assert delay2 > delay1


class TestPerformanceAndLoad:
    """Test performance impact and load handling of recovery system."""
    
    @pytest.mark.asyncio
    async def test_recovery_performance_overhead(self):
        """Test performance overhead introduced by recovery system."""
        
        @recoverable(max_retries=0)  # No retries, just decorator overhead
        async def operation_with_recovery(data_size: int):
            # Simulate work
            data = [i for i in range(data_size)]
            return {"processed": len(data)}
        
        async def operation_without_recovery(data_size: int):
            # Same operation without recovery
            data = [i for i in range(data_size)]
            return {"processed": len(data)}
        
        # Measure performance with recovery
        start_time = time.time()
        for i in range(100):
            await operation_with_recovery(1000)
        recovery_time = time.time() - start_time
        
        # Measure performance without recovery
        start_time = time.time()
        for i in range(100):
            await operation_without_recovery(1000)
        baseline_time = time.time() - start_time
        
        # Calculate overhead
        overhead_percentage = ((recovery_time - baseline_time) / baseline_time) * 100
        
        # Overhead should be reasonable (less than 50%)
        assert overhead_percentage < 50.0
        
        # Log performance metrics
        print(f"Recovery overhead: {overhead_percentage:.2f}%")
        print(f"Baseline time: {baseline_time:.3f}s")
        print(f"Recovery time: {recovery_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_load_with_recovery(self):
        """Test system behavior under load with concurrent recovery operations."""
        operation_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "recovery_attempts": 0,
            "execution_times": []
        }
        
        @recoverable(
            max_retries=2,
            initial_delay=0.01,
            strategy=ExponentialBackoffStrategy(jitter=False)
        )
        async def load_test_operation(operation_id: str, failure_rate: float = 0.3):
            start_time = time.time()
            operation_stats["total_operations"] += 1
            
            # Simulate failure based on rate
            if operation_stats["recovery_attempts"] == 0 and hash(operation_id) % 100 < int(failure_rate * 100):
                operation_stats["recovery_attempts"] += 1
                raise ConnectionError(f"Load-induced failure for {operation_id}")
            
            execution_time = time.time() - start_time
            operation_stats["execution_times"].append(execution_time)
            operation_stats["successful_operations"] += 1
            
            return {
                "operation_id": operation_id,
                "status": "completed",
                "execution_time": execution_time
            }
        
        # Run load test with concurrent operations
        num_operations = 50
        tasks = [
            load_test_operation(f"load_op_{i}") 
            for i in range(num_operations)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        success_rate = len(successful_results) / num_operations * 100
        avg_execution_time = sum(operation_stats["execution_times"]) / len(operation_stats["execution_times"]) if operation_stats["execution_times"] else 0
        operations_per_second = num_operations / total_time
        
        # Verify load handling
        assert success_rate >= 80.0  # At least 80% success rate
        assert operations_per_second >= 10.0  # At least 10 ops/sec
        
        print(f"Load test results:")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Operations/sec: {operations_per_second:.1f}")
        print(f"  Avg execution time: {avg_execution_time:.3f}s")
        print(f"  Total time: {total_time:.3f}s")


@pytest.mark.asyncio
async def test_comprehensive_recovery_integration():
    """Comprehensive integration test covering all recovery scenarios."""
    
    # Create test suite
    test_suite = RecoveryTestSuite()
    
    # Run all recovery tests
    results = await test_suite.run_all_tests()
    summary = test_suite.get_test_summary()
    
    # Verify comprehensive coverage
    assert summary["total_tests"] >= 4  # At least 4 main scenarios
    assert summary["success_rate"] >= 75.0  # At least 75% success rate
    
    # Verify specific scenarios were tested
    test_names = [result.scenario_name for result in results]
    expected_scenarios = [
        "network_interruption_model_download",
        "app_crash_workflow_import", 
        "browser_refresh_installation",
        "concurrent_recoveries"
    ]
    
    for scenario in expected_scenarios:
        assert any(scenario in name for name in test_names), f"Scenario {scenario} not found in tests"
    
    print(f"Comprehensive recovery test summary:")
    print(f"  Total tests: {summary['total_tests']}")
    print(f"  Passed: {summary['passed_tests']}")
    print(f"  Failed: {summary['failed_tests']}")
    print(f"  Success rate: {summary['success_rate']:.1f}%")
    print(f"  Avg execution time: {summary['average_execution_time']:.2f}s")
    
    return summary


if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(test_comprehensive_recovery_integration())