"""
Recovery-enhanced installation operations for ComfyUI Launcher.

This module provides recovery capabilities for installation processes,
including ComfyUI installation, custom node installation, and dependency management.
"""

import os
import json
import time
import logging
import subprocess
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InstallationTask:
    """Represents an installation task with all necessary metadata."""
    project_id: str
    project_path: str
    installation_type: str  # "comfyui", "custom_nodes", "dependencies"
    target_version: Optional[str] = None
    custom_nodes: List[str] = None
    dependencies: List[str] = None
    task_id: str = ""
    status: str = "pending"
    progress: float = 0.0
    current_step: str = ""
    error: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    retry_count: int = 0

class InstallationRecovery:
    """Handles recovery for installation operations."""
    
    def __init__(self, recovery_integrator=None):
        self.recovery_integrator = recovery_integrator
        self.active_installations = {}
        self.installation_history = []
        self.installation_checkpoints = {}
        
    def create_installation_task(self, project_id: str, project_path: str, 
                               installation_type: str,
                               target_version: Optional[str] = None,
                               custom_nodes: List[str] = None,
                               dependencies: List[str] = None) -> InstallationTask:
        """Create a new installation task with recovery support."""
        import uuid
        task_id = str(uuid.uuid4())
        
        task = InstallationTask(
            project_id=project_id,
            project_path=project_path,
            installation_type=installation_type,
            target_version=target_version,
            custom_nodes=custom_nodes or [],
            dependencies=dependencies or [],
            task_id=task_id,
            status="pending",
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.active_installations[task_id] = task
        logger.info(f"Created installation task: {task_id} for project: {project_id}")
        
        return task
    
    def get_installation_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an installation task."""
        if task_id in self.active_installations:
            task = self.active_installations[task_id]
            return {
                "task_id": task.task_id,
                "project_id": task.project_id,
                "installation_type": task.installation_type,
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "error": task.error,
                "retry_count": task.retry_count,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "target_version": task.target_version,
                "custom_nodes_count": len(task.custom_nodes) if task.custom_nodes else 0,
                "dependencies_count": len(task.dependencies) if task.dependencies else 0
            }
        return None
    
    def update_installation_progress(self, task_id: str, progress: float, 
                                   current_step: str = "", status: str = None, 
                                   error: str = None):
        """Update progress of an installation task."""
        if task_id in self.active_installations:
            task = self.active_installations[task_id]
            task.progress = progress
            task.current_step = current_step
            task.updated_at = time.time()
            if status:
                task.status = status
            if error:
                task.error = error
            
            # Save checkpoint
            self._save_checkpoint(task_id, progress, current_step)
            
            logger.info(f"Updated installation task {task_id}: progress={progress:.1f}%, step={current_step}")
    
    def _save_checkpoint(self, task_id: str, progress: float, current_step: str):
        """Save installation checkpoint for recovery."""
        if task_id in self.active_installations:
            task = self.active_installations[task_id]
            
            checkpoint = {
                "task_id": task_id,
                "progress": progress,
                "current_step": current_step,
                "timestamp": time.time(),
                "project_path": task.project_path,
                "installation_type": task.installation_type
            }
            
            self.installation_checkpoints[task_id] = checkpoint
    
    def complete_installation_task(self, task_id: str, success: bool = True, error: str = None):
        """Mark an installation task as completed."""
        if task_id in self.active_installations:
            task = self.active_installations[task_id]
            task.status = "completed" if success else "failed"
            task.progress = 100.0 if success else task.progress
            task.error = error
            task.updated_at = time.time()
            
            # Move to history
            self.installation_history.append(task)
            del self.active_installations[task_id]
            
            # Clean up checkpoint
            if task_id in self.installation_checkpoints:
                del self.installation_checkpoints[task_id]
            
            logger.info(f"Completed installation task {task_id}: success={success}")
    
    def apply_recovery_to_installation_function(self, original_install_function):
        """Apply recovery mechanisms to installation functions."""
        if not self.recovery_integrator or not self.recovery_integrator.enabled:
            logger.warning("Recovery system not available for installation processes")
            return original_install_function
        
        try:
            from .recovery import recoverable
            
            @recoverable(
                max_retries=5,
                persistence=self.recovery_integrator.persistence,
                strategy=self.recovery_integrator.strategy,
                timeout=3600,  # 1 hour for installation
                circuit_breaker_threshold=5,
                circuit_breaker_timeout=900.0,
                classifier=self.recovery_integrator.classifier
            )
            async def recoverable_installation(*args, **kwargs):
                """Recoverable installation function."""
                # Extract task information from arguments
                task_id = kwargs.get('_recovery_operation_id')
                
                if task_id and task_id in self.active_installations:
                    task = self.active_installations[task_id]
                    self.update_installation_progress(task_id, 10.0, "starting_installation")
                
                try:
                    # Call original installation function
                    result = await original_install_function(*args, **kwargs)
                    
                    if task_id:
                        self.update_installation_progress(task_id, 100.0, "completed", "completed")
                        self.complete_installation_task(task_id, True)
                    
                    return result
                    
                except Exception as e:
                    if task_id:
                        task = self.active_installations[task_id]
                        task.retry_count += 1
                        self.update_installation_progress(task_id, task.progress, "failed", str(e))
                        
                        # Analyze error for recovery potential
                        recovery_action = self._analyze_installation_error(e, task)
                        if recovery_action == "retry":
                            logger.info(f"Installation error for task {task_id} is recoverable, will retry")
                            # Don't complete the task, let recovery system handle retry
                        else:
                            self.complete_installation_task(task_id, False, str(e))
                    raise
            
            logger.info("Applied recovery mechanisms to installation processes")
            return recoverable_installation
            
        except Exception as e:
            logger.error(f"Failed to apply recovery to installation processes: {e}")
            return original_install_function
    
    def _analyze_installation_error(self, error: Exception, task: InstallationTask) -> str:
        """Analyze installation error to determine recovery action."""
        error_str = str(error).lower()
        
        # Network-related errors - can retry
        if any(indicator in error_str for indicator in [
            "connection", "network", "timeout", "resolve", "refused"
        ]):
            return "retry"
        
        # Disk space errors - can retry after cleanup
        if any(indicator in error_str for indicator in [
            "disk space", "no space", "quota exceeded"
        ]):
            return "retry"
        
        # Permission errors - might need user intervention
        if any(indicator in error_str for indicator in [
            "permission", "access denied", "forbidden"
        ]):
            return "manual"
        
        # Version conflicts - might need version adjustment
        if any(indicator in error_str for indicator in [
            "version conflict", "incompatible", "requirements"
        ]):
            return "adjust"
        
        # Critical errors - cannot recover
        if any(indicator in error_str for indicator in [
            "corrupted", "invalid", "malformed"
        ]):
            return "abort"
        
        # Default to retry for unknown errors
        return "retry"
    
    def resume_interrupted_installation(self, task_id: str) -> bool:
        """Resume an interrupted installation from checkpoint."""
        if task_id not in self.installation_checkpoints:
            logger.error(f"No checkpoint found for task {task_id}")
            return False
        
        if task_id not in self.active_installations:
            logger.error(f"Task {task_id} not found for resume")
            return False
        
        try:
            checkpoint = self.installation_checkpoints[task_id]
            task = self.active_installations[task_id]
            
            # Update status to indicate resuming
            self.update_installation_progress(task_id, checkpoint["progress"], 
                                          f"resuming_from_{checkpoint['current_step']}", 
                                          "resuming")
            
            # This would implement the actual resume logic based on checkpoint
            logger.info(f"Resuming installation task {task_id} from checkpoint")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False
    
    def handle_installation_step_failure(self, task_id: str, step_name: str, error: Exception):
        """Handle failure during a specific installation step."""
        if task_id in self.active_installations:
            task = self.active_installations[task_id]
            
            # Update status to indicate step failure
            self.update_installation_progress(task_id, task.progress, 
                                          f"failed_at_{step_name}", str(error))
            
            # Analyze error for recovery potential
            recovery_action = self._analyze_installation_error(error, task)
            
            logger.info(f"Installation step {step_name} failed for task {task_id}: {recovery_action}")
            
            return recovery_action
        
        return "unknown"
    
    def cancel_installation_task(self, task_id: str) -> bool:
        """Cancel an installation task."""
        if task_id in self.active_installations:
            task = self.active_installations[task_id]
            
            # Update status to cancelled
            self.update_installation_progress(task_id, task.progress, "cancelled", "Cancelled by user")
            self.complete_installation_task(task_id, False, "Cancelled by user")
            
            logger.info(f"Cancelled installation task {task_id}")
            return True
        
        return False
    
    def get_active_installations(self) -> List[Dict[str, Any]]:
        """Get all active installation tasks."""
        return [
            {
                "task_id": task.task_id,
                "project_id": task.project_id,
                "installation_type": task.installation_type,
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "error": task.error,
                "retry_count": task.retry_count,
                "created_at": task.created_at,
                "updated_at": task.updated_at
            }
            for task in self.active_installations.values()
        ]
    
    def get_installation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get installation history."""
        return [
            {
                "task_id": task.task_id,
                "project_id": task.project_id,
                "installation_type": task.installation_type,
                "status": task.status,
                "progress": task.progress,
                "error": task.error,
                "retry_count": task.retry_count,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "duration": task.updated_at - task.created_at
            }
            for task in self.installation_history[-limit:]
        ]
    
    def cleanup_failed_installations(self, project_path: str):
        """Clean up failed installation artifacts."""
        try:
            # Remove temporary files
            temp_files = [
                os.path.join(project_path, "install.tmp"),
                os.path.join(project_path, "download.tmp"),
                os.path.join(project_path, "venv.tmp")
            ]
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")
            
            # Remove incomplete installations
            incomplete_dirs = [
                os.path.join(project_path, "comfyui.incomplete"),
                os.path.join(project_path, "custom_nodes.incomplete")
            ]
            
            for incomplete_dir in incomplete_dirs:
                if os.path.exists(incomplete_dir):
                    shutil.rmtree(incomplete_dir)
                    logger.info(f"Cleaned up incomplete directory: {incomplete_dir}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup failed installation: {e}")

# Global instance
_installation_recovery = None

def get_installation_recovery() -> InstallationRecovery:
    """Get the global installation recovery instance."""
    global _installation_recovery
    if _installation_recovery is None:
        from .integration import get_recovery_integrator
        _installation_recovery = InstallationRecovery(get_recovery_integrator())
    return _installation_recovery