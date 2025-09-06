"""
Integration utilities for applying recovery to existing code.
"""
import asyncio
from typing import Callable, Optional, Any
from functools import wraps

# Import from stub if main recovery system not available
try:
    from .decorator import recoverable
    from .persistence import SQLitePersistence
    from .strategies import ExponentialBackoffStrategy
except ImportError:
    from .decorator_stub import recoverable
    
    class SQLitePersistence:
        def __init__(self, *args, **kwargs):
            pass
        async def load(self, *args): return None
        async def save(self, *args): pass
    
    class ExponentialBackoffStrategy:
        def __init__(self, *args, **kwargs):
            pass
from .download_manager import RecoverableDownloadManager


def enhance_download_manager(existing_manager, persistence: Optional[SQLitePersistence] = None):
    """
    Enhance existing DownloadManager with recovery capabilities.
    
    This monkey-patches the existing download methods to add recovery.
    """
    if not persistence:
        persistence = SQLitePersistence()
    
    # Create recovery strategy for downloads
    download_strategy = ExponentialBackoffStrategy(
        initial_delay=2.0,
        backoff_factor=2.0,
        max_delay=60.0,
        jitter=True
    )
    
    # Store original methods
    original_download_file = existing_manager.download_file
    original_download_with_progress = existing_manager._download_file_with_progress
    
    # Create enhanced download_file method
    @recoverable(
        max_retries=5,
        persistence=persistence,
        strategy=download_strategy,
        timeout=3600  # 1 hour for downloads
    )
    def enhanced_download_file(task):
        """Enhanced download_file with recovery."""
        return original_download_file(task)
    
    # Create enhanced _download_file_with_progress
    @recoverable(
        max_retries=5,
        persistence=persistence,
        strategy=download_strategy,
        timeout=3600
    )
    def enhanced_download_with_progress(url: str, dest_path: str, headers: dict = None):
        """Enhanced download with progress and recovery."""
        return original_download_with_progress(url, dest_path, headers)
    
    # Apply enhancements
    existing_manager.download_file = enhanced_download_file
    existing_manager._download_file_with_progress = enhanced_download_with_progress
    
    # Add recovery status method
    def get_recovery_status(url: str, dest_path: str):
        """Get recovery status for a download."""
        import hashlib
        key = hashlib.sha256(f"{url}:{dest_path}".encode()).hexdigest()
        
        # Run async method in sync context
        async def _get_status():
            recovery_data = await persistence.load(key)
            if recovery_data:
                return {
                    'state': recovery_data.state.value,
                    'attempts': recovery_data.attempt,
                    'last_error': str(recovery_data.error) if recovery_data.error else None,
                    'updated_at': recovery_data.updated_at.isoformat()
                }
            return None
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(_get_status())
    
    existing_manager.get_recovery_status = get_recovery_status
    
    return existing_manager


def create_recoverable_download_function(
    download_func: Callable,
    max_retries: int = 5,
    persistence: Optional[SQLitePersistence] = None
) -> Callable:
    """
    Wrap any download function with recovery capabilities.
    
    Args:
        download_func: Function that downloads files (url, dest_path) -> bool
        max_retries: Maximum retry attempts
        persistence: Optional persistence backend
        
    Returns:
        Enhanced download function with recovery
    """
    if not persistence:
        persistence = SQLitePersistence()
    
    strategy = ExponentialBackoffStrategy(
        initial_delay=1.0,
        backoff_factor=2.0,
        max_delay=60.0
    )
    
    @recoverable(
        max_retries=max_retries,
        persistence=persistence,
        strategy=strategy
    )
    @wraps(download_func)
    def enhanced_func(*args, **kwargs):
        return download_func(*args, **kwargs)
    
    return enhanced_func


def apply_recovery_to_auto_downloader():
    """
    Apply recovery enhancements to the auto_model_downloader module.
    
    This should be called during application startup.
    """
    try:
        from backend.src import auto_model_downloader
        from backend.src.utils import DownloadManager
        
        # Create a simplified download wrapper for auto_model_downloader
        class RecoverableSimpleDownloader:
            def __init__(self, max_workers=2):
                self.max_workers = max_workers
                self.persistence = SQLitePersistence()
            
            @recoverable(
                max_retries=5,
                persistence=SQLitePersistence(),
                strategy=ExponentialBackoffStrategy(
                    initial_delay=2.0,
                    jitter=True
                )
            )
            def download_file(self, url: str, dest_path: str) -> dict:
                """Simple download with recovery."""
                import requests
                import os
                
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Download with streaming
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return {"success": True, "error": None}
        
        # Replace the DownloadManager in auto_model_downloader
        auto_model_downloader.DownloadManager = RecoverableSimpleDownloader
        
        print("Applied recovery enhancements to auto_model_downloader")
        
    except ImportError:
        print("Warning: Could not import auto_model_downloader for enhancement")


def integrate_with_progress_tracker(progress_tracker_instance):
    """
    Integrate recovery with existing progress tracker.
    
    Adds checkpointing and recovery capabilities.
    """
    persistence = SQLitePersistence()
    
    # Store original methods
    original_update = progress_tracker_instance.update_progress
    original_fail = progress_tracker_instance.fail_task
    
    def enhanced_update(task_id: str, progress: float, message: str = ""):
        """Enhanced update with checkpoint."""
        # Call original
        result = original_update(task_id, progress, message)
        
        # Save checkpoint
        async def save_checkpoint():
            from .types import RecoveryData, RecoveryState
            
            recovery_data = RecoveryData(
                operation_id=f"progress_{task_id}",
                function_name="progress_checkpoint",
                args=(task_id,),
                kwargs={"progress": progress, "message": message},
                state=RecoveryState.IN_PROGRESS,
                metadata={
                    "progress": progress,
                    "message": message,
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
            await persistence.save(recovery_data)
        
        # Run async save
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.create_task(save_checkpoint())
        
        return result
    
    def enhanced_fail(task_id: str, error: str):
        """Enhanced fail with recovery metadata."""
        result = original_fail(task_id, error)
        
        # Save failure for recovery
        async def save_failure():
            from .types import RecoveryData, RecoveryState
            
            recovery_data = RecoveryData(
                operation_id=f"progress_{task_id}",
                function_name="progress_checkpoint",
                args=(task_id,),
                kwargs={"error": error},
                state=RecoveryState.FAILED,
                error=Exception(error),
                metadata={"error": error}
            )
            await persistence.save(recovery_data)
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.create_task(save_failure())
        
        return result
    
    # Apply enhancements
    progress_tracker_instance.update_progress = enhanced_update
    progress_tracker_instance.fail_task = enhanced_fail
    
    # Add recovery method
    def recover_progress(task_id: str):
        """Recover progress for a task."""
        async def _recover():
            recovery_data = await persistence.load(f"progress_{task_id}")
            if recovery_data and recovery_data.metadata:
                return recovery_data.metadata.get("progress", 0)
            return 0
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(_recover())
    
    progress_tracker_instance.recover_progress = recover_progress
    
    return progress_tracker_instance