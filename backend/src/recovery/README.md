# Recovery System Documentation

The recovery system provides automatic retry and recovery capabilities for critical operations in ComfyUI Launcher.

## Quick Start

```python
from backend.src.recovery import recoverable

@recoverable(max_retries=3)
def download_model(url: str):
    # Your download logic here
    pass
```

## Features

- **Automatic Retries**: Configurable retry logic with exponential backoff
- **State Persistence**: Save and resume operations across process restarts
- **Circuit Breaker**: Prevent cascading failures
- **Flexible Strategies**: Built-in and custom retry strategies
- **Error Classification**: Smart retry decisions based on error types
- **Async Support**: Works with both sync and async functions

## Basic Usage

### Simple Retry

```python
from backend.src.recovery import recoverable

@recoverable(max_retries=3, initial_delay=1.0)
def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

### With State Persistence

```python
from backend.src.recovery import recoverable
from backend.src.recovery.persistence import SQLitePersistence

persistence = SQLitePersistence()

@recoverable(max_retries=5, persistence=persistence)
async def long_running_operation(data):
    # Operation that can be resumed if interrupted
    result = await process_data(data)
    return result
```

### Custom Strategy

```python
from backend.src.recovery import recoverable
from backend.src.recovery.strategies import ExponentialBackoffStrategy

strategy = ExponentialBackoffStrategy(
    initial_delay=0.5,
    backoff_factor=3.0,
    max_delay=30.0,
    jitter=True
)

@recoverable(strategy=strategy)
def api_call(endpoint):
    return make_request(endpoint)
```

## Error Classification

The system automatically classifies errors and makes smart retry decisions:

- **Network Errors**: Connection issues, timeouts - will retry
- **Permission Errors**: 401/403 errors - won't retry
- **Validation Errors**: Schema/format errors - won't retry
- **Resource Errors**: Memory/disk issues - will retry
- **Timeout Errors**: Operation timeouts - will retry

## Persistence Backends

### Memory Persistence
Good for testing and single-session recovery:

```python
from backend.src.recovery.persistence import MemoryPersistence

persistence = MemoryPersistence()
```

### SQLite Persistence
Survives process restarts:

```python
from backend.src.recovery.persistence import SQLitePersistence

# Uses default location: ~/.comfyui-launcher/data/recovery.db
persistence = SQLitePersistence()

# Or specify custom path
persistence = SQLitePersistence("/path/to/recovery.db")
```

## Recovery Strategies

### Built-in Strategies

1. **ExponentialBackoffStrategy**: Delay doubles each attempt
2. **LinearBackoffStrategy**: Delay increases linearly
3. **FixedDelayStrategy**: Same delay between attempts
4. **CustomStrategy**: Define your own logic

### Creating Custom Strategies

```python
from backend.src.recovery.strategies import CustomStrategy

def fibonacci_delay(attempt):
    if attempt <= 1:
        return 1.0
    return fibonacci_delay(attempt-1) + fibonacci_delay(attempt-2)

strategy = CustomStrategy(
    delay_func=fibonacci_delay,
    name="Fibonacci"
)
```

## Circuit Breaker

Prevents cascading failures by stopping retries after threshold:

```python
@recoverable(
    circuit_breaker_threshold=5,  # Open after 5 failures
    circuit_breaker_timeout=300.0  # Reopen after 5 minutes
)
def protected_operation():
    pass
```

## Integration Examples

### With Progress Tracking

```python
@recoverable(max_retries=3)
async def download_with_progress(url, progress_tracker):
    # Recovery will preserve progress tracker state
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            async for chunk in response.content.iter_chunked(8192):
                downloaded += len(chunk)
                progress_tracker.update(downloaded, total_size)
                # Write chunk to file
```

### With Celery Tasks

```python
from celery import Task

class RecoverableTask(Task):
    @recoverable(max_retries=3, persistence=SQLitePersistence())
    def run(self, *args, **kwargs):
        return self._run(*args, **kwargs)
```

### With WebSocket Notifications

```python
@recoverable(max_retries=3)
async def operation_with_notifications(data, socket):
    try:
        result = await process_data(data)
        await socket.emit('success', {'result': result})
        return result
    except Exception as e:
        await socket.emit('retry', {'error': str(e)})
        raise
```

## Best Practices

1. **Choose appropriate retry counts**: Network operations might need more retries than local operations
2. **Set reasonable delays**: Balance between quick recovery and not overwhelming services
3. **Use persistence for long operations**: Especially important for downloads or multi-step processes
4. **Monitor circuit breakers**: Log when circuits open to identify systemic issues
5. **Test recovery paths**: Ensure your operations are truly idempotent

## Error Handling

```python
from backend.src.recovery import (
    recoverable,
    RecoveryExhaustedError,
    CircuitBreakerOpenError
)

try:
    result = recoverable_operation()
except RecoveryExhaustedError as e:
    # All retries failed
    logger.error(f"Operation failed after {e.attempts} attempts")
    logger.error(f"Original error: {e.original_error}")
except CircuitBreakerOpenError as e:
    # Circuit breaker is preventing execution
    logger.warning(f"Circuit breaker open, retry in {e.timeout_remaining}s")
```

## Configuration Reference

### Decorator Parameters

- `max_retries`: Maximum retry attempts (default: 3)
- `initial_delay`: First retry delay in seconds (default: 1.0)
- `backoff_factor`: Multiply delay by this each retry (default: 2.0)
- `max_delay`: Maximum delay between retries (default: 60.0)
- `timeout`: Timeout for each attempt (default: None)
- `persistence`: State persistence implementation (default: None)
- `strategy`: Custom recovery strategy (default: None)
- `circuit_breaker_threshold`: Failures before circuit opens (default: 5)
- `circuit_breaker_timeout`: Seconds before circuit closes (default: 300.0)