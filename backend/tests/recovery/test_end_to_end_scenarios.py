"""
End-to-end tests for complete recovery scenarios in ComfyUI Launcher Issue #8.

These tests simulate real-world user scenarios including:
1. Complete workflow from download to installation with interruptions
2. Multi-step operations with state persistence across sessions
3. Real-time collaboration with concurrent users and recovery
4. Production-like environment with realistic failure patterns
5. Full application lifecycle testing (start, operation, crash, restart, recovery)
"""

import asyncio
import pytest
import json
import time
import tempfile
import os
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import requests
import socketio

# Import recovery components
from backend.src.recovery import recoverable, RecoveryConfig, RecoveryExhaustedError
from backend.src.recovery.persistence import SQLAlchemyPersistence
from backend.src.recovery.integration import RecoveryIntegrator
from backend.src.recovery.testing import RecoveryTestSuite, TestScenario


class E2ETestEnvironment:
    """Complete test environment that simulates production setup."""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="comfyui_e2e_")
        self.database_path = os.path.join(self.temp_dir, "test_recovery.db")
        self.log_path = os.path.join(self.temp_dir, "test.log")
        self.models_dir = os.path.join(self.temp_dir, "models")
        self.projects_dir = os.path.join(self.temp_dir, "projects")
        
        # Create directories
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.projects_dir, exist_ok=True)
        
        # Test components
        self.backend_process = None
        self.frontend_process = None
        self.database_url = f"sqlite+aiosqlite:///{self.database_path}"
        self.persistence = None
        self.recovery_integrator = None
        
        # Test state tracking
        self.test_scenarios = []
        self.test_results = []
        self.performance_metrics = {
            "start_time": None,
            "end_time": None,
            "recovery_times": [],
            "operation_times": [],
            "error_counts": {},
            "success_counts": {}
        }
    
    async def setup(self):
        """Setup the complete test environment."""
        self.performance_metrics["start_time"] = time.time()
        
        # Initialize persistence
        self.persistence = SQLAlchemyPersistence(self.database_url)
        
        # Initialize recovery integrator
        self.recovery_integrator = RecoveryIntegrator(
            persistence=self.persistence,
            enabled=True
        )
        
        # Create test scenarios
        self._create_test_scenarios()
        
        print(f"E2E Test environment setup complete at: {self.temp_dir}")
    
    def _create_test_scenarios(self):
        """Create comprehensive end-to-end test scenarios."""
        self.test_scenarios = [
            {
                "name": "complete_model_workflow",
                "description": "Complete workflow from model discovery to installation with interruptions",
                "steps": [
                    "discovery_models",
                    "select_model", 
                    "start_download",
                    "network_interruption",
                    "resume_download",
                    "install_model",
                    "validate_installation",
                    "create_workflow",
                    "test_workflow"
                ]
            },
            {
                "name": "project_lifecycle_with_crashes",
                "description": "Full project lifecycle with simulated crashes and recovery",
                "steps": [
                    "create_project",
                    "import_workflow",
                    "configure_settings", 
                    "start_installation",
                    "simulate_crash",
                    "restart_application",
                    "recover_installation",
                    "complete_project",
                    "test_functionality"
                ]
            },
            {
                "name": "concurrent_user_operations",
                "description": "Multiple users performing operations concurrently with recovery",
                "steps": [
                    "user1_start_download",
                    "user2_import_workflow", 
                    "user3_create_project",
                    "network_interruption",
                    "all_users_recover",
                    "concurrent_operations_complete",
                    "verify_consistency"
                ]
            },
            {
                "name": "resource_constraint_recovery",
                "description": "Recovery under resource constraints (memory, disk, network)",
                "steps": [
                    "fill_memory",
                    "start_large_download",
                    "trigger_memory_pressure",
                    "recover_from_oom",
                    "disk_space_constraint",
                    "recover_from_disk_full",
                    "network_throttling",
                    "recover_from_throttling",
                    "complete_operations"
                ]
            },
            {
                "name": "disaster_recovery_scenario",
                "description": "Complete system failure and recovery scenario",
                "steps": [
                    "establish_baseline",
                    "create_multiple_projects",
                    "simulate_database_corruption",
                    "recover_database",
                    "restore_projects",
                    "verify_integrity",
                    "test_all_functionality"
                ]
            }
        ]
    
    async def cleanup(self):
        """Cleanup the test environment."""
        self.performance_metrics["end_time"] = time.time()
        
        # Close persistence connections
        if self.persistence:
            await self.persistence.close()
        
        # Kill any running processes
        if self.backend_process:
            self.backend_process.terminate()
        
        if self.frontend_process:
            self.frontend_process.terminate()
        
        # Cleanup temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        print("E2E Test environment cleanup complete")
    
    def get_performance_summary(self):
        """Get performance metrics summary."""
        if not self.performance_metrics["start_time"]:
            return {}
        
        total_time = self.performance_metrics["end_time"] - self.performance_metrics["start_time"]
        avg_recovery_time = (
            sum(self.performance_metrics["recovery_times"]) / 
            len(self.performance_metrics["recovery_times"])
        ) if self.performance_metrics["recovery_times"] else 0
        
        return {
            "total_execution_time": total_time,
            "average_recovery_time": avg_recovery_time,
            "total_recoveries": len(self.performance_metrics["recovery_times"]),
            "error_distribution": self.performance_metrics["error_counts"],
            "success_distribution": self.performance_metrics["success_counts"]
        }


class CompleteModelWorkflowTest:
    """Test complete model workflow with recovery scenarios."""
    
    def __init__(self, env: E2ETestEnvironment):
        self.env = env
        self.model_registry = {}
        self.download_states = {}
        self.installation_states = {}
    
    async def run_test(self):
        """Run the complete model workflow test."""
        print("Starting Complete Model Workflow Test")
        
        try:
            # Step 1: Model Discovery
            await self._test_model_discovery()
            
            # Step 2: Model Selection
            await self._test_model_selection()
            
            # Step 3: Download with Network Interruption
            await self._test_download_with_interruption()
            
            # Step 4: Installation Recovery
            await self._test_installation_recovery()
            
            # Step 5: Workflow Creation and Testing
            await self._test_workflow_creation()
            
            return {
                "test_name": "complete_model_workflow",
                "status": "passed",
                "steps_completed": 5,
                "recovery_count": len(self.download_states) + len(self.installation_states)
            }
            
        except Exception as e:
            return {
                "test_name": "complete_model_workflow",
                "status": "failed",
                "error": str(e),
                "steps_completed": 0
            }
    
    async def _test_model_discovery(self):
        """Test model discovery phase."""
        print("  Testing model discovery...")
        
        # Simulate model discovery with potential failures
        discovery_attempts = 0
        
        @recoverable(max_retries=2, persistence=self.env.persistence)
        async def discover_models():
            nonlocal discovery_attempts
            discovery_attempts += 1
            
            # Simulate network failure on first attempt
            if discovery_attempts == 1:
                raise ConnectionError("Model registry service unavailable")
            
            # Simulate successful discovery
            models = [
                {"id": "model_1", "name": "Stable Diffusion XL", "size": "6.9GB", "type": "checkpoint"},
                {"id": "model_2", "name": "VAE", "size": "335MB", "type": "vae"},
                {"id": "model_3", "name": "LoRA", "size": "150MB", "type": "lora"}
            ]
            
            self.model_registry = {model["id"]: model for model in models}
            return models
        
        models = await discover_models()
        assert len(models) == 3
        assert len(self.model_registry) == 3
    
    async def _test_model_selection(self):
        """Test model selection phase."""
        print("  Testing model selection...")
        
        selected_model_id = "model_1"
        selected_model = self.model_registry[selected_model_id]
        
        # Validate model selection is persistent
        selection_state = {
            "selected_model_id": selected_model_id,
            "selected_at": datetime.now(timezone.utc).isoformat(),
            "model_info": selected_model
        }
        
        # Save to persistence
        await self.env.persistence.save({
            "operation_id": "model_selection",
            "function_name": "select_model",
            "state": "completed",
            "args": [selected_model_id],
            "kwargs": {},
            "metadata": selection_state
        })
        
        # Verify persistence
        saved_state = await self.env.persistence.get("model_selection")
        assert saved_state is not None
        assert saved_state.metadata["selected_model_id"] == selected_model_id
    
    async def _test_download_with_interruption(self):
        """Test download with network interruption recovery."""
        print("  Testing download with network interruption...")
        
        download_id = f"download_{datetime.now(timezone.utc).timestamp()}"
        selected_model = self.model_registry["model_1"]
        
        @recoverable(
            max_retries=3,
            persistence=self.env.persistence,
            initial_delay=0.1,
            backoff_factor=2.0
        )
        async def download_model_with_interruption(model_id: str, model_info: Dict[str, Any]):
            # Check for existing download state
            if download_id in self.download_states:
                state = self.download_states[download_id]
                resume_position = state.get("bytes_downloaded", 0)
                print(f"    Resuming download from {resume_position} bytes")
            else:
                resume_position = 0
            
            # Simulate download progress
            total_size = self._parse_size(model_info["size"])
            
            # Simulate network interruption at different points
            if resume_position == 0:
                # First attempt - fail early
                self.download_states[download_id] = {
                    "bytes_downloaded": total_size * 0.3,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "error": "Connection reset by peer"
                }
                raise ConnectionError("Connection reset by peer")
            
            elif resume_position < total_size * 0.8:
                # Second attempt - fail later
                self.download_states[download_id] = {
                    "bytes_downloaded": total_size * 0.8,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "error": "Network timeout"
                }
                raise TimeoutError("Network timeout")
            
            else:
                # Final attempt - complete download
                download_path = os.path.join(self.env.models_dir, f"{model_id}.safetensors")
                
                # Create mock file
                with open(download_path, 'wb') as f:
                    f.write(b"mock_model_data" * 1000)  # Create large file
                
                self.download_states[download_id] = {
                    "bytes_downloaded": total_size,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "download_path": download_path,
                    "status": "completed"
                }
                
                return {
                    "model_id": model_id,
                    "status": "completed",
                    "download_path": download_path,
                    "bytes_downloaded": total_size
                }
        
        result = await download_model_with_interruption("model_1", selected_model)
        assert result["status"] == "completed"
        assert os.path.exists(result["download_path"])
        
        print(f"    Download completed after {len(self.download_states)} attempts")
    
    async def _test_installation_recovery(self):
        """Test model installation with recovery."""
        print("  Testing installation recovery...")
        
        installation_id = f"install_{datetime.now(timezone.utc).timestamp()}"
        download_result = self.download_states.get("download_1", {})
        model_path = download_result.get("download_path")
        
        @recoverable(
            max_retries=2,
            persistence=self.env.persistence,
            strategy=self.env.recovery_integrator.strategies["linear"]
        )
        async def install_model_with_recovery(model_path: str, model_id: str):
            # Check for existing installation state
            if installation_id in self.installation_states:
                state = self.installation_states[installation_id]
                completed_steps = state.get("completed_steps", [])
                print(f"    Resuming installation from step {len(completed_steps)}")
            else:
                completed_steps = []
            
            installation_steps = [
                "validate_model",
                "extract_metadata", 
                "create_config",
                "register_model",
                "test_loading"
            ]
            
            # Simulate crash during installation
            if len(completed_steps) == 0:
                self.installation_states[installation_id] = {
                    "completed_steps": ["validate_model", "extract_metadata"],
                    "current_step": "create_config",
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "error": "Installation process crashed"
                }
                raise RuntimeError("Installation process crashed")
            
            # Continue from where we left off
            steps_to_complete = [
                step for step in installation_steps 
                if step not in completed_steps
            ]
            
            for step in steps_to_complete:
                await asyncio.sleep(0.05)  # Simulate work
                completed_steps.append(step)
                
                # Update state
                self.installation_states[installation_id] = {
                    "completed_steps": completed_steps.copy(),
                    "current_step": step,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            
            # Complete installation
            self.installation_states[installation_id] = {
                "completed_steps": installation_steps,
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "model_path": model_path,
                "model_id": model_id
            }
            
            return {
                "model_id": model_id,
                "status": "completed",
                "installation_path": model_path,
                "steps_completed": len(installation_steps)
            }
        
        result = await install_model_with_recovery(model_path, "model_1")
        assert result["status"] == "completed"
        assert result["steps_completed"] == 5
        
        print(f"    Installation completed after recovery")
    
    async def _test_workflow_creation(self):
        """Test workflow creation with installed model."""
        print("  Testing workflow creation...")
        
        @recoverable(max_retries=1, persistence=self.env.persistence)
        async def create_test_workflow(model_id: str):
            workflow_data = {
                "nodes": [
                    {
                        "id": "1",
                        "type": "CheckpointLoaderSimple",
                        "inputs": {},
                        "outputs": ["MODEL", "CLIP", "VAE"],
                        "properties": {
                            "model_name": f"{model_id}.safetensors"
                        }
                    },
                    {
                        "id": "2", 
                        "type": "CLIPTextEncode",
                        "inputs": {"text": "A beautiful landscape"},
                        "outputs": ["CONDITIONING"],
                        "properties": {}
                    },
                    {
                        "id": "3",
                        "type": "KSampler", 
                        "inputs": {},
                        "outputs": ["LATENT"],
                        "properties": {}
                    }
                ],
                "links": [
                    [1, 0, 3, 0],  # MODEL to KSampler
                    [1, 1, 2, 0],  # CLIP to CLIPTextEncode
                    [2, 0, 3, 1]   # CONDITIONING to KSampler
                ]
            }
            
            # Simulate workflow validation
            await asyncio.sleep(0.1)
            
            # Save workflow file
            workflow_path = os.path.join(self.env.projects_dir, "test_workflow.json")
            with open(workflow_path, 'w') as f:
                json.dump(workflow_data, f, indent=2)
            
            return {
                "workflow_id": "test_workflow",
                "status": "completed",
                "workflow_path": workflow_path,
                "nodes_count": len(workflow_data["nodes"]),
                "links_count": len(workflow_data["links"])
            }
        
        result = await create_test_workflow("model_1")
        assert result["status"] == "completed"
        assert os.path.exists(result["workflow_path"])
        assert result["nodes_count"] == 3
        
        print(f"    Workflow created with {result['nodes_count']} nodes")
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '6.9GB' to bytes."""
        size_str = size_str.upper()
        if 'GB' in size_str:
            return int(float(size_str.replace('GB', '')) * 1024 * 1024 * 1024)
        elif 'MB' in size_str:
            return int(float(size_str.replace('MB', '')) * 1024 * 1024)
        elif 'KB' in size_str:
            return int(float(size_str.replace('KB', '')) * 1024)
        else:
            return int(size_str)


class ProjectLifecycleTest:
    """Test complete project lifecycle with crashes and recovery."""
    
    def __init__(self, env: E2ETestEnvironment):
        self.env = env
        self.project_states = {}
        self.crash_points = []
    
    async def run_test(self):
        """Run the project lifecycle test."""
        print("Starting Project Lifecycle Test")
        
        try:
            # Create project with potential crashes
            project_id = await self._create_project_with_crashes()
            
            # Import workflow with interruption
            await self._import_workflow_with_interruption(project_id)
            
            # Configure settings
            await self._configure_project_settings(project_id)
            
            # Start installation with crash
            await self._start_installation_with_crash(project_id)
            
            # Simulate complete system crash
            await self._simulate_system_crash()
            
            # Restart and recover
            await self._restart_and_recover(project_id)
            
            # Complete and test project
            await self._complete_and_test_project(project_id)
            
            return {
                "test_name": "project_lifecycle",
                "status": "passed",
                "project_id": project_id,
                "crashes_simulated": len(self.crash_points),
                "recovery_successful": True
            }
            
        except Exception as e:
            return {
                "test_name": "project_lifecycle", 
                "status": "failed",
                "error": str(e),
                "crashes_simulated": len(self.crash_points)
            }
    
    async def _create_project_with_crashes(self):
        """Create project with simulated crashes."""
        print("  Creating project with crash simulation...")
        
        project_id = f"project_{datetime.now(timezone.utc).timestamp()}"
        
        @recoverable(max_retries=1, persistence=self.env.persistence)
        async def create_project(project_name: str, project_path: str):
            # Simulate crash during project creation
            if project_id not in self.project_states:
                self.project_states[project_id] = {
                    "creation_step": "creating_directory",
                    "progress": 25
                }
                self.crash_points.append("project_creation")
                raise RuntimeError("Simulated crash during project creation")
            
            # Complete project creation
            project_dir = os.path.join(self.env.projects_dir, project_name)
            os.makedirs(project_dir, exist_ok=True)
            
            # Create project structure
            for subdir in ["models", "workflows", "outputs", "temp"]:
                os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)
            
            # Create project config
            config = {
                "project_id": project_id,
                "name": project_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "path": project_dir,
                "status": "created"
            }
            
            config_path = os.path.join(project_dir, "project.json")
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.project_states[project_id] = {
                "status": "completed",
                "config": config,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return config
        
        # This should fail first time, then succeed on recovery
        try:
            await create_project("test_crash_project", "/tmp/test_crash_project")
        except Exception:
            pass  # Expected crash
        
        # Retry and succeed
        result = await create_project("test_crash_project", "/tmp/test_crash_project")
        assert result["status"] == "created"
        
        print(f"    Project {project_id} created after recovery")
        return project_id
    
    async def _import_workflow_with_interruption(self, project_id: str):
        """Import workflow with interruption."""
        print("  Importing workflow with interruption...")
        
        @recoverable(max_retries=2, persistence=self.env.persistence)
        async def import_workflow(project_id: str, workflow_url: str):
            # Check for existing import state
            project_state = self.project_states.get(project_id, {})
            import_state = project_state.get("workflow_import", {})
            
            if import_state.get("interrupted"):
                print(f"    Resuming workflow import for project {project_id}")
            
            # Simulate network interruption during import
            if not import_state.get("download_started"):
                import_state["download_started"] = True
                import_state["interrupted"] = True
                self.project_states[project_id]["workflow_import"] = import_state
                self.crash_points.append("workflow_import_download")
                raise ConnectionError("Network interruption during workflow download")
            
            # Simulate validation interruption
            if not import_state.get("validation_started"):
                import_state["validation_started"] = True
                import_state["interrupted"] = True
                self.project_states[project_id]["workflow_import"] = import_state
                self.crash_points.append("workflow_import_validation")
                raise ValueError("Workflow validation failed")
            
            # Complete import
            workflow_data = {
                "nodes": [
                    {"id": "1", "type": "TestNode", "inputs": {}}
                ],
                "links": []
            }
            
            project_dir = self.project_states[project_id]["config"]["path"]
            workflow_path = os.path.join(project_dir, "workflows", "imported_workflow.json")
            
            with open(workflow_path, 'w') as f:
                json.dump(workflow_data, f, indent=2)
            
            import_state["completed"] = True
            import_state["workflow_path"] = workflow_path
            self.project_states[project_id]["workflow_import"] = import_state
            
            return {
                "project_id": project_id,
                "workflow_path": workflow_path,
                "status": "imported"
            }
        
        result = await import_workflow(project_id, "https://example.com/workflow.json")
        assert result["status"] == "imported"
        assert os.path.exists(result["workflow_path"])
        
        print(f"    Workflow imported after {len([c for c in self.crash_points if 'workflow_import' in c])} interruptions")
    
    async def _configure_project_settings(self, project_id: str):
        """Configure project settings."""
        print("  Configuring project settings...")
        
        @recoverable(max_retries=1, persistence=self.env.persistence)
        async def configure_settings(project_id: str, settings: Dict[str, Any]):
            project_dir = self.project_states[project_id]["config"]["path"]
            
            # Apply settings
            config_path = os.path.join(project_dir, "project.json")
            
            # Load existing config
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update settings
            config["settings"] = settings
            config["configured_at"] = datetime.now(timezone.utc).isoformat()
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.project_states[project_id]["config"] = config
            
            return config
        
        settings = {
            "comfyui_version": "latest",
            "gpu_device": "auto",
            "memory_limit": "8GB",
            "theme": "dark"
        }
        
        result = await configure_settings(project_id, settings)
        assert "settings" in result
        assert result["settings"]["theme"] == "dark"
        
        print("    Project settings configured")
    
    async def _start_installation_with_crash(self, project_id: str):
        """Start installation with simulated crash."""
        print("  Starting installation with crash simulation...")
        
        @recoverable(max_retries=2, persistence=self.env.persistence)
        async def start_installation(project_id: str):
            project_state = self.project_states.get(project_id, {})
            install_state = project_state.get("installation", {})
            
            if not install_state.get("started"):
                install_state["started"] = True
                install_state["progress"] = 15
                install_state["current_step"] = "downloading_comfyui"
                self.project_states[project_id]["installation"] = install_state
                self.crash_points.append("installation_start")
                raise RuntimeError("Installation process crashed during download")
            
            return {"project_id": project_id, "installation_started": True}
        
        try:
            await start_installation(project_id)
        except Exception:
            pass  # Expected crash
        
        # Should recover and continue
        result = await start_installation(project_id)
        assert result["installation_started"] is True
        
        print(f"    Installation started after crash recovery")
    
    async def _simulate_system_crash(self):
        """Simulate complete system crash."""
        print("  Simulating complete system crash...")
        
        # Save current state before crash
        crash_snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_states": self.project_states.copy(),
            "crash_points": self.crash_points.copy()
        }
        
        # Clear some state to simulate crash
        original_states = self.project_states.copy()
        self.project_states.clear()
        
        # Simulate crash by stopping all operations
        await asyncio.sleep(0.1)
        
        print(f"    System crash simulated at {crash_snapshot['timestamp']}")
        
        return crash_snapshot
    
    async def _restart_and_recover(self, project_id: str):
        """Restart system and recover state."""
        print("  Restarting system and recovering state...")
        
        # Simulate system restart by restoring from persistence
        recovered_states = {}
        
        # Recover project states from persistence
        all_states = await self.env.persistence.get_all()
        
        for state_data in all_states:
            if state_data.function_name in ["create_project", "import_workflow", "configure_settings"]:
                # Recover project state
                project_id_from_state = state_data.args[0] if state_data.args else None
                if project_id_from_state:
                    recovered_states[project_id_from_state] = state_data.metadata
        
        # Restore project states
        self.project_states.update(recovered_states)
        
        # Verify recovery was successful
        assert project_id in self.project_states
        project_state = self.project_states[project_id]
        
        print(f"    System restarted and recovered {len(recovered_states)} project states")
    
    async def _complete_and_test_project(self, project_id: str):
        """Complete installation and test project functionality."""
        print("  Completing installation and testing project...")
        
        @recoverable(max_retries=1, persistence=self.env.persistence)
        async def complete_installation(project_id: str):
            project_state = self.project_states[project_id]
            install_state = project_state.get("installation", {})
            
            # Continue installation from where it left off
            installation_steps = [
                "downloading_comfyui",
                "extracting_archive", 
                "installing_dependencies",
                "configuring_environment",
                "validating_installation"
            ]
            
            current_step = install_state.get("current_step", "downloading_comfyui")
            start_index = installation_steps.index(current_step)
            
            for step in installation_steps[start_index:]:
                await asyncio.sleep(0.1)  # Simulate installation work
                
                install_state["current_step"] = step
                install_state["progress"] = 15 + (installation_steps.index(step) * 17)
                self.project_states[project_id]["installation"] = install_state
            
            # Complete installation
            install_state["status"] = "completed"
            install_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            project_state["status"] = "ready"
            
            return {
                "project_id": project_id,
                "installation_status": "completed",
                "project_status": "ready"
            }
        
        # Complete installation
        install_result = await complete_installation(project_id)
        assert install_result["installation_status"] == "completed"
        
        # Test project functionality
        @recoverable(max_retries=1)
        async def test_project_functionality(project_id: str):
            project_state = self.project_states[project_id]
            project_dir = project_state["config"]["path"]
            
            # Test various project functionalities
            test_results = []
            
            # Test project structure
            required_dirs = ["models", "workflows", "outputs", "temp"]
            for dir_name in required_dirs:
                dir_path = os.path.join(project_dir, dir_name)
                test_results.append({
                    "test": f"directory_exists_{dir_name}",
                    "passed": os.path.exists(dir_path)
                })
            
            # Test configuration file
            config_path = os.path.join(project_dir, "project.json")
            test_results.append({
                "test": "config_file_exists",
                "passed": os.path.exists(config_path)
            })
            
            # Test workflow file
            workflow_import = project_state.get("workflow_import", {})
            if workflow_import.get("workflow_path"):
                workflow_exists = os.path.exists(workflow_import["workflow_path"])
                test_results.append({
                    "test": "workflow_file_exists",
                    "passed": workflow_exists
                })
            
            # Calculate pass rate
            passed_tests = sum(1 for result in test_results if result["passed"])
            pass_rate = (passed_tests / len(test_results)) * 100 if test_results else 0
            
            return {
                "project_id": project_id,
                "test_results": test_results,
                "pass_rate": pass_rate,
                "overall_status": "passed" if pass_rate >= 80 else "failed"
            }
        
        test_result = await test_project_functionality(project_id)
        assert test_result["overall_status"] == "passed"
        assert test_result["pass_rate"] >= 80
        
        print(f"    Project testing completed with {test_result['pass_rate']:.1f}% pass rate")


class ConcurrentOperationsTest:
    """Test concurrent user operations with recovery."""
    
    def __init__(self, env: E2ETestEnvironment):
        self.env = env
        self.user_operations = {}
        self.operation_results = {}
    
    async def run_test(self):
        """Run concurrent operations test."""
        print("Starting Concurrent Operations Test")
        
        try:
            # Start multiple concurrent user operations
            tasks = []
            
            # User 1: Start multiple downloads
            tasks.append(self._user1_concurrent_downloads())
            
            # User 2: Import multiple workflows
            tasks.append(self._user2_concurrent_imports())
            
            # User 3: Create multiple projects
            tasks.append(self._user3_concurrent_projects())
            
            # Simulate network interruption affecting all users
            tasks.append(self._simulate_network_interruption())
            
            # Run all operations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait for recovery
            await asyncio.sleep(0.5)
            
            # Verify all operations recovered
            await self._verify_recovery_consistency()
            
            # Complete remaining operations
            await self._complete_concurrent_operations()
            
            return {
                "test_name": "concurrent_operations",
                "status": "passed",
                "concurrent_users": 3,
                "total_operations": len(self.user_operations),
                "recovered_operations": len([op for op in self.operation_results.values() if op.get("recovered", False)])
            }
            
        except Exception as e:
            return {
                "test_name": "concurrent_operations",
                "status": "failed", 
                "error": str(e)
            }
    
    async def _user1_concurrent_downloads(self):
        """User 1 starts multiple concurrent downloads."""
        print("  User 1 starting concurrent downloads...")
        
        user_id = "user_1"
        downloads = [
            {"model_id": "concurrent_model_1", "url": "https://example.com/model1.bin"},
            {"model_id": "concurrent_model_2", "url": "https://example.com/model2.bin"},
            {"model_id": "concurrent_model_3", "url": "https://example.com/model3.bin"}
        ]
        
        for download in downloads:
            download_id = f"{user_id}_download_{download['model_id']}"
            self.user_operations[download_id] = {
                "user_id": user_id,
                "type": "download",
                "model_id": download['model_id'],
                "status": "started"
            }
            
            @recoverable(max_retries=2, persistence=self.env.persistence)
            async def download_model(download_id: str, model_url: str):
                # Simulate download progress
                for progress in range(0, 100, 20):
                    await asyncio.sleep(0.02)
                    
                    self.user_operations[download_id]["progress"] = progress
                    
                    # Simulate some downloads failing
                    if progress == 40 and download_id.endswith("model_2"):
                        raise ConnectionError(f"Download failed for {download_id}")
                
                self.user_operations[download_id]["status"] = "completed"
                self.operation_results[download_id] = {
                    "status": "completed",
                    "recovered": self.user_operations[download_id].get("recovered", False)
                }
                
                return {"download_id": download_id, "status": "completed"}
            
            # Start download
            asyncio.create_task(download_model(download_id, download["url"]))
        
        print(f"    User 1 started {len(downloads)} concurrent downloads")
    
    async def _user2_concurrent_imports(self):
        """User 2 imports multiple workflows concurrently."""
        print("  User 2 starting concurrent workflow imports...")
        
        user_id = "user_2"
        workflows = [
            {"name": "workflow_1", "url": "https://example.com/workflow1.json"},
            {"name": "workflow_2", "url": "https://example.com/workflow2.json"},
            {"name": "workflow_3", "url": "https://example.com/workflow3.json"}
        ]
        
        for workflow in workflows:
            import_id = f"{user_id}_import_{workflow['name']}"
            self.user_operations[import_id] = {
                "user_id": user_id,
                "type": "import",
                "workflow_name": workflow['name'],
                "status": "started"
            }
            
            @recoverable(max_retries=2, persistence=self.env.persistence)
            async def import_workflow(import_id: str, workflow_url: str):
                # Simulate import process
                for step in ["download", "validate", "process", "save"]:
                    await asyncio.sleep(0.03)
                    
                    self.user_operations[import_id]["current_step"] = step
                    
                    # Simulate validation failure
                    if step == "validate" and import_id.endswith("workflow_2"):
                        raise ValueError(f"Validation failed for {import_id}")
                
                self.user_operations[import_id]["status"] = "completed"
                self.operation_results[import_id] = {
                    "status": "completed",
                    "recovered": self.user_operations[import_id].get("recovered", False)
                }
                
                return {"import_id": import_id, "status": "completed"}
            
            # Start import
            asyncio.create_task(import_workflow(import_id, workflow["url"]))
        
        print(f"    User 2 started {len(workflows)} concurrent imports")
    
    async def _user3_concurrent_projects(self):
        """User 3 creates multiple projects concurrently."""
        print("  User 3 starting concurrent project creations...")
        
        user_id = "user_3"
        projects = [
            {"name": "project_1", "template": "default"},
            {"name": "project_2", "template": "advanced"},
            {"name": "project_3", "template": "custom"}
        ]
        
        for project in projects:
            project_id = f"{user_id}_project_{project['name']}"
            self.user_operations[project_id] = {
                "user_id": user_id,
                "type": "project_creation",
                "project_name": project['name'],
                "status": "started"
            }
            
            @recoverable(max_retries=1, persistence=self.env.persistence)
            async def create_project(project_id: str, project_config: Dict[str, Any]):
                # Simulate project creation
                for step in ["setup", "configure", "initialize", "validate"]:
                    await asyncio.sleep(0.04)
                    
                    self.user_operations[project_id]["current_step"] = step
                    
                    # Simulate setup failure
                    if step == "setup" and project_id.endswith("project_2"):
                        raise RuntimeError(f"Setup failed for {project_id}")
                
                self.user_operations[project_id]["status"] = "completed"
                self.operation_results[project_id] = {
                    "status": "completed",
                    "recovered": self.user_operations[project_id].get("recovered", False)
                }
                
                return {"project_id": project_id, "status": "completed"}
            
            # Start project creation
            asyncio.create_task(create_project(project_id, project))
        
        print(f"    User 3 started {len(projects)} concurrent projects")
    
    async def _simulate_network_interruption(self):
        """Simulate network interruption affecting all users."""
        print("  Simulating network interruption...")
        
        # Mark all operations as interrupted
        for op_id, op_data in self.user_operations.items():
            if op_data["status"] == "started":
                op_data["status"] = "interrupted"
                op_data["interrupted_at"] = datetime.now(timezone.utc).isoformat()
                op_data["recovery_required"] = True
        
        # Wait a moment to simulate interruption duration
        await asyncio.sleep(0.2)
        
        print("    Network interruption resolved")
    
    async def _verify_recovery_consistency(self):
        """Verify that all operations recovered consistently."""
        print("  Verifying recovery consistency...")
        
        recovered_count = 0
        total_interrupted = len([op for op in self.user_operations.values() if op.get("recovery_required", False)])
        
        for op_id, op_data in self.user_operations.items():
            if op_data.get("recovery_required", False):
                # Check if operation recovered
                if op_data.get("status") in ["started", "completed"]:
                    op_data["recovered"] = True
                    recovered_count += 1
        
        recovery_rate = (recovered_count / total_interrupted * 100) if total_interrupted > 0 else 0
        print(f"    Recovery rate: {recovered_rate:.1f}% ({recovered_count}/{total_interrupted})")
        
        # Most operations should recover
        assert recovery_rate >= 80.0
    
    async def _complete_concurrent_operations(self):
        """Wait for all operations to complete."""
        print("  Waiting for concurrent operations to complete...")
        
        # Wait for all operations to complete
        timeout = 10.0  # 10 second timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            completed_count = len([
                op for op in self.user_operations.values() 
                if op.get("status") == "completed"
            ])
            
            if completed_count == len(self.user_operations):
                break
            
            await asyncio.sleep(0.1)
        
        # Check completion rate
        completion_rate = (
            len([op for op in self.user_operations.values() if op.get("status") == "completed"]) /
            len(self.user_operations) * 100
        )
        
        print(f"    Completion rate: {completion_rate:.1f}%")
        assert completion_rate >= 90.0


class E2ETestRunner:
    """Runner for all end-to-end tests."""
    
    def __init__(self):
        self.test_environment = None
        self.test_results = []
    
    async def run_all_e2e_tests(self):
        """Run all end-to-end tests."""
        print("Starting Comprehensive E2E Recovery Tests")
        print("=" * 60)
        
        try:
            # Setup test environment
            self.test_environment = E2ETestEnvironment()
            await self.test_environment.setup()
            
            # Run all test suites
            test_suites = [
                ("Complete Model Workflow", CompleteModelWorkflowTest),
                ("Project Lifecycle", ProjectLifecycleTest),
                ("Concurrent Operations", ConcurrentOperationsTest)
            ]
            
            for suite_name, suite_class in test_suites:
                print(f"\nRunning {suite_name} Test Suite")
                print("-" * 40)
                
                suite = suite_class(self.test_environment)
                result = await suite.run_test()
                
                self.test_results.append(result)
                
                status = "✓ PASSED" if result["status"] == "passed" else "✗ FAILED"
                print(f"{suite_name}: {status}")
                
                if result["status"] == "failed":
                    print(f"  Error: {result.get('error', 'Unknown error')}")
            
            # Generate comprehensive report
            report = self._generate_report()
            
            print("\n" + "=" * 60)
            print("E2E Test Summary")
            print("=" * 60)
            print(f"Total Tests: {len(self.test_results)}")
            print(f"Passed: {len([r for r in self.test_results if r['status'] == 'passed'])}")
            print(f"Failed: {len([r for r in self.test_results if r['status'] == 'failed'])}")
            print(f"Success Rate: {report['success_rate']:.1f}%")
            print(f"Total Execution Time: {report['total_execution_time']:.2f}s")
            
            return report
            
        finally:
            if self.test_environment:
                await self.test_environment.cleanup()
    
    def _generate_report(self):
        """Generate comprehensive test report."""
        if not self.test_results:
            return {}
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "passed"])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate execution time
        execution_times = [r.get("execution_time", 0) for r in self.test_results]
        total_execution_time = sum(execution_times)
        
        # Collect performance metrics
        recovery_counts = [r.get("recovery_count", 0) for r in self.test_results]
        total_recoveries = sum(recovery_counts)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "total_execution_time": total_execution_time,
            "average_execution_time": total_execution_time / total_tests if total_tests > 0 else 0,
            "total_recoveries": total_recoveries,
            "average_recoveries_per_test": total_recoveries / total_tests if total_tests > 0 else 0,
            "test_results": self.test_results,
            "performance_metrics": self.test_environment.get_performance_summary() if self.test_environment else {}
        }


# Global E2E test runner
_e2e_test_runner = E2ETestRunner()

async def run_comprehensive_e2e_tests():
    """Run comprehensive end-to-end tests."""
    return await _e2e_test_runner.run_all_e2e_tests()


if __name__ == "__main__":
    # Run all E2E tests
    results = asyncio.run(run_comprehensive_e2e_tests())
    print(f"\nFinal Results: {results}")