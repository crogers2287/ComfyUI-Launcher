"""
Recovery-enhanced ComfyUI operations for ComfyUI Launcher.

This module provides recovery capabilities for long-running ComfyUI operations,
including workflow execution, model processing, and server management.
"""

import os
import json
import time
import logging
import psutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ComfyUIOperation:
    """Represents a long-running ComfyUI operation."""
    project_id: str
    operation_type: str  # "workflow_execution", "model_processing", "server_management"
    workflow_data: Optional[Dict[str, Any]] = None
    input_data: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    task_id: str = ""
    status: str = "pending"
    progress: float = 0.0
    current_step: str = ""
    result_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    process_id: Optional[int] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    retry_count: int = 0
    checkpoint_data: Optional[Dict[str, Any]] = None

class ComfyUIOperationRecovery:
    """Handles recovery for long-running ComfyUI operations."""
    
    def __init__(self, recovery_integrator=None):
        self.recovery_integrator = recovery_integrator
        self.active_operations = {}
        self.operation_history = []
        self.operation_checkpoints = {}
        self.process_monitor = ProcessMonitor()
        
    def create_operation(self, project_id: str, operation_type: str,
                         workflow_data: Optional[Dict[str, Any]] = None,
                         input_data: Optional[Dict[str, Any]] = None,
                         parameters: Optional[Dict[str, Any]] = None) -> ComfyUIOperation:
        """Create a new ComfyUI operation with recovery support."""
        import uuid
        task_id = str(uuid.uuid4())
        
        operation = ComfyUIOperation(
            project_id=project_id,
            operation_type=operation_type,
            workflow_data=workflow_data,
            input_data=input_data,
            parameters=parameters or {},
            task_id=task_id,
            status="pending",
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.active_operations[task_id] = operation
        logger.info(f"Created ComfyUI operation: {task_id} for project: {project_id}")
        
        return operation
    
    def get_operation_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a ComfyUI operation."""
        if task_id in self.active_operations:
            operation = self.active_operations[task_id]
            
            # Check if process is still running
            if operation.process_id:
                is_running = self.process_monitor.is_process_running(operation.process_id)
                if not is_running and operation.status == "running":
                    # Process died unexpectedly
                    operation.status = "failed"
                    operation.error = "Process terminated unexpectedly"
                    operation.updated_at = time.time()
            
            return {
                "task_id": operation.task_id,
                "project_id": operation.project_id,
                "operation_type": operation.operation_type,
                "status": operation.status,
                "progress": operation.progress,
                "current_step": operation.current_step,
                "error": operation.error,
                "retry_count": operation.retry_count,
                "process_id": operation.process_id,
                "is_process_running": self.process_monitor.is_process_running(operation.process_id) if operation.process_id else False,
                "created_at": operation.created_at,
                "updated_at": operation.updated_at,
                "has_result": operation.result_data is not None
            }
        return None
    
    def update_operation_progress(self, task_id: str, progress: float,
                                current_step: str = "", status: str = None,
                                error: str = None, result_data: Optional[Dict[str, Any]] = None):
        """Update progress of a ComfyUI operation."""
        if task_id in self.active_operations:
            operation = self.active_operations[task_id]
            operation.progress = progress
            operation.current_step = current_step
            operation.updated_at = time.time()
            if status:
                operation.status = status
            if error:
                operation.error = error
            if result_data:
                operation.result_data = result_data
            
            # Save checkpoint for critical operations
            if operation.operation_type in ["workflow_execution", "model_processing"]:
                self._save_operation_checkpoint(task_id, progress, current_step, result_data)
            
            logger.info(f"Updated ComfyUI operation {task_id}: progress={progress:.1f}%, step={current_step}")
    
    def _save_operation_checkpoint(self, task_id: str, progress: float, 
                                 current_step: str, result_data: Optional[Dict[str, Any]]):
        """Save operation checkpoint for recovery."""
        if task_id in self.active_operations:
            operation = self.active_operations[task_id]
            
            checkpoint = {
                "task_id": task_id,
                "progress": progress,
                "current_step": current_step,
                "timestamp": time.time(),
                "project_id": operation.project_id,
                "operation_type": operation.operation_type,
                "result_data": result_data,
                "process_id": operation.process_id
            }
            
            self.operation_checkpoints[task_id] = checkpoint
    
    def complete_operation(self, task_id: str, success: bool = True, 
                          error: str = None, result_data: Optional[Dict[str, Any]] = None):
        """Mark a ComfyUI operation as completed."""
        if task_id in self.active_operations:
            operation = self.active_operations[task_id]
            operation.status = "completed" if success else "failed"
            operation.progress = 100.0 if success else operation.progress
            operation.error = error
            operation.result_data = result_data
            operation.updated_at = time.time()
            
            # Move to history
            self.operation_history.append(operation)
            del self.active_operations[task_id]
            
            # Clean up checkpoint
            if task_id in self.operation_checkpoints:
                del self.operation_checkpoints[task_id]
            
            logger.info(f"Completed ComfyUI operation {task_id}: success={success}")
    
    def apply_recovery_to_comfyui_operation(self, original_operation_function):
        """Apply recovery mechanisms to ComfyUI operations."""
        if not self.recovery_integrator or not self.recovery_integrator.enabled:
            logger.warning("Recovery system not available for ComfyUI operations")
            return original_operation_function
        
        try:
            from .recovery import recoverable
            
            @recoverable(
                max_retries=3,
                persistence=self.recovery_integrator.persistence,
                strategy=self.recovery_integrator.strategy,
                timeout=7200,  # 2 hours for long operations
                circuit_breaker_threshold=3,
                circuit_breaker_timeout=1200.0,
                classifier=self.recovery_integrator.classifier
            )
            async def recoverable_operation(*args, **kwargs):
                """Recoverable ComfyUI operation function."""
                # Extract task information from arguments
                task_id = kwargs.get('_recovery_operation_id')
                
                if task_id and task_id in self.active_operations:
                    operation = self.active_operations[task_id]
                    self.update_operation_progress(task_id, 10.0, "initializing", "running")
                
                try:
                    # Call original operation function
                    result = await original_operation_function(*args, **kwargs)
                    
                    if task_id:
                        self.update_operation_progress(task_id, 100.0, "completed", "completed", result_data=result)
                        self.complete_operation(task_id, True, result_data=result)
                    
                    return result
                    
                except Exception as e:
                    if task_id:
                        operation = self.active_operations[task_id]
                        operation.retry_count += 1
                        
                        # Analyze error for recovery potential
                        recovery_action = self._analyze_comfyui_error(e, operation)
                        
                        if recovery_action == "retry":
                            logger.info(f"ComfyUI operation error for task {task_id} is recoverable, will retry")
                            # Don't complete the task, let recovery system handle retry
                        elif recovery_action == "resume":
                            logger.info(f"ComfyUI operation error for task {task_id} can be resumed")
                            self.update_operation_progress(task_id, operation.progress, "paused", "paused", str(e))
                        else:
                            self.complete_operation(task_id, False, str(e))
                    raise
            
            logger.info("Applied recovery mechanisms to ComfyUI operations")
            return recoverable_operation
            
        except Exception as e:
            logger.error(f"Failed to apply recovery to ComfyUI operations: {e}")
            return original_operation_function
    
    def _analyze_comfyui_error(self, error: Exception, operation: ComfyUIOperation) -> str:
        """Analyze ComfyUI operation error to determine recovery action."""
        error_str = str(error).lower()
        
        # Process-related errors
        if any(indicator in error_str for indicator in [
            "process", "terminated", "killed", "exit"
        ]):
            if operation.process_id and not self.process_monitor.is_process_running(operation.process_id):
                return "restart"  # Can restart the process
            return "retry"
        
        # Memory errors
        if any(indicator in error_str for indicator in [
            "memory", "out of memory", "oom", "ram"
        ]):
            return "adjust"  # Can retry with adjusted parameters
        
        # Model-related errors
        if any(indicator in error_str for indicator in [
            "model", "checkpoint", "weight", "tensor"
        ]):
            return "retry"  # Can retry model loading
        
        # Workflow validation errors
        if any(indicator in error_str for indicator in [
            "workflow", "validation", "node", "connection"
        ]):
            return "manual"  # Needs user intervention
        
        # File system errors
        if any(indicator in error_str for indicator in [
            "file", "directory", "permission", "access"
        ]):
            return "retry"  # Can retry after checking permissions
        
        # Network errors (for remote operations)
        if any(indicator in error_str for indicator in [
            "network", "connection", "timeout", "remote"
        ]):
            return "retry"
        
        # Default to retry for unknown errors
        return "retry"
    
    def resume_interrupted_operation(self, task_id: str) -> bool:
        """Resume an interrupted ComfyUI operation from checkpoint."""
        if task_id not in self.operation_checkpoints:
            logger.error(f"No checkpoint found for operation {task_id}")
            return False
        
        if task_id not in self.active_operations:
            logger.error(f"Operation {task_id} not found for resume")
            return False
        
        try:
            checkpoint = self.operation_checkpoints[task_id]
            operation = self.active_operations[task_id]
            
            # Update status to indicate resuming
            self.update_operation_progress(task_id, checkpoint["progress"], 
                                       f"resuming_from_{checkpoint['current_step']}", 
                                       "resuming")
            
            # Restore checkpoint data
            if checkpoint.get("result_data"):
                operation.checkpoint_data = checkpoint["result_data"]
            
            # This would implement the actual resume logic based on checkpoint
            logger.info(f"Resuming ComfyUI operation {task_id} from checkpoint")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume operation {task_id}: {e}")
            return False
    
    def handle_process_failure(self, task_id: str, exit_code: int, error_message: str):
        """Handle process failure during ComfyUI operation."""
        if task_id in self.active_operations:
            operation = self.active_operations[task_id]
            
            # Update status to indicate process failure
            self.update_operation_progress(task_id, operation.progress, 
                                       "process_failed", f"Process exited with code {exit_code}: {error_message}")
            
            # Analyze failure for recovery potential
            if exit_code == 0:
                # Process completed successfully but operation may have failed
                return "check_output"
            elif exit_code < 0:
                # Process was killed
                return "restart"
            else:
                # Process failed with error
                return "retry"
        
        return "unknown"
    
    def cancel_operation(self, task_id: str) -> bool:
        """Cancel a ComfyUI operation."""
        if task_id in self.active_operations:
            operation = self.active_operations[task_id]
            
            # Kill process if running
            if operation.process_id and self.process_monitor.is_process_running(operation.process_id):
                try:
                    self.process_monitor.kill_process(operation.process_id)
                    logger.info(f"Killed process {operation.process_id} for operation {task_id}")
                except Exception as e:
                    logger.error(f"Failed to kill process {operation.process_id}: {e}")
            
            # Update status to cancelled
            self.update_operation_progress(task_id, operation.progress, "cancelled", "Cancelled by user")
            self.complete_operation(task_id, False, "Cancelled by user")
            
            logger.info(f"Cancelled ComfyUI operation {task_id}")
            return True
        
        return False
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get all active ComfyUI operations."""
        return [
            {
                "task_id": operation.task_id,
                "project_id": operation.project_id,
                "operation_type": operation.operation_type,
                "status": operation.status,
                "progress": operation.progress,
                "current_step": operation.current_step,
                "error": operation.error,
                "retry_count": operation.retry_count,
                "process_id": operation.process_id,
                "created_at": operation.created_at,
                "updated_at": operation.updated_at
            }
            for operation in self.active_operations.values()
        ]
    
    def get_operation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get ComfyUI operation history."""
        return [
            {
                "task_id": operation.task_id,
                "project_id": operation.project_id,
                "operation_type": operation.operation_type,
                "status": operation.status,
                "progress": operation.progress,
                "error": operation.error,
                "retry_count": operation.retry_count,
                "created_at": operation.created_at,
                "updated_at": operation.updated_at,
                "duration": operation.updated_at - operation.created_at,
                "had_result": operation.result_data is not None
            }
            for operation in self.operation_history[-limit:]
        ]

class ProcessMonitor:
    """Monitor and manage processes for ComfyUI operations."""
    
    def __init__(self):
        self.monitored_processes = {}
    
    def register_process(self, task_id: str, process_id: int):
        """Register a process for monitoring."""
        self.monitored_processes[task_id] = process_id
        logger.info(f"Registered process {process_id} for task {task_id}")
    
    def is_process_running(self, process_id: int) -> bool:
        """Check if a process is still running."""
        try:
            process = psutil.Process(process_id)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            logger.warning(f"Access denied checking process {process_id}")
            return True  # Assume still running if we can't check
    
    def kill_process(self, process_id: int) -> bool:
        """Kill a process."""
        try:
            process = psutil.Process(process_id)
            process.kill()
            logger.info(f"Killed process {process_id}")
            return True
        except psutil.NoSuchProcess:
            logger.warning(f"Process {process_id} not found")
            return True  # Consider it "killed" if it doesn't exist
        except psutil.AccessDenied:
            logger.error(f"Access denied killing process {process_id}")
            return False
    
    def get_process_info(self, process_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a process."""
        try:
            process = psutil.Process(process_id)
            return {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "create_time": process.create_time(),
                "running": process.is_running()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def cleanup_monitored_processes(self):
        """Clean up terminated processes from monitoring."""
        terminated_tasks = []
        
        for task_id, process_id in self.monitored_processes.items():
            if not self.is_process_running(process_id):
                terminated_tasks.append(task_id)
        
        for task_id in terminated_tasks:
            del self.monitored_processes[task_id]
            logger.info(f"Cleaned up terminated process for task {task_id}")

# Global instance
_comfyui_operation_recovery = None

def get_comfyui_operation_recovery() -> ComfyUIOperationRecovery:
    """Get the global ComfyUI operation recovery instance."""
    global _comfyui_operation_recovery
    if _comfyui_operation_recovery is None:
        from .integration import get_recovery_integrator
        _comfyui_operation_recovery = ComfyUIOperationRecovery(get_recovery_integrator())
    return _comfyui_operation_recovery