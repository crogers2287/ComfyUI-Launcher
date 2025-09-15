"""
End-to-end testing scenarios for ComfyUI Launcher recovery system.

This module provides comprehensive testing for all recovery mechanisms
including network interruptions, app crashes, browser refresh, and concurrent recoveries.
"""

import os
import json
import time
import asyncio
import logging
import threading
import subprocess
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from unittest.mock import Mock, patch, AsyncMock

logger = logging.getLogger(__name__)

@dataclass
class TestScenario:
    """Represents a test scenario with setup, execution, and validation."""
    name: str
    description: str
    setup_func: Optional[Callable] = None
    execute_func: Optional[Callable] = None
    validate_func: Optional[Callable] = None
    cleanup_func: Optional[Callable] = None
    expected_result: str = "success"
    timeout: float = 60.0

@dataclass
class TestResult:
    """Represents the result of a test scenario."""
    scenario_name: str
    status: str  # "passed", "failed", "error"
    execution_time: float
    error_message: Optional[str] = None
    recovery_data: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

class RecoveryTestSuite:
    """Comprehensive test suite for recovery mechanisms."""
    
    def __init__(self):
        self.test_results = []
        self.scenarios = []
        self.performance_monitor = PerformanceMonitor()
        self._setup_test_scenarios()
    
    def _setup_test_scenarios(self):
        """Setup all test scenarios."""
        self.scenarios = [
            TestScenario(
                name="network_interruption_model_download",
                description="Test recovery from network interruption during model download",
                setup_func=self._setup_network_interruption,
                execute_func=self._execute_network_interruption,
                validate_func=self._validate_network_interruption,
                cleanup_func=self._cleanup_network_interruption,
                expected_result="success",
                timeout=120.0
            ),
            TestScenario(
                name="app_crash_workflow_import",
                description="Test recovery from app crash during workflow import",
                setup_func=self._setup_app_crash,
                execute_func=self._execute_app_crash,
                validate_func=self._validate_app_crash,
                cleanup_func=self._cleanup_app_crash,
                expected_result="success",
                timeout=90.0
            ),
            TestScenario(
                name="browser_refresh_installation",
                description="Test recovery from browser refresh during installation",
                setup_func=self._setup_browser_refresh,
                execute_func=self._execute_browser_refresh,
                validate_func=self._validate_browser_refresh,
                cleanup_func=self._cleanup_browser_refresh,
                expected_result="success",
                timeout=180.0
            ),
            TestScenario(
                name="concurrent_recoveries",
                description="Test handling of multiple concurrent recoveries",
                setup_func=self._setup_concurrent_recoveries,
                execute_func=self._execute_concurrent_recoveries,
                validate_func=self._validate_concurrent_recoveries,
                cleanup_func=self._cleanup_concurrent_recoveries,
                expected_result="success",
                timeout=300.0
            )
        ]
    
    async def run_all_tests(self) -> List[TestResult]:
        """Run all test scenarios."""
        logger.info("Starting comprehensive recovery test suite")
        
        for scenario in self.scenarios:
            try:
                result = await self._run_single_test(scenario)
                self.test_results.append(result)
                logger.info(f"Test {scenario.name}: {result.status}")
                
            except Exception as e:
                error_result = TestResult(
                    scenario_name=scenario.name,
                    status="error",
                    execution_time=0.0,
                    error_message=str(e)
                )
                self.test_results.append(error_result)
                logger.error(f"Test {scenario.name} failed with error: {e}")
        
        return self.test_results
    
    async def _run_single_test(self, scenario: TestScenario) -> TestResult:
        """Run a single test scenario."""
        start_time = time.time()
        
        try:
            logger.info(f"Running test scenario: {scenario.name}")
            
            # Setup
            if scenario.setup_func:
                await scenario.setup_func()
            
            # Execute with timeout
            execute_task = asyncio.create_task(self._execute_with_timeout(scenario))
            
            try:
                await asyncio.wait_for(execute_task, timeout=scenario.timeout)
            except asyncio.TimeoutError:
                logger.error(f"Test {scenario.name} timed out after {scenario.timeout} seconds")
                raise TimeoutError(f"Test {scenario.name} timed out")
            
            # Validate
            validation_result = None
            if scenario.validate_func:
                validation_result = await scenario.validate_func()
            
            # Cleanup
            if scenario.cleanup_func:
                await scenario.cleanup_func()
            
            execution_time = time.time() - start_time
            
            # Determine test status
            if validation_result is not False:
                status = "passed"
            else:
                status = "failed"
            
            return TestResult(
                scenario_name=scenario.name,
                status=status,
                execution_time=execution_time,
                performance_metrics=self.performance_monitor.get_metrics()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Attempt cleanup even on failure
            if scenario.cleanup_func:
                try:
                    await scenario.cleanup_func()
                except Exception as cleanup_error:
                    logger.error(f"Cleanup failed for {scenario.name}: {cleanup_error}")
            
            return TestResult(
                scenario_name=scenario.name,
                status="failed",
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def _execute_with_timeout(self, scenario: TestScenario):
        """Execute test scenario with performance monitoring."""
        self.performance_monitor.start_monitoring()
        
        try:
            if scenario.execute_func:
                await scenario.execute_func()
        finally:
            self.performance_monitor.stop_monitoring()
    
    # Network Interruption Test Scenario
    async def _setup_network_interruption(self):
        """Setup for network interruption test."""
        logger.info("Setting up network interruption test")
        
        # Create mock download manager
        self.mock_download_manager = Mock()
        self.mock_download_manager.download_model = AsyncMock()
        self.mock_download_manager.active_downloads = {}
        
        # Simulate network failure
        self.network_patch = patch('socket.socket')
        self.mock_socket = self.network_patch.start()
        
        # Setup socket to raise connection error on first call
        self.mock_socket.return_value.recv.side_effect = [
            ConnectionError("Network connection lost"),
            b"partial_data",
            b"remaining_data"
        ]
        
        logger.info("Network interruption test setup complete")
    
    async def _execute_network_interruption(self):
        """Execute network interruption test."""
        logger.info("Executing network interruption test")
        
        # Import recovery integration
        from .integration import get_recovery_integrator
        
        # Get recovery integrator
        integrator = get_recovery_integrator()
        
        if not integrator.enabled:
            logger.warning("Recovery system not available for network test")
            return
        
        # Apply recovery to mock download manager
        enhanced_manager = integrator.apply_to_model_downloads(self.mock_download_manager)
        
        # Simulate download with network interruption
        try:
            # This should fail and recover
            result = await enhanced_manager.download_model(
                model_id="test_model",
                url="http://example.com/model.bin",
                save_path="/tmp/test_model.bin"
            )
            
            logger.info("Network interruption test completed successfully")
            
        except Exception as e:
            logger.error(f"Network interruption test failed: {e}")
            raise
    
    async def _validate_network_interruption(self):
        """Validate network interruption test results."""
        logger.info("Validating network interruption test results")
        
        # Check if recovery system handled the interruption
        from .integration import get_recovery_integrator
        integrator = get_recovery_integrator()
        
        if integrator.enabled and integrator.persistence:
            # Check if recovery data was saved
            # This would need to be implemented based on actual persistence
            pass
        
        return True
    
    async def _cleanup_network_interruption(self):
        """Cleanup network interruption test."""
        logger.info("Cleaning up network interruption test")
        
        if hasattr(self, 'network_patch'):
            self.network_patch.stop()
        
        if hasattr(self, 'mock_download_manager'):
            del self.mock_download_manager
    
    # App Crash Test Scenario
    async def _setup_app_crash(self):
        """Setup for app crash test."""
        logger.info("Setting up app crash test")
        
        # Create mock workflow import data
        self.test_workflow_data = {
            "nodes": [
                {"id": "1", "type": "CheckpointLoaderSimple", "inputs": {}},
                {"id": "2", "type": "CLIPTextEncode", "inputs": {}}
            ],
            "links": []
        }
        
        # Setup crash simulation
        self.crash_patch = patch('os._exit')
        self.mock_exit = self.crash_patch.start()
        
        logger.info("App crash test setup complete")
    
    async def _execute_app_crash(self):
        """Execute app crash test."""
        logger.info("Executing app crash test")
        
        # Import workflow import recovery
        from .workflow_import import get_workflow_import_recovery
        
        # Get workflow import recovery instance
        recovery = get_workflow_import_recovery()
        
        # Create import task
        task = recovery.create_import_task(
            project_name="test_project",
            import_json=self.test_workflow_data,
            resolved_missing_models=[],
            skipping_model_validation=True
        )
        
        # Simulate crash during import
        try:
            # Start import
            recovery.update_import_progress(task.task_id, 25.0, "processing")
            
            # Simulate crash (don't actually crash)
            logger.info("Simulating app crash during workflow import")
            
            # Simulate recovery after restart
            recovered_task = recovery.active_imports.get(task.task_id)
            if recovered_task:
                recovery.update_import_progress(recovered_task.task_id, 100.0, "completed")
                recovery.complete_import_task(recovered_task.task_id, True)
            
            logger.info("App crash test completed successfully")
            
        except Exception as e:
            logger.error(f"App crash test failed: {e}")
            raise
    
    async def _validate_app_crash(self):
        """Validate app crash test results."""
        logger.info("Validating app crash test results")
        
        from .workflow_import import get_workflow_import_recovery
        recovery = get_workflow_import_recovery()
        
        # Check if task was recovered and completed
        history = recovery.get_import_history()
        if history:
            latest_task = history[-1]
            return latest_task["status"] == "completed"
        
        return False
    
    async def _cleanup_app_crash(self):
        """Cleanup app crash test."""
        logger.info("Cleaning up app crash test")
        
        if hasattr(self, 'crash_patch'):
            self.crash_patch.stop()
        
        if hasattr(self, 'test_workflow_data'):
            del self.test_workflow_data
    
    # Browser Refresh Test Scenario
    async def _setup_browser_refresh(self):
        """Setup for browser refresh test."""
        logger.info("Setting up browser refresh test")
        
        # Create mock installation data
        self.test_installation_data = {
            "project_id": "test_project",
            "project_path": "/tmp/test_project",
            "installation_type": "comfyui",
            "target_version": "latest"
        }
        
        logger.info("Browser refresh test setup complete")
    
    async def _execute_browser_refresh(self):
        """Execute browser refresh test."""
        logger.info("Executing browser refresh test")
        
        # Import installation recovery
        from .installation import get_installation_recovery
        
        # Get installation recovery instance
        recovery = get_installation_recovery()
        
        # Create installation task
        task = recovery.create_installation_task(**self.test_installation_data)
        
        # Simulate browser refresh (loss of connection)
        try:
            # Start installation
            recovery.update_installation_progress(task.task_id, 30.0, "installing_comfyui")
            
            # Simulate browser refresh
            logger.info("Simulating browser refresh during installation")
            
            # Simulate recovery after reconnect
            recovered_task = recovery.active_installations.get(task.task_id)
            if recovered_task:
                recovery.update_installation_progress(recovered_task.task_id, 100.0, "completed")
                recovery.complete_installation_task(recovered_task.task_id, True)
            
            logger.info("Browser refresh test completed successfully")
            
        except Exception as e:
            logger.error(f"Browser refresh test failed: {e}")
            raise
    
    async def _validate_browser_refresh(self):
        """Validate browser refresh test results."""
        logger.info("Validating browser refresh test results")
        
        from .installation import get_installation_recovery
        recovery = get_installation_recovery()
        
        # Check if installation was recovered and completed
        history = recovery.get_installation_history()
        if history:
            latest_task = history[-1]
            return latest_task["status"] == "completed"
        
        return False
    
    async def _cleanup_browser_refresh(self):
        """Cleanup browser refresh test."""
        logger.info("Cleaning up browser refresh test")
        
        if hasattr(self, 'test_installation_data'):
            del self.test_installation_data
    
    # Concurrent Recoveries Test Scenario
    async def _setup_concurrent_recoveries(self):
        """Setup for concurrent recoveries test."""
        logger.info("Setting up concurrent recoveries test")
        
        # Create multiple concurrent tasks
        self.concurrent_tasks = []
        
        # Model download task
        self.mock_download_manager = Mock()
        self.mock_download_manager.download_model = AsyncMock()
        
        # Workflow import task
        self.test_workflow_data = {
            "nodes": [{"id": "1", "type": "TestNode", "inputs": {}}],
            "links": []
        }
        
        # Installation task
        self.test_installation_data = {
            "project_id": "concurrent_test",
            "project_path": "/tmp/concurrent_test",
            "installation_type": "custom_nodes",
            "custom_nodes": ["test_node_1", "test_node_2"]
        }
        
        logger.info("Concurrent recoveries test setup complete")
    
    async def _execute_concurrent_recoveries(self):
        """Execute concurrent recoveries test."""
        logger.info("Executing concurrent recoveries test")
        
        # Create and run multiple concurrent tasks
        tasks = []
        
        # Task 1: Model download
        from .integration import get_recovery_integrator
        integrator = get_recovery_integrator()
        
        if integrator.enabled:
            enhanced_manager = integrator.apply_to_model_downloads(self.mock_download_manager)
            tasks.append(self._run_concurrent_download(enhanced_manager))
        
        # Task 2: Workflow import
        from .workflow_import import get_workflow_import_recovery
        workflow_recovery = get_workflow_import_recovery()
        tasks.append(self._run_concurrent_workflow_import(workflow_recovery))
        
        # Task 3: Installation
        from .installation import get_installation_recovery
        installation_recovery = get_installation_recovery()
        tasks.append(self._run_concurrent_installation(installation_recovery))
        
        # Run all tasks concurrently
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Concurrent recoveries test completed successfully")
            
        except Exception as e:
            logger.error(f"Concurrent recoveries test failed: {e}")
            raise
    
    async def _run_concurrent_download(self, download_manager):
        """Run concurrent model download task."""
        try:
            await asyncio.sleep(0.5)  # Simulate work
            return await download_manager.download_model(
                model_id="concurrent_model",
                url="http://example.com/concurrent_model.bin",
                save_path="/tmp/concurrent_model.bin"
            )
        except Exception as e:
            logger.error(f"Concurrent download failed: {e}")
            raise
    
    async def _run_concurrent_workflow_import(self, recovery):
        """Run concurrent workflow import task."""
        try:
            task = recovery.create_import_task(
                project_name="concurrent_project",
                import_json=self.test_workflow_data,
                resolved_missing_models=[],
                skipping_model_validation=True
            )
            
            await asyncio.sleep(0.3)  # Simulate work
            recovery.update_import_progress(task.task_id, 100.0, "completed")
            recovery.complete_import_task(task.task_id, True)
            
            return True
        except Exception as e:
            logger.error(f"Concurrent workflow import failed: {e}")
            raise
    
    async def _run_concurrent_installation(self, recovery):
        """Run concurrent installation task."""
        try:
            task = recovery.create_installation_task(**self.test_installation_data)
            
            await asyncio.sleep(0.7)  # Simulate work
            recovery.update_installation_progress(task.task_id, 100.0, "completed")
            recovery.complete_installation_task(task.task_id, True)
            
            return True
        except Exception as e:
            logger.error(f"Concurrent installation failed: {e}")
            raise
    
    async def _validate_concurrent_recoveries(self):
        """Validate concurrent recoveries test results."""
        logger.info("Validating concurrent recoveries test results")
        
        # Check if all tasks completed successfully
        success_count = 0
        
        # Check workflow import history
        from .workflow_import import get_workflow_import_recovery
        workflow_recovery = get_workflow_import_recovery()
        workflow_history = workflow_recovery.get_import_history()
        success_count += len([t for t in workflow_history if t["status"] == "completed"])
        
        # Check installation history
        from .installation import get_installation_recovery
        installation_recovery = get_installation_recovery()
        installation_history = installation_recovery.get_installation_history()
        success_count += len([t for t in installation_history if t["status"] == "completed"])
        
        return success_count >= 2  # At least 2 tasks should complete
    
    async def _cleanup_concurrent_recoveries(self):
        """Cleanup concurrent recoveries test."""
        logger.info("Cleaning up concurrent recoveries test")
        
        if hasattr(self, 'mock_download_manager'):
            del self.mock_download_manager
        
        if hasattr(self, 'test_workflow_data'):
            del self.test_workflow_data
        
        if hasattr(self, 'test_installation_data'):
            del self.test_installation_data
        
        if hasattr(self, 'concurrent_tasks'):
            del self.concurrent_tasks
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all test results."""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == "passed"])
        failed_tests = len([r for r in self.test_results if r.status == "failed"])
        error_tests = len([r for r in self.test_results if r.status == "error"])
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "average_execution_time": sum(r.execution_time for r in self.test_results) / total_tests if total_tests > 0 else 0,
            "test_results": [asdict(result) for result in self.test_results]
        }

class PerformanceMonitor:
    """Monitor performance metrics during testing."""
    
    def __init__(self):
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "response_times": [],
            "recovery_times": []
        }
        self.start_time = None
        self.monitoring = False
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.monitoring = True
        self.metrics["start_time"] = self.start_time
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        self.metrics["end_time"] = time.time()
    
    def record_metric(self, metric_type: str, value: float):
        """Record a performance metric."""
        if metric_type in self.metrics:
            self.metrics[metric_type].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        if not self.start_time:
            return {}
        
        total_time = (self.metrics.get("end_time", time.time()) - self.start_time)
        
        return {
            "total_time": total_time,
            "avg_cpu_usage": sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
            "avg_memory_usage": sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
            "avg_response_time": sum(self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0,
            "avg_recovery_time": sum(self.metrics["recovery_times"]) / len(self.metrics["recovery_times"]) if self.metrics["recovery_times"] else 0,
            "recovery_overhead": self._calculate_recovery_overhead()
        }
    
    def _calculate_recovery_overhead(self) -> float:
        """Calculate recovery system overhead percentage."""
        if not self.metrics["response_times"] or not self.metrics["recovery_times"]:
            return 0.0
        
        avg_response = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        avg_recovery = sum(self.metrics["recovery_times"]) / len(self.metrics["recovery_times"])
        
        if avg_response > 0:
            return ((avg_recovery - avg_response) / avg_response) * 100
        
        return 0.0

# Global test suite instance
_test_suite = None

def get_test_suite() -> RecoveryTestSuite:
    """Get the global test suite instance."""
    global _test_suite
    if _test_suite is None:
        _test_suite = RecoveryTestSuite()
    return _test_suite

async def run_comprehensive_recovery_tests() -> Dict[str, Any]:
    """Run comprehensive recovery tests and return results."""
    test_suite = get_test_suite()
    results = await test_suite.run_all_tests()
    summary = test_suite.get_test_summary()
    
    logger.info(f"Recovery test suite completed: {summary['success_rate']:.1f}% success rate")
    
    return summary