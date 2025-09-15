"""
Recovery-enhanced workflow import operations for ComfyUI Launcher.

This module provides recovery capabilities for workflow import operations,
including network interruption handling, crash recovery, and progress tracking.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WorkflowImportTask:
    """Represents a workflow import task with all necessary metadata."""
    project_name: str
    import_json: Dict[str, Any]
    resolved_missing_models: List[Dict[str, Any]]
    skipping_model_validation: bool
    port: Optional[int] = None
    task_id: str = ""
    status: str = "pending"
    progress: float = 0.0
    error: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0

class WorkflowImportRecovery:
    """Handles recovery for workflow import operations."""
    
    def __init__(self, recovery_integrator=None):
        self.recovery_integrator = recovery_integrator
        self.active_imports = {}
        self.import_history = []
        
    def create_import_task(self, project_name: str, import_json: Dict[str, Any], 
                          resolved_missing_models: List[Dict[str, Any]], 
                          skipping_model_validation: bool, 
                          port: Optional[int] = None) -> WorkflowImportTask:
        """Create a new workflow import task with recovery support."""
        import uuid
        task_id = str(uuid.uuid4())
        
        task = WorkflowImportTask(
            project_name=project_name,
            import_json=import_json,
            resolved_missing_models=resolved_missing_models,
            skipping_model_validation=skipping_model_validation,
            port=port,
            task_id=task_id,
            status="pending",
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.active_imports[task_id] = task
        logger.info(f"Created workflow import task: {task_id} for project: {project_name}")
        
        return task
    
    def get_import_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow import task."""
        if task_id in self.active_imports:
            task = self.active_imports[task_id]
            return {
                "task_id": task.task_id,
                "project_name": task.project_name,
                "status": task.status,
                "progress": task.progress,
                "error": task.error,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "resolved_models_count": len(task.resolved_missing_models)
            }
        return None
    
    def update_import_progress(self, task_id: str, progress: float, status: str = None, error: str = None):
        """Update progress of a workflow import task."""
        if task_id in self.active_imports:
            task = self.active_imports[task_id]
            task.progress = progress
            task.updated_at = time.time()
            if status:
                task.status = status
            if error:
                task.error = error
            
            logger.info(f"Updated import task {task_id}: progress={progress:.1f}%, status={status}")
    
    def complete_import_task(self, task_id: str, success: bool = True, error: str = None):
        """Mark a workflow import task as completed."""
        if task_id in self.active_imports:
            task = self.active_imports[task_id]
            task.status = "completed" if success else "failed"
            task.progress = 100.0 if success else task.progress
            task.error = error
            task.updated_at = time.time()
            
            # Move to history
            self.import_history.append(task)
            del self.active_imports[task_id]
            
            logger.info(f"Completed import task {task_id}: success={success}")
    
    def apply_recovery_to_import_function(self, original_import_function):
        """Apply recovery mechanisms to the workflow import function."""
        if not self.recovery_integrator or not self.recovery_integrator.enabled:
            logger.warning("Recovery system not available for workflow imports")
            return original_import_function
        
        try:
            from .recovery import recoverable
            
            @recoverable(
                max_retries=3,
                persistence=self.recovery_integrator.persistence,
                strategy=self.recovery_integrator.strategy,
                timeout=1800,  # 30 minutes for workflow import
                circuit_breaker_threshold=3,
                circuit_breaker_timeout=600.0,
                classifier=self.recovery_integrator.classifier
            )
            async def recoverable_import(*args, **kwargs):
                """Recoverable workflow import function."""
                # Extract task information from arguments
                task_id = kwargs.get('_recovery_operation_id')
                
                if task_id and task_id in self.active_imports:
                    task = self.active_imports[task_id]
                    self.update_import_progress(task_id, 10.0, "processing")
                
                try:
                    # Call original import function
                    result = await original_import_function(*args, **kwargs)
                    
                    if task_id:
                        self.update_import_progress(task_id, 100.0, "completed")
                        self.complete_import_task(task_id, True)
                    
                    return result
                    
                except Exception as e:
                    if task_id:
                        self.update_import_progress(task_id, task.progress, "failed", str(e))
                        self.complete_import_task(task_id, False, str(e))
                    raise
            
            logger.info("Applied recovery mechanisms to workflow imports")
            return recoverable_import
            
        except Exception as e:
            logger.error(f"Failed to apply recovery to workflow imports: {e}")
            return original_import_function
    
    def handle_network_interruption(self, task_id: str, error: Exception):
        """Handle network interruption during workflow import."""
        if task_id in self.active_imports:
            task = self.active_imports[task_id]
            
            # Update status to indicate network issue
            self.update_import_progress(task_id, task.progress, "network_error", str(error))
            
            # Attempt to recover based on error type
            error_str = str(error).lower()
            
            if "connection" in error_str or "network" in error_str or "timeout" in error_str:
                # Network-related error - can retry
                logger.info(f"Network interruption detected for task {task_id}, will retry")
                return "retry"
            elif "validation" in error_str or "format" in error_str:
                # Validation error - don't retry
                logger.error(f"Validation error for task {task_id}, cannot retry")
                return "abort"
            else:
                # Unknown error - retry with caution
                logger.warning(f"Unknown error for task {task_id}, will retry")
                return "retry"
        
        return "unknown"
    
    def resume_interrupted_import(self, task_id: str) -> bool:
        """Resume an interrupted workflow import."""
        if task_id not in self.active_imports:
            logger.error(f"Task {task_id} not found for resume")
            return False
        
        task = self.active_imports[task_id]
        
        if task.status not in ["failed", "network_error", "paused"]:
            logger.warning(f"Task {task_id} is not in a resumable state: {task.status}")
            return False
        
        try:
            # Update status to indicate resuming
            self.update_import_progress(task_id, task.progress, "resuming")
            
            # This would implement the actual resume logic
            # For now, just update the status
            logger.info(f"Resuming interrupted import task {task_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False
    
    def cancel_import_task(self, task_id: str) -> bool:
        """Cancel a workflow import task."""
        if task_id in self.active_imports:
            task = self.active_imports[task_id]
            
            # Update status to cancelled
            self.update_import_progress(task_id, task.progress, "cancelled", "Cancelled by user")
            self.complete_import_task(task_id, False, "Cancelled by user")
            
            logger.info(f"Cancelled import task {task_id}")
            return True
        
        return False
    
    def get_active_imports(self) -> List[Dict[str, Any]]:
        """Get all active workflow import tasks."""
        return [
            {
                "task_id": task.task_id,
                "project_name": task.project_name,
                "status": task.status,
                "progress": task.progress,
                "error": task.error,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "resolved_models_count": len(task.resolved_missing_models)
            }
            for task in self.active_imports.values()
        ]
    
    def get_import_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get workflow import history."""
        return [
            {
                "task_id": task.task_id,
                "project_name": task.project_name,
                "status": task.status,
                "progress": task.progress,
                "error": task.error,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "duration": task.updated_at - task.created_at
            }
            for task in self.import_history[-limit:]
        ]

# Global instance
_workflow_import_recovery = None

def get_workflow_import_recovery() -> WorkflowImportRecovery:
    """Get the global workflow import recovery instance."""
    global _workflow_import_recovery
    if _workflow_import_recovery is None:
        from .integration import get_recovery_integrator
        _workflow_import_recovery = WorkflowImportRecovery(get_recovery_integrator())
    return _workflow_import_recovery