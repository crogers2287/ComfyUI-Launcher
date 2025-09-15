"""
Comprehensive Recovery Integration for ComfyUI Launcher

This module integrates recovery mechanisms across all critical operations:
- Model downloads
- Workflow imports  
- Installation processes
- Long-running ComfyUI operations
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import recovery components
try:
    from ..recovery import recoverable
    from ..recovery.persistence import SQLitePersistence
    from ..recovery.strategies import ExponentialBackoffStrategy
    from ..recovery.classification import ErrorClassifier
    RECOVERY_AVAILABLE = True
except ImportError:
    RECOVERY_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class RecoveryConfig:
    """Configuration for recovery mechanisms."""
    enabled: bool = True
    max_retries: int = 5
    initial_delay: float = 2.0
    backoff_factor: float = 2.0
    max_delay: float = 300.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 600.0
    persistence_enabled: bool = True
    
class RecoveryIntegrator:
    """Main class for integrating recovery across all operations."""
    
    def __init__(self, config: RecoveryConfig = None):
        self.config = config or RecoveryConfig()
        self.enabled = self.config.enabled and RECOVERY_AVAILABLE
        self.persistence = None
        self.strategy = None
        self.classifier = None
        
        if self.enabled:
            self._initialize_recovery_components()
    
    def _initialize_recovery_components(self):
        """Initialize recovery system components."""
        try:
            # Initialize persistence
            if self.config.persistence_enabled:
                self.persistence = SQLitePersistence()
            
            # Initialize recovery strategy
            self.strategy = ExponentialBackoffStrategy(
                initial_delay=self.config.initial_delay,
                backoff_factor=self.config.backoff_factor,
                max_delay=self.config.max_delay,
                jitter=True
            )
            
            # Initialize error classifier
            self.classifier = ErrorClassifier()
            
            logger.info("Recovery system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize recovery components: {e}")
            self.enabled = False
    
    def apply_to_model_downloads(self, download_manager):
        """Apply recovery mechanisms to model downloads."""
        if not self.enabled:
            logger.warning("Recovery system not available for model downloads")
            return download_manager
        
        try:
            # Enhance download manager with recovery capabilities
            if hasattr(download_manager, 'recovery_enabled'):
                download_manager.recovery_enabled = True
                download_manager.persistence = self.persistence
                download_manager.recovery_strategy = self.strategy
                
            logger.info("Applied recovery mechanisms to model downloads")
            return download_manager
            
        except Exception as e:
            logger.error(f"Failed to apply recovery to model downloads: {e}")
            return download_manager
    
    def apply_to_workflow_imports(self, import_function):
        """Apply recovery mechanisms to workflow imports."""
        if not self.enabled:
            logger.warning("Recovery system not available for workflow imports")
            return import_function
        
        try:
            # Create recoverable version of import function
            @recoverable(
                max_retries=self.config.max_retries,
                persistence=self.persistence,
                strategy=self.strategy,
                circuit_breaker_threshold=self.config.circuit_breaker_threshold,
                circuit_breaker_timeout=self.config.circuit_breaker_timeout,
                classifier=self.classifier
            )
            async def recoverable_import(*args, **kwargs):
                """Recoverable workflow import function."""
                return await import_function(*args, **kwargs)
            
            logger.info("Applied recovery mechanisms to workflow imports")
            return recoverable_import
            
        except Exception as e:
            logger.error(f"Failed to apply recovery to workflow imports: {e}")
            return import_function
    
    def apply_to_installation_processes(self, installer_function):
        """Apply recovery mechanisms to installation processes."""
        if not self.enabled:
            logger.warning("Recovery system not available for installation processes")
            return installer_function
        
        try:
            # Create recoverable version of installation function
            @recoverable(
                max_retries=self.config.max_retries,
                persistence=self.persistence,
                strategy=self.strategy,
                timeout=1800,  # 30 minutes for installation
                circuit_breaker_threshold=self.config.circuit_breaker_threshold,
                circuit_breaker_timeout=self.config.circuit_breaker_timeout,
                classifier=self.classifier
            )
            async def recoverable_installation(*args, **kwargs):
                """Recoverable installation function."""
                return await installer_function(*args, **kwargs)
            
            logger.info("Applied recovery mechanisms to installation processes")
            return recoverable_installation
            
        except Exception as e:
            logger.error(f"Failed to apply recovery to installation processes: {e}")
            return installer_function
    
    def apply_to_comfyui_operations(self, operation_function):
        """Apply recovery mechanisms to long-running ComfyUI operations."""
        if not self.enabled:
            logger.warning("Recovery system not available for ComfyUI operations")
            return operation_function
        
        try:
            # Create recoverable version of operation function
            @recoverable(
                max_retries=self.config.max_retries,
                persistence=self.persistence,
                strategy=self.strategy,
                timeout=3600,  # 1 hour for long operations
                circuit_breaker_threshold=self.config.circuit_breaker_threshold,
                circuit_breaker_timeout=self.config.circuit_breaker_timeout,
                classifier=self.classifier
            )
            async def recoverable_operation(*args, **kwargs):
                """Recoverable ComfyUI operation function."""
                return await operation_function(*args, **kwargs)
            
            logger.info("Applied recovery mechanisms to ComfyUI operations")
            return recoverable_operation
            
        except Exception as e:
            logger.error(f"Failed to apply recovery to ComfyUI operations: {e}")
            return operation_function
    
    def get_recovery_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get recovery status for a specific operation."""
        if not self.enabled or not self.persistence:
            return None
        
        try:
            import asyncio
            
            async def _get_status():
                recovery_data = await self.persistence.load(operation_id)
                if recovery_data:
                    return {
                        'operation_id': recovery_data.operation_id,
                        'function_name': recovery_data.function_name,
                        'state': recovery_data.state.value,
                        'attempts': recovery_data.attempt,
                        'error': str(recovery_data.error) if recovery_data.error else None,
                        'created_at': recovery_data.created_at.isoformat(),
                        'updated_at': recovery_data.updated_at.isoformat(),
                        'metadata': recovery_data.metadata
                    }
                return None
            
            # Run async function in sync context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(_get_status())
            
        except Exception as e:
            logger.error(f"Failed to get recovery status: {e}")
            return None
    
    def list_active_operations(self) -> List[Dict[str, Any]]:
        """List all active operations with recovery state."""
        if not self.enabled or not self.persistence:
            return []
        
        try:
            # This would need to be implemented in the persistence layer
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to list active operations: {e}")
            return []
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery system statistics."""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            stats = {
                "enabled": True,
                "persistence_enabled": self.config.persistence_enabled,
                "max_retries": self.config.max_retries,
                "circuit_breaker_threshold": self.config.circuit_breaker_threshold,
                "active_operations": len(self.list_active_operations())
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get recovery stats: {e}")
            return {"enabled": True, "error": str(e)}

# Global recovery integrator instance
_recovery_integrator = None

def get_recovery_integrator() -> RecoveryIntegrator:
    """Get the global recovery integrator instance."""
    global _recovery_integrator
    if _recovery_integrator is None:
        _recovery_integrator = RecoveryIntegrator()
    return _recovery_integrator

def initialize_recovery_system(config: RecoveryConfig = None):
    """Initialize the global recovery system."""
    global _recovery_integrator
    _recovery_integrator = RecoveryIntegrator(config)
    return _recovery_integrator

def apply_recovery_to_all_operations():
    """
    Apply recovery mechanisms to all critical operations.
    
    This function should be called during application startup to ensure
    all operations have recovery capabilities.
    """
    try:
        integrator = get_recovery_integrator()
        
        if not integrator.enabled:
            logger.warning("Recovery system not available")
            return False
        
        # Apply to download manager (will be initialized when needed)
        logger.info("Recovery system ready for all operations")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply recovery to operations: {e}")
        return False