"""
Example integrations of the recovery system with ComfyUI Launcher.
"""
import asyncio
import aiohttp
from pathlib import Path

from .decorator import recoverable
from .persistence import SQLitePersistence
from .strategies import ExponentialBackoffStrategy


# Example 1: Model Download with Resume
@recoverable(
    max_retries=5,
    persistence=SQLitePersistence(),
    strategy=ExponentialBackoffStrategy(initial_delay=2.0, jitter=True)
)
async def download_model_with_resume(
    model_url: str,
    destination_path: Path,
    progress_callback=None
):
    """
    Download a model with automatic resume on failure.
    
    Args:
        model_url: URL of the model to download
        destination_path: Where to save the model
        progress_callback: Optional callback(bytes_downloaded, total_bytes)
    """
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if partial download exists
    if destination_path.exists():
        resume_pos = destination_path.stat().st_size
    else:
        resume_pos = 0
    
    headers = {}
    if resume_pos > 0:
        headers['Range'] = f'bytes={resume_pos}-'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(model_url, headers=headers) as response:
            response.raise_for_status()
            
            # Get total size
            if resume_pos > 0:
                total_size = resume_pos + int(response.headers.get('content-length', 0))
            else:
                total_size = int(response.headers.get('content-length', 0))
            
            # Open file in append mode if resuming
            mode = 'ab' if resume_pos > 0 else 'wb'
            
            with open(destination_path, mode) as f:
                downloaded = resume_pos
                
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress_callback(downloaded, total_size)
    
    return destination_path


# Example 2: Workflow Validation with Recovery
@recoverable(
    max_retries=3,
    timeout=30.0,  # 30 second timeout per attempt
    strategy=ExponentialBackoffStrategy(
        initial_delay=0.5,
        non_retryable_exceptions={ValueError, KeyError}
    )
)
async def validate_workflow_with_recovery(workflow_data: dict, api_endpoint: str):
    """
    Validate workflow with automatic recovery from network issues.
    
    Args:
        workflow_data: Workflow to validate
        api_endpoint: Validation API endpoint
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            api_endpoint,
            json=workflow_data,
            timeout=aiohttp.ClientTimeout(total=25)
        ) as response:
            if response.status == 400:
                # Validation error - don't retry
                error_data = await response.json()
                raise ValueError(f"Validation failed: {error_data['error']}")
            
            response.raise_for_status()
            return await response.json()


# Example 3: Batch Operation with Progress
class BatchProcessor:
    def __init__(self):
        self.persistence = SQLitePersistence()
        self.processed_items = set()
    
    @recoverable(
        max_retries=3,
        persistence=SQLitePersistence(),
        initial_delay=1.0
    )
    async def process_batch(self, items: list, operation_id: str = None):
        """
        Process a batch of items with recovery.
        
        The operation_id allows resuming the exact same batch if interrupted.
        """
        results = []
        
        for i, item in enumerate(items):
            # Skip already processed items (for resume)
            if item['id'] in self.processed_items:
                continue
            
            try:
                result = await self._process_single_item(item)
                results.append(result)
                self.processed_items.add(item['id'])
            except Exception as e:
                # Log but continue with other items
                print(f"Failed to process {item['id']}: {e}")
        
        return results
    
    async def _process_single_item(self, item):
        # Simulate processing
        await asyncio.sleep(0.1)
        return {"id": item['id'], "status": "processed"}


# Example 4: Integration with existing progress tracker
def integrate_with_progress_tracker(progress_tracker):
    """
    Example of integrating recovery with existing progress tracking.
    """
    from functools import wraps
    
    def with_recovery_progress(func):
        @wraps(func)
        @recoverable(
            max_retries=3,
            persistence=SQLitePersistence()
        )
        async def wrapper(*args, **kwargs):
            # Save progress state before attempt
            operation_id = kwargs.get('_recovery_operation_id', 'unknown')
            progress_tracker.save_checkpoint(operation_id)
            
            try:
                result = await func(*args, **kwargs)
                progress_tracker.mark_complete(operation_id)
                return result
            except Exception as e:
                progress_tracker.mark_failed(operation_id, str(e))
                raise
        
        return wrapper
    
    return with_recovery_progress


# Example 5: WebSocket notification integration
@recoverable(max_retries=3)
async def operation_with_socket_updates(data: dict, socket_io):
    """
    Example of emitting recovery status via WebSocket.
    """
    operation_id = data.get('operation_id', 'unknown')
    
    async def emit_status(status: str, details: dict = None):
        await socket_io.emit('recovery_status', {
            'operation_id': operation_id,
            'status': status,
            'details': details or {}
        })
    
    try:
        await emit_status('started')
        result = await process_data(data)
        await emit_status('completed', {'result': result})
        return result
    except Exception as e:
        await emit_status('retrying', {'error': str(e)})
        raise


# Example helper for existing code migration
def add_recovery_to_existing_function(
    func,
    max_retries=3,
    network_errors_only=True
):
    """
    Helper to add recovery to existing functions without modifying them.
    
    Usage:
        download_file = add_recovery_to_existing_function(
            original_download_file,
            max_retries=5
        )
    """
    if network_errors_only:
        from .types import ErrorCategory
        strategy = ExponentialBackoffStrategy(
            retryable_categories={ErrorCategory.NETWORK, ErrorCategory.TIMEOUT}
        )
    else:
        strategy = None
    
    return recoverable(
        max_retries=max_retries,
        strategy=strategy,
        initial_delay=1.0
    )(func)