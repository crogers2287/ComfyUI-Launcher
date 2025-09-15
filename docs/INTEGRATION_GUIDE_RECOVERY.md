# Recovery System Integration Documentation

## Overview

This document provides comprehensive guidance for integrating the ComfyUI Launcher Recovery System into new operations, extending existing functionality, and implementing custom recovery strategies. The recovery system is designed to be extensible, configurable, and easy to integrate.

## Quick Start Integration

### Basic Function Integration

The simplest way to add recovery capabilities to any function is using the `@recoverable` decorator:

```python
from backend.src.recovery import recoverable

@recoverable(max_retries=3)
async def download_model(url: str, destination: str):
    """Download a model with automatic recovery"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            with open(destination, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
    return destination
```

### With Progress Tracking

For operations that benefit from progress tracking:

```python
@recoverable(max_retries=3, persistence=SQLitePersistence())
async def download_with_progress(url: str, destination: str, progress_tracker):
    """Download with progress preservation"""
    total_size = 0
    downloaded = 0
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            
            with open(destination, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress_tracker.update(downloaded, total_size)
    
    progress_tracker.complete()
    return destination
```

## Advanced Integration Patterns

### 1. State Persistence Integration

For operations that need to preserve complex state:

```python
@dataclass
class DownloadState:
    url: str
    destination: str
    downloaded_bytes: int
    total_bytes: int
    chunk_size: int
    last_modified: Optional[str] = None

@recoverable(
    max_retries=5,
    persistence=SQLitePersistence(),
    state_serializer=lambda state: {
        'url': state.url,
        'destination': state.destination,
        'downloaded_bytes': state.downloaded_bytes,
        'total_bytes': state.total_bytes,
        'chunk_size': state.chunk_size,
        'last_modified': state.last_modified
    },
    state_deserializer=lambda data: DownloadState(**data)
)
async def resilient_download(state: DownloadState):
    """Resume download from preserved state"""
    # Check if file exists and get current size
    if os.path.exists(state.destination):
        current_size = os.path.getsize(state.destination)
        if current_size >= state.downloaded_bytes:
            state.downloaded_bytes = current_size
    
    # Continue download with Range header
    headers = {}
    if state.downloaded_bytes > 0:
        headers['Range'] = f'bytes={state.downloaded_bytes}-'
    
    async with aiohttp.ClientSession() as session:
        async with session.get(state.url, headers=headers) as response:
            with open(state.destination, 'ab' if state.downloaded_bytes > 0 else 'wb') as f:
                async for chunk in response.content.iter_chunked(state.chunk_size):
                    f.write(chunk)
                    state.downloaded_bytes += len(chunk)
    
    return state.destination
```

### 2. Custom Retry Strategies

Implement domain-specific retry strategies:

```python
from backend.src.recovery.strategies import CustomStrategy

class ModelDownloadStrategy(CustomStrategy):
    """Specialized strategy for model downloads"""
    
    def __init__(self):
        super().__init__(
            delay_func=self._calculate_model_delay,
            name="ModelDownload"
        )
    
    def _calculate_model_delay(self, attempt: int) -> float:
        """Calculate delay based on attempt and model characteristics"""
        base_delay = 2.0
        max_delay = 300.0
        
        if attempt <= 3:
            # Fast retry for transient issues
            return base_delay * (2 ** (attempt - 1))
        else:
            # Slower retry for persistent issues
            return min(max_delay, base_delay * (attempt - 2))
    
    def should_retry(self, error: Exception, attempt: int, max_attempts: int) -> bool:
        """Custom retry logic for model downloads"""
        if attempt >= max_attempts:
            return False
        
        # Don't retry authentication errors
        if isinstance(error, (AuthenticationError, PermissionError)):
            return False
        
        # Always retry network and timeout errors
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True
        
        # Retry HTTP 429 (rate limit) and 5xx errors
        if hasattr(error, 'status_code'):
            if error.status_code == 429:
                return True
            if 500 <= error.status_code < 600:
                return True
        
        return attempt < 3  # Retry other errors up to 3 times

@recoverable(strategy=ModelDownloadStrategy())
async def download_model_with_custom_strategy(url: str, destination: str):
    """Download model with specialized recovery strategy"""
    # Download implementation
    pass
```

### 3. Error Classification Integration

Custom error classification for specific domains:

```python
from backend.src.recovery.classification import ErrorClassifier, ErrorCategory

class ModelDownloadErrorClassifier(ErrorClassifier):
    """Specialized error classifier for model downloads"""
    
    def classify_error(self, error: Exception) -> ErrorCategory:
        """Classify model download specific errors"""
        error_str = str(error).lower()
        
        # Network-related errors
        if any(keyword in error_str for keyword in [
            'connection', 'timeout', 'network', 'dns', 'resolve'
        ]):
            return ErrorCategory.NETWORK
        
        # Authentication errors
        if any(keyword in error_str for keyword in [
            'unauthorized', 'forbidden', 'authentication', 'api key'
        ]):
            return ErrorCategory.PERMISSION
        
        # Rate limiting
        if any(keyword in error_str for keyword in [
            'rate limit', 'too many requests', '429'
        ]):
            return ErrorCategory.RESOURCE
        
        # Validation errors
        if any(keyword in error_str for keyword in [
            'invalid', 'malformed', 'validation', 'schema'
        ]):
            return ErrorCategory.VALIDATION
        
        # Resource errors
        if any(keyword in error_str for keyword in [
            'disk', 'space', 'memory', 'resource', 'quota'
        ]):
            return ErrorCategory.RESOURCE
        
        return ErrorCategory.UNKNOWN

@recoverable(classifier=ModelDownloadErrorClassifier())
async def download_model_with_custom_classifier(url: str, destination: str):
    """Download model with custom error classification"""
    # Download implementation
    pass
```

### 4. Circuit Breaker Integration

Protect against cascading failures:

```python
@recoverable(
    max_retries=5,
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=60.0,
    circuit_breaker_scope="model_downloads"
)
async def download_model_with_circuit_breaker(url: str, destination: str):
    """Download model with circuit breaker protection"""
    # Download implementation
    pass
```

### 5. Async Operation Integration

For complex async operations with multiple steps:

```python
@recoverable(max_retries=3, persistence=SQLitePersistence())
async def install_project_with_dependencies(project_config: dict):
    """Install project with all dependencies"""
    operation_id = generate_operation_id()
    
    try:
        # Step 1: Download ComfyUI
        comfyui_path = await download_comfyui(project_config['comfyui_version'])
        
        # Step 2: Install custom nodes
        for node in project_config['custom_nodes']:
            await install_custom_node(node, comfyui_path)
        
        # Step 3: Download required models
        for model in project_config['required_models']:
            await download_model(model['url'], model['destination'])
        
        # Step 4: Validate installation
        await validate_installation(comfyui_path)
        
        return {
            'success': True,
            'path': comfyui_path,
            'project_id': project_config['id']
        }
        
    except Exception as e:
        logger.error(f"Project installation failed: {e}")
        raise
```

## Integration with Existing Systems

### 1. Celery Task Integration

```python
from celery import Task
from backend.src.recovery import recoverable

class RecoverableTask(Task):
    """Base class for recoverable Celery tasks"""
    
    @classmethod
    def apply_recovery(cls, task_func):
        """Apply recovery decorator to task function"""
        return recoverable(
            max_retries=3,
            persistence=SQLitePersistence(),
            circuit_breaker_threshold=5
        )(task_func)

@ RecoverableTask.apply_recovery
def process_model_download(model_info: dict):
    """Process model download with recovery"""
    # Implementation
    pass
```

### 2. WebSocket Integration

```python
@recoverable(max_retries=3)
async def operation_with_websocket_updates(data: dict, socket):
    """Operation with real-time WebSocket updates"""
    operation_id = generate_operation_id()
    
    try:
        # Emit start event
        await socket.emit('operation_started', {
            'operation_id': operation_id,
            'data': data
        })
        
        # Process operation
        result = await process_data(data)
        
        # Emit success event
        await socket.emit('operation_completed', {
            'operation_id': operation_id,
            'result': result,
            'success': True
        })
        
        return result
        
    except Exception as e:
        # Emit error event
        await socket.emit('operation_error', {
            'operation_id': operation_id,
            'error': str(e),
            'retrying': True
        })
        raise
```

### 3. Database Transaction Integration

```python
@recoverable(max_retries=3)
async def database_operation_with_recovery(session, data: dict):
    """Database operation with transaction recovery"""
    try:
        # Start transaction
        async with session.begin():
            # Perform database operations
            record = await create_record(session, data)
            
            # Related operations
            await update_related_records(session, record.id)
            
            return record
            
    except Exception as e:
        # Rollback will happen automatically
        logger.error(f"Database operation failed: {e}")
        raise
```

## Configuration Integration

### 1. Environment-Based Configuration

```python
import os
from backend.src.recovery import recoverable, SQLitePersistence

# Configure based on environment
def get_recovery_config():
    """Get recovery configuration from environment"""
    return {
        'max_retries': int(os.getenv('RECOVERY_MAX_RETRIES', '3')),
        'initial_delay': float(os.getenv('RECOVERY_INITIAL_DELAY', '1.0')),
        'backoff_factor': float(os.getenv('RECOVERY_BACKOFF_FACTOR', '2.0')),
        'max_delay': float(os.getenv('RECOVERY_MAX_DELAY', '60.0')),
        'persistence': SQLitePersistence() if os.getenv('RECOVERY_PERSISTENCE_ENABLED', 'true').lower() == 'true' else None,
        'circuit_breaker_threshold': int(os.getenv('RECOVERY_CIRCUIT_BREAKER_THRESHOLD', '5'))
    }

@recoverable(**get_recovery_config())
async def configured_operation(data: dict):
    """Operation with environment-based recovery configuration"""
    # Implementation
    pass
```

### 2. Dynamic Configuration Updates

```python
from backend.src.recovery.integration import get_recovery_integrator

def update_recovery_config(new_config: dict):
    """Update recovery configuration dynamically"""
    integrator = get_recovery_integrator()
    integrator.update_config(new_config)

# Usage during runtime
update_recovery_config({
    'max_retries': 5,
    'initial_delay': 2.0,
    'circuit_breaker_threshold': 10
})
```

## Testing Integration

### 1. Unit Testing Recovery Operations

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.src.recovery import recoverable

@pytest.mark.asyncio
async def test_recoverable_operation_success():
    """Test successful recoverable operation"""
    
    @recoverable(max_retries=3)
    async def test_operation():
        return "success"
    
    result = await test_operation()
    assert result == "success"

@pytest.mark.asyncio
async def test_recoverable_operation_with_retry():
    """Test operation that succeeds after retry"""
    
    call_count = 0
    
    @recoverable(max_retries=3)
    async def failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Network error")
        return "success_after_retry"
    
    result = await failing_operation()
    assert result == "success_after_retry"
    assert call_count == 3
```

### 2. Integration Testing

```python
@pytest.mark.asyncio
async def test_full_recovery_cycle():
    """Test complete recovery cycle with persistence"""
    
    operation_id = "test_operation_123"
    
    @recoverable(
        max_retries=3,
        persistence=SQLitePersistence(":memory:")
    )
    async def persistent_operation(data: dict):
        if data.get('simulate_failure'):
            raise ConnectionError("Simulated failure")
        return {"processed": True, "data": data}
    
    # Test with failure
    with pytest.raises(ConnectionError):
        await persistent_operation({"simulate_failure": True, "id": operation_id})
    
    # Test retry succeeds
    result = await persistent_operation({"id": operation_id})
    assert result["processed"] is True
```

### 3. Performance Testing

```python
import time
import asyncio
from backend.src.recovery import recoverable

@pytest.mark.asyncio
async def test_recovery_performance():
    """Benchmark recovery system performance"""
    
    @recoverable(max_retries=3)
    async def benchmark_operation():
        await asyncio.sleep(0.1)  # Simulate work
        return "completed"
    
    # Measure baseline performance
    start_time = time.time()
    for _ in range(100):
        await benchmark_operation()
    baseline_time = time.time() - start_time
    
    # Measure with recovery overhead
    @recoverable(max_retries=3, persistence=SQLitePersistence(":memory:"))
    async def benchmark_with_recovery():
        await asyncio.sleep(0.1)
        return "completed"
    
    start_time = time.time()
    for _ in range(100):
        await benchmark_with_recovery()
    recovery_time = time.time() - start_time
    
    # Calculate overhead
    overhead_percent = ((recovery_time - baseline_time) / baseline_time) * 100
    assert overhead_percent < 10  # Less than 10% overhead
```

## Best Practices

### 1. Idempotent Operations

Ensure operations are safe to retry:

```python
@recoverable(max_retries=3)
async def create_resource_safely(resource_data: dict):
    """Create resource with idempotency checks"""
    resource_id = generate_resource_id(resource_data)
    
    # Check if resource already exists
    existing = await get_resource(resource_id)
    if existing:
        return existing
    
    # Create new resource
    return await create_resource(resource_id, resource_data)
```

### 2. State Management

Manage state carefully during recovery:

```python
@recoverable(max_retries=3, persistence=SQLitePersistence())
async def process_file_with_state(file_path: str):
    """Process file with proper state management"""
    # Check if already processed
    state = await load_processing_state(file_path)
    if state and state.get('completed'):
        return state['result']
    
    # Process file
    result = await process_file_content(file_path)
    
    # Save state
    await save_processing_state(file_path, {
        'completed': True,
        'result': result,
        'timestamp': datetime.now().isoformat()
    })
    
    return result
```

### 3. Error Handling

Implement comprehensive error handling:

```python
@recoverable(max_retries=3)
async def robust_operation(data: dict):
    """Operation with comprehensive error handling"""
    try:
        # Validate input
        if not data.get('required_field'):
            raise ValueError("Missing required field")
        
        # Process data
        result = await process_data(data)
        
        # Validate result
        if not result.get('success'):
            raise ProcessingError("Operation failed")
        
        return result
        
    except ValueError as e:
        # Don't retry validation errors
        logger.error(f"Validation error: {e}")
        raise
        
    except ProcessingError as e:
        # Retry processing errors
        logger.warning(f"Processing error, will retry: {e}")
        raise
        
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error: {e}")
        raise
```

### 4. Monitoring and Logging

Implement proper monitoring:

```python
@recoverable(max_retries=3)
async def monitored_operation(data: dict):
    """Operation with comprehensive monitoring"""
    operation_id = generate_operation_id()
    start_time = time.time()
    
    try:
        # Log operation start
        logger.info(f"Starting operation {operation_id}", extra={
            'operation_id': operation_id,
            'data_size': len(str(data))
        })
        
        # Process operation
        result = await process_data(data)
        
        # Log success
        duration = time.time() - start_time
        logger.info(f"Operation {operation_id} completed", extra={
            'operation_id': operation_id,
            'duration': duration,
            'success': True
        })
        
        return result
        
    except Exception as e:
        # Log failure
        duration = time.time() - start_time
        logger.error(f"Operation {operation_id} failed", extra={
            'operation_id': operation_id,
            'duration': duration,
            'error': str(e),
            'success': False
        })
        raise
```

## Performance Considerations

### 1. Persistence Overhead

- **SQLite**: Minimal overhead (~1-2ms per operation)
- **Memory**: Zero overhead but lost on restart
- **Caching**: Cache frequently accessed recovery data

### 2. Memory Usage

- **State Serialization**: Use efficient serialization formats
- **Cleanup**: Implement automatic cleanup of old recovery data
- **Concurrent Operations**: Monitor memory usage during high concurrency

### 3. Network Impact

- **Retry Delays**: Configure appropriate backoff strategies
- **Circuit Breakers**: Prevent network storms during outages
- **Bandwidth**: Consider bandwidth limitations for large downloads

## Migration Guide

### 1. Existing Functions

```python
# Before
async def download_model(url: str, destination: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            with open(destination, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
    return destination

# After
@recoverable(max_retries=3)
async def download_model(url: str, destination: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            with open(destination, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
    return destination
```

### 2. Gradual Rollout

```python
# Enable recovery gradually
RECOVERY_ENABLED = os.getenv('RECOVERY_ENABLED', 'false').lower() == 'true'

def apply_recovery(func):
    """Apply recovery conditionally"""
    if RECOVERY_ENABLED:
        return recoverable(max_retries=3)(func)
    return func

@apply_recovery
async def download_model(url: str, destination: str):
    # Implementation
    pass
```

## Conclusion

The ComfyUI Launcher Recovery System provides a comprehensive, extensible framework for adding robust recovery capabilities to any operation. By following the integration patterns and best practices outlined in this document, developers can ensure their operations are resilient to failures while maintaining good performance and user experience.

The system's modular design allows for customization at every level, from retry strategies to error classification, making it suitable for a wide variety of use cases and operational requirements.