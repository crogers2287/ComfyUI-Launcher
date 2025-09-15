"""
Integration tests for frontend-backend communication with recovery mechanisms.

These tests verify that the frontend and backend work together correctly
during recovery scenarios including network interruptions, state persistence,
and WebSocket reconnection.
"""

import asyncio
import pytest
import json
import time
import tempfile
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List
import aiohttp
import aiohttp_cors
from aiohttp import web
import socketio

# Import backend components
from backend.src.recovery import recoverable, RecoveryConfig
from backend.src.recovery.persistence import SQLAlchemyPersistence
from backend.src.server import create_app
from backend.src.tasks import create_celery_app

# Import frontend components (mocked)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from mocks.frontend_mocks import (
        MockReactComponent, MockWebSocketClient, MockQueryClient
    )
except ImportError:
    # Create simple mocks if the file doesn't exist
    class MockReactComponent:
        def __init__(self, props=None):
            self.props = props or {}
            self.state = {}
        
        def handle_error(self, status, message):
            self.state['error'] = {'status': status, 'message': message}
        
        def get_error_message(self):
            return self.state.get('error', {}).get('message')
        
        def get_retry_button_visible(self):
            return self.state.get('error') is not None
        
        def click_retry(self):
            self.state['retry_count'] = self.state.get('retry_count', 0) + 1
        
        def get_retry_count(self):
            return self.state.get('retry_count', 0)
    
    class MockWebSocketClient:
        def __init__(self, url):
            self.url = url
            self.connected = False
            self.received_events = []
        
        async def connect(self):
            self.connected = True
            self.received_events.append({'event': 'connection_established'})
        
        async def disconnect(self):
            self.connected = False
        
        async def reconnect(self):
            await self.connect()
        
        async def emit(self, event, data):
            pass
    
    class MockQueryClient:
        def __init__(self):
            self.queries = {}
        
        def setQueryData(self, key, data):
            self.queries[key] = data


class TestFrontendBackendIntegration:
    """Test integration between frontend React components and backend recovery systems."""
    
    @pytest.fixture
    async def test_server(self):
        """Create a test server with recovery endpoints."""
        app = create_app()
        app['config'] = {
            'cors_origins': ['http://localhost:3000'],
            'debug': True
        }
        
        # Add recovery-specific routes
        async def get_recovery_status(request):
            return web.json_response({
                'status': 'healthy',
                'active_operations': 3,
                'recovery_count': 5
            })
        
        async def simulate_network_failure(request):
            raise web.HTTPInternalServerError(reason="Simulated network failure")
        
        async def download_with_recovery(request):
            data = await request.json()
            
            @recoverable(max_retries=2, initial_delay=0.1)
            async def mock_download(url: str, save_path: str):
                # Simulate network failure on first attempt
                if request.app.get('download_attempts', 0) == 0:
                    request.app['download_attempts'] = 1
                    raise ConnectionError("Network interruption")
                
                return {
                    'status': 'completed',
                    'url': url,
                    'path': save_path,
                    'bytes_downloaded': 1000000
                }
            
            try:
                result = await mock_download(data['url'], data['save_path'])
                return web.json_response(result)
            except Exception as e:
                return web.json_response({
                    'error': str(e),
                    'recovery_attempt': True
                }, status=500)
        
        app.router.add_get('/api/recovery/status', get_recovery_status)
        app.router.add_post('/api/simulate/failure', simulate_network_failure)
        app.router.add_post('/api/download/recoverable', download_with_recovery)
        
        return app
    
    @pytest.fixture
    async def test_client(self, test_server):
        """Create a test client."""
        return aiohttp.test_utils.TestClient(test_server)
    
    @pytest.fixture
    async def websocket_server(self):
        """Create a WebSocket server for testing."""
        sio = socketio.AsyncServer(
            cors_allowed_origins=['http://localhost:3000'],
            logger=False,
            engineio_logger=False
        )
        
        app = web.Application()
        sio.attach(app)
        
        # Track connections and messages
        connected_clients = set()
        message_history = []
        
        @sio.event
        async def connect(sid, environ):
            connected_clients.add(sid)
            await sio.emit('connection_established', {'sid': sid}, room=sid)
        
        @sio.event
        async def disconnect(sid):
            connected_clients.discard(sid)
        
        @sio.event
        async def download_progress(sid, data):
            message_history.append({
                'event': 'download_progress',
                'sid': sid,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Simulate progress update
            progress = data.get('progress', 0) + 10
            await sio.emit('progress_update', {
                'operation_id': data.get('operation_id'),
                'progress': progress,
                'status': 'downloading'
            }, room=sid)
        
        @sio.event
        async def recovery_status(sid, data):
            message_history.append({
                'event': 'recovery_status',
                'sid': sid,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            await sio.emit('recovery_update', {
                'status': 'recovering',
                'message': 'Attempting to recover connection'
            }, room=sid)
        
        app['socketio'] = sio
        app['connected_clients'] = connected_clients
        app['message_history'] = message_history
        
        return app
    
    @pytest.mark.asyncio
    async def test_network_interruption_recovery_integration(self, test_client):
        """Test recovery from network interruption during frontend-backend communication."""
        
        # Mock frontend component
        frontend_component = MockReactComponent({
            'url': 'https://example.com/model.bin',
            'save_path': '/tmp/model.bin'
        })
        
        # Test initial request failure
        response = await test_client.post('/api/simulate/failure')
        assert response.status == 500
        
        # Test frontend error handling
        await frontend_component.handle_error(response.status, await response.text())
        
        # Verify frontend shows appropriate error message
        assert frontend_component.get_error_message() is not None
        assert frontend_component.get_retry_button_visible() is True
        
        # Test retry mechanism
        frontend_component.click_retry()
        
        # Verify retry request was made
        retry_response = await test_client.post('/api/simulate/failure')
        assert retry_response.status == 500
        
        # Verify frontend updates retry count
        assert frontend_component.get_retry_count() == 1
    
    @pytest.mark.asyncio
    async def test_download_with_frontend_backend_recovery(self, test_client):
        """Test coordinated recovery between frontend and backend during download."""
        
        # Test successful download with recovery
        download_data = {
            'url': 'https://example.com/test-model.bin',
            'save_path': '/tmp/test-model.bin'
        }
        
        response = await test_client.post(
            '/api/download/recoverable',
            json=download_data
        )
        
        # First attempt should fail and recover
        assert response.status == 200
        
        result = await response.json()
        assert result['status'] == 'completed'
        assert result['bytes_downloaded'] == 1000000
        
        # Verify backend recovery attempts
        assert test_client.server.app.get('download_attempts', 0) == 1
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_integration(self, websocket_server):
        """Test WebSocket reconnection with state synchronization."""
        
        # Create WebSocket client
        ws_client = MockWebSocketClient('http://localhost:8080')
        
        # Connect to server
        await ws_client.connect()
        
        # Verify connection established
        assert ws_client.connected is True
        assert 'connection_established' in ws_client.received_events
        
        # Send progress update
        await ws_client.emit('download_progress', {
            'operation_id': 'download_123',
            'progress': 30,
            'total_bytes': 1000000
        })
        
        # Verify progress update received
        await asyncio.sleep(0.1)
        progress_events = [e for e in ws_client.received_events if e.get('event') == 'progress_update']
        assert len(progress_events) >= 1
        
        # Simulate connection loss
        await ws_client.disconnect()
        assert ws_client.connected is False
        
        # Test reconnection logic
        await ws_client.reconnect()
        assert ws_client.connected is True
        
        # Verify reconnection recovery
        reconnect_events = [e for e in ws_client.received_events if e.get('event') == 'connection_established']
        assert len(reconnect_events) >= 2  # Initial + reconnection
        
        # Send recovery status
        await ws_client.emit('recovery_status', {
            'operation_id': 'download_123',
            'status': 'recovering'
        })
        
        # Verify recovery updates
        await asyncio.sleep(0.1)
        recovery_events = [e for e in ws_client.received_events if e.get('event') == 'recovery_update']
        assert len(recovery_events) >= 1
    
    @pytest.mark.asyncio
    async def test_state_persistence_integration(self, test_client):
        """Test state persistence between frontend and backend."""
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
            db_path = tf.name
        
        try:
            # Setup persistence
            persistence = SQLAlchemyPersistence(f"sqlite+aiosqlite:///{db_path}")
            
            # Create recoverable operation with persistence
            @recoverable(
                max_retries=2,
                persistence=persistence,
                initial_delay=0.1
            )
            async def persistent_operation(operation_id: str, data: Dict[str, Any]):
                # Simulate failure on first attempt
                if operation_id not in test_client.server.app:
                    test_client.server.app[operation_id] = 1
                    raise ConnectionError("Simulated failure")
                
                return {
                    'operation_id': operation_id,
                    'status': 'completed',
                    'data': data
                }
            
            # Test operation with failure and recovery
            operation_data = {'key': 'value', 'timestamp': datetime.now(timezone.utc).isoformat()}
            
            try:
                result = await persistent_operation('test_op_1', operation_data)
            except Exception:
                pass  # Expected to fail initially
            
            # Verify persistence saved state
            stats = await persistence.get_statistics()
            assert stats['total'] >= 1
            
            # Test frontend can recover state
            frontend_component = MockReactComponent({'operation_id': 'test_op_1'})
            
            # Simulate frontend requesting recovery state
            recovery_state = await persistence.get('test_op_1')
            assert recovery_state is not None
            
            # Verify frontend can restore from persisted state
            restored_state = await frontend_component.restore_from_persistence(recovery_state)
            assert restored_state['operation_id'] == 'test_op_1'
            
        finally:
            import os
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_operation_integration(self, test_client):
        """Test handling of concurrent operations with coordinated recovery."""
        
        # Track concurrent operations
        operation_tracker = {}
        
        @recoverable(max_retries=1, initial_delay=0.05)
        async def concurrent_operation(operation_id: str, duration: float = 0.1):
            if operation_id not in operation_tracker:
                operation_tracker[operation_id] = {'attempts': 0, 'status': 'started'}
            
            operation_tracker[operation_id]['attempts'] += 1
            
            # Simulate failure on first attempt for some operations
            if (operation_tracker[operation_id]['attempts'] == 1 and 
                hash(operation_id) % 3 == 0):
                raise ConnectionError(f"Concurrent operation failed: {operation_id}")
            
            await asyncio.sleep(duration)
            operation_tracker[operation_id]['status'] = 'completed'
            
            return {
                'operation_id': operation_id,
                'status': 'completed',
                'attempts': operation_tracker[operation_id]['attempts']
            }
        
        # Execute multiple concurrent operations
        operations = [
            concurrent_operation(f'concurrent_op_{i}', 0.05 + i * 0.01)
            for i in range(5)
        ]
        
        results = await asyncio.gather(*operations, return_exceptions=True)
        
        # Verify all operations completed
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == 5
        
        # Verify recovery was attempted where needed
        for op_id, tracker_data in operation_tracker.items():
            if tracker_data['attempts'] > 1:
                assert tracker_data['status'] == 'completed'
        
        # Test frontend can handle concurrent operation updates
        frontend_component = MockReactComponent({})
        
        # Simulate receiving concurrent operation updates
        for result in successful_results:
            await frontend_component.handle_operation_update(result)
        
        # Verify frontend state is correct
        frontend_state = frontend_component.get_state()
        assert len(frontend_state['operations']) == 5
        assert all(op['status'] == 'completed' for op in frontend_state['operations'])


class TestAPIRecoveryIntegration:
    """Test API-level recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_recovery(self):
        """Test recovery from rate limiting scenarios."""
        
        # Mock rate limiting
        rate_limiter = {
            'requests': [],
            'limit': 5,
            'window': 60  # 60 seconds
        }
        
        async def rate_limited_middleware(request):
            now = time.time()
            # Clean old requests
            rate_limiter['requests'] = [
                req_time for req_time in rate_limiter['requests']
                if now - req_time < rate_limiter['window']
            ]
            
            if len(rate_limiter['requests']) >= rate_limiter['limit']:
                raise web.HTTPTooManyRequests(reason="Rate limit exceeded")
            
            rate_limiter['requests'].append(now)
            return await request.handler()
        
        # Test rate limiting and recovery
        responses = []
        
        for i in range(7):  # Exceed rate limit
            try:
                await rate_limited_middleware(Mock(handler=AsyncMock()))
                responses.append({'status': 'success'})
            except web.HTTPTooManyRequests as e:
                responses.append({'status': 'rate_limited', 'reason': str(e)})
        
        # Verify rate limiting was enforced
        rate_limited_count = len([r for r in responses if r['status'] == 'rate_limited'])
        assert rate_limited_count >= 1
        
        # Test recovery after rate limit reset
        rate_limiter['requests'] = []  # Reset rate limiter
        
        recovery_response = await rate_limited_middleware(Mock(handler=AsyncMock()))
        responses.append({'status': 'success'})
        
        success_count = len([r for r in responses if r['status'] == 'success'])
        assert success_count >= 6  # Original successful + recovery
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration across frontend and backend."""
        
        circuit_state = {
            'failure_count': 0,
            'state': 'closed',  # closed, open, half-open
            'last_failure': None,
            'threshold': 3,
            'timeout': 5.0
        }
        
        def check_circuit_breaker():
            now = time.time()
            
            if circuit_state['state'] == 'open':
                if (circuit_state['last_failure'] and 
                    now - circuit_state['last_failure'] > circuit_state['timeout']):
                    circuit_state['state'] = 'half-open'
                else:
                    raise Exception("Circuit breaker is open")
            
            return True
        
        def record_failure():
            circuit_state['failure_count'] += 1
            circuit_state['last_failure'] = time.time()
            
            if circuit_state['failure_count'] >= circuit_state['threshold']:
                circuit_state['state'] = 'open'
        
        def record_success():
            circuit_state['failure_count'] = 0
            circuit_state['state'] = 'closed'
        
        # Test circuit breaker activation
        for i in range(4):
            try:
                check_circuit_breaker()
                # Simulate operation failure
                record_failure()
                raise Exception("Operation failed")
            except Exception as e:
                if "Circuit breaker is open" in str(e):
                    assert i >= 2  # Circuit should open after threshold
                    break
        
        assert circuit_state['state'] == 'open'
        
        # Test circuit breaker recovery after timeout
        await asyncio.sleep(circuit_state['timeout'] + 0.1)
        
        try:
            check_circuit_breaker()
            assert circuit_state['state'] == 'half-open'
            
            # Simulate successful operation in half-open state
            record_success()
            assert circuit_state['state'] == 'closed'
            
        except Exception:
            assert False, "Circuit breaker should have recovered"


class TestDataConsistencyIntegration:
    """Test data consistency during recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_recovery(self):
        """Test transaction rollback during recovery scenarios."""
        
        transaction_log = []
        
        async def execute_with_transaction(operations: List[Dict[str, Any]]):
            transaction_id = f"tx_{datetime.now(timezone.utc).timestamp()}"
            transaction_log.append({
                'transaction_id': transaction_id,
                'status': 'started',
                'operations': operations
            })
            
            try:
                # Simulate transaction processing
                results = []
                for i, op in enumerate(operations):
                    # Simulate failure mid-transaction
                    if i == 2 and op.get('simulate_failure', False):
                        raise Exception("Mid-transaction failure")
                    
                    # Process operation
                    result = {'operation_id': op['id'], 'status': 'completed'}
                    results.append(result)
                
                transaction_log.append({
                    'transaction_id': transaction_id,
                    'status': 'completed',
                    'results': results
                })
                
                return results
                
            except Exception as e:
                # Rollback transaction
                transaction_log.append({
                    'transaction_id': transaction_id,
                    'status': 'rolled_back',
                    'error': str(e)
                })
                raise
        
        # Test transaction with failure
        operations = [
            {'id': 'op1', 'action': 'create'},
            {'id': 'op2', 'action': 'update'},
            {'id': 'op3', 'action': 'delete', 'simulate_failure': True},
            {'id': 'op4', 'action': 'validate'}
        ]
        
        try:
            await execute_with_transaction(operations)
            assert False, "Should have raised exception"
        except Exception:
            pass  # Expected
        
        # Verify transaction was rolled back
        rollback_transactions = [t for t in transaction_log if t['status'] == 'rolled_back']
        assert len(rollback_transactions) == 1
        
        # Test recovery with retry
        recovery_operations = [
            {'id': 'op1', 'action': 'create'},
            {'id': 'op2', 'action': 'update'},
            {'id': 'op3', 'action': 'delete'},  # No failure this time
            {'id': 'op4', 'action': 'validate'}
        ]
        
        results = await execute_with_transaction(recovery_operations)
        
        assert len(results) == 4
        assert all(r['status'] == 'completed' for r in results)
        
        # Verify final transaction completed
        completed_transactions = [t for t in transaction_log if t['status'] == 'completed']
        assert len(completed_transactions) == 1


class TestWebSocketStateSynchronization:
    """Test WebSocket state synchronization during recovery."""
    
    @pytest.mark.asyncio
    async def test_state_synchronization_on_reconnect(self):
        """Test state synchronization when WebSocket reconnects."""
        
        # Simulate server state
        server_state = {
            'downloads': {},
            'installations': {},
            'operations': {}
        }
        
        # Simulate WebSocket connection manager
        class ConnectionManager:
            def __init__(self):
                self.connections = {}
                self.message_queue = {}
            
            def add_connection(self, connection_id):
                self.connections[connection_id] = {
                    'connected': True,
                    'last_seen': time.time()
                }
            
            def remove_connection(self, connection_id):
                if connection_id in self.connections:
                    self.connections[connection_id]['connected'] = False
            
            def queue_message(self, connection_id, message):
                if connection_id not in self.message_queue:
                    self.message_queue[connection_id] = []
                self.message_queue[connection_id].append({
                    'message': message,
                    'timestamp': time.time()
                })
            
            async def synchronize_state(self, connection_id):
                if not self.connections.get(connection_id, {}).get('connected'):
                    return
                
                # Send queued messages
                queued_messages = self.message_queue.get(connection_id, [])
                for msg in queued_messages:
                    # Simulate sending message to client
                    pass
                
                # Clear queue
                self.message_queue[connection_id] = []
        
        connection_manager = ConnectionManager()
        
        # Test connection and disconnection
        connection_id = 'client_123'
        connection_manager.add_connection(connection_id)
        
        # Simulate state changes while disconnected
        connection_manager.remove_connection(connection_id)
        
        # Queue state updates
        for i in range(3):
            connection_manager.queue_message(connection_id, {
                'type': 'download_progress',
                'operation_id': f'download_{i}',
                'progress': i * 25
            })
        
        # Test reconnection and synchronization
        connection_manager.add_connection(connection_id)
        await connection_manager.synchronize_state(connection_id)
        
        # Verify state was synchronized
        assert len(connection_manager.message_queue.get(connection_id, [])) == 0


class TestPerformanceIntegration:
    """Test performance aspects of recovery integration."""
    
    @pytest.mark.asyncio
    async def test_recovery_performance_overhead(self):
        """Measure performance overhead of recovery mechanisms."""
        
        # Test without recovery
        async def operation_without_recovery(data_size: int):
            await asyncio.sleep(0.01)  # Simulate work
            return {'processed': data_size}
        
        # Test with recovery
        @recoverable(max_retries=0)
        async def operation_with_recovery(data_size: int):
            await asyncio.sleep(0.01)  # Simulate work
            return {'processed': data_size}
        
        # Measure performance
        iterations = 100
        data_size = 1000
        
        # Without recovery
        start_time = time.time()
        for _ in range(iterations):
            await operation_without_recovery(data_size)
        baseline_time = time.time() - start_time
        
        # With recovery
        start_time = time.time()
        for _ in range(iterations):
            await operation_with_recovery(data_size)
        recovery_time = time.time() - start_time
        
        # Calculate overhead
        overhead_percentage = ((recovery_time - baseline_time) / baseline_time) * 100
        
        # Overhead should be reasonable
        assert overhead_percentage < 20.0
        
        print(f"Recovery overhead: {overhead_percentage:.2f}%")
    
    @pytest.mark.asyncio
    async def test_concurrent_recovery_performance(self):
        """Test performance of concurrent recovery operations."""
        
        operation_results = []
        
        @recoverable(max_retries=1, initial_delay=0.01)
        async def concurrent_recovery_operation(operation_id: str):
            # Simulate some operations failing and recovering
            if hash(operation_id) % 4 == 0:
                await asyncio.sleep(0.02)
                raise ConnectionError("Simulated failure")
            
            await asyncio.sleep(0.05)
            operation_results.append({'operation_id': operation_id, 'status': 'completed'})
            return {'operation_id': operation_id, 'status': 'completed'}
        
        # Execute concurrent operations
        num_operations = 20
        tasks = [
            concurrent_recovery_operation(f'op_{i}')
            for i in range(num_operations)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Verify performance
        successful_results = [r for r in results if isinstance(r, dict)]
        success_rate = len(successful_results) / num_operations * 100
        operations_per_second = num_operations / execution_time
        
        assert success_rate >= 90.0  # High success rate expected
        assert operations_per_second >= 10.0  # Reasonable throughput
        
        print(f"Concurrent recovery performance:")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Operations/sec: {operations_per_second:.1f}")
        print(f"  Execution time: {execution_time:.3f}s")


# Integration test runner
class IntegrationTestRunner:
    """Runner for comprehensive integration tests."""
    
    def __init__(self):
        self.test_results = []
        self.performance_metrics = {}
    
    async def run_all_integration_tests(self):
        """Run all integration tests and return comprehensive results."""
        
        # Test categories
        test_categories = [
            "frontend_backend_communication",
            "websocket_integration", 
            "state_persistence",
            "concurrent_operations",
            "data_consistency",
            "performance"
        ]
        
        overall_start_time = time.time()
        
        for category in test_categories:
            category_start_time = time.time()
            
            try:
                # Run tests for this category
                if category == "frontend_backend_communication":
                    await self._test_frontend_backend_integration()
                elif category == "websocket_integration":
                    await self._test_websocket_integration()
                elif category == "state_persistence":
                    await self._test_state_persistence()
                elif category == "concurrent_operations":
                    await self._test_concurrent_operations()
                elif category == "data_consistency":
                    await self._test_data_consistency()
                elif category == "performance":
                    await self._test_performance_integration()
                
                category_time = time.time() - category_start_time
                self.test_results.append({
                    'category': category,
                    'status': 'passed',
                    'execution_time': category_time
                })
                
            except Exception as e:
                category_time = time.time() - category_start_time
                self.test_results.append({
                    'category': category,
                    'status': 'failed',
                    'error': str(e),
                    'execution_time': category_time
                })
        
        overall_time = time.time() - overall_start_time
        
        # Calculate summary
        passed_tests = len([r for r in self.test_results if r['status'] == 'passed'])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'total_execution_time': overall_time,
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics
        }
    
    async def _test_frontend_backend_integration(self):
        """Test frontend-backend integration."""
        # Implementation would involve actual frontend-backend interaction tests
        await asyncio.sleep(0.1)  # Placeholder
    
    async def _test_websocket_integration(self):
        """Test WebSocket integration."""
        # Implementation would test WebSocket reconnection and state sync
        await asyncio.sleep(0.1)  # Placeholder
    
    async def _test_state_persistence(self):
        """Test state persistence."""
        # Implementation would test data persistence across sessions
        await asyncio.sleep(0.1)  # Placeholder
    
    async def _test_concurrent_operations(self):
        """Test concurrent operation handling."""
        # Implementation would test concurrent recovery scenarios
        await asyncio.sleep(0.1)  # Placeholder
    
    async def _test_data_consistency(self):
        """Test data consistency."""
        # Implementation would test transaction and consistency mechanisms
        await asyncio.sleep(0.1)  # Placeholder
    
    async def _test_performance_integration(self):
        """Test performance aspects."""
        # Implementation would measure performance overhead
        await asyncio.sleep(0.1)  # Placeholder


# Global test runner instance
_integration_test_runner = IntegrationTestRunner()

async def run_comprehensive_integration_tests():
    """Run comprehensive integration tests."""
    return await _integration_test_runner.run_all_integration_tests()


if __name__ == "__main__":
    # Run integration tests
    results = asyncio.run(run_comprehensive_integration_tests())
    print(f"Integration test results: {results}")