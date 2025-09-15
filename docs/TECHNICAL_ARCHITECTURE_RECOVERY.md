# Recovery System Technical Architecture

## Overview

The ComfyUI Launcher Recovery System is a comprehensive, multi-layered architecture designed to provide robust automatic recovery capabilities for critical operations. This document details the technical implementation, architecture patterns, and integration points of the recovery system.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  Recovery Integration Layer                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Download Manager│  │ Project Manager │  │ Installation    │ │
│  │ Recovery        │  │ Recovery        │  │ Recovery        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Recovery Core Layer                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Recovery        │  │ Error           │  │ State           │ │
│  │ Decorator       │  │ Classification  │  │ Persistence     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Retry           │  │ Circuit         │  │ Recovery        │ │
│  │ Strategies      │  │ Breaker         │  │ Data Models     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Persistence Layer                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ SQLite          │  │ Memory          │  │ SQLAlchemy      │ │
│  │ Persistence     │  │ Persistence     │  │ Models          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Recovery Decorator (`recovery/decorator.py`)

The `@recoverable` decorator is the primary interface for adding recovery capabilities to functions:

```python
@recoverable(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    max_delay=60.0,
    persistence=SQLitePersistence(),
    strategy=ExponentialBackoffStrategy(),
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=300.0
)
async def critical_operation(*args, **kwargs):
    # Operation logic
    return result
```

**Key Features:**
- Automatic retry logic with configurable strategies
- State persistence across process restarts
- Circuit breaker pattern for failure isolation
- Async/sync function support
- Comprehensive error handling

#### 2. Error Classification (`recovery/classification/`)

Intelligent error classification determines retry appropriateness:

```python
class ErrorClassifier:
    def classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error and determine if retry is appropriate"""
        
    def should_retry(self, error: Exception) -> bool:
        """Return True if error warrants retry"""
```

**Error Categories:**
- **Network Errors**: Connection issues, timeouts, DNS failures
- **Timeout Errors**: Operation timeouts, response timeouts
- **Validation Errors**: Schema errors, malformed data
- **Permission Errors**: Authentication, authorization failures
- **Resource Errors**: Memory, disk space, file system issues
- **Unknown Errors**: Unclassified errors

#### 3. Retry Strategies (`recovery/strategies/`)

Pluggable retry strategies for different use cases:

```python
# Exponential Backoff (Default)
strategy = ExponentialBackoffStrategy(
    initial_delay=1.0,
    backoff_factor=2.0,
    max_delay=60.0,
    jitter=True
)

# Linear Backoff
strategy = LinearBackoffStrategy(
    initial_delay=1.0,
    increment=5.0,
    max_delay=60.0
)

# Fixed Delay
strategy = FixedDelayStrategy(delay=5.0)

# Custom Strategy
strategy = CustomStrategy(
    delay_func=lambda attempt: fibonacci(attempt),
    name="Fibonacci"
)
```

#### 4. State Persistence (`recovery/persistence/`)

Multiple persistence backends for recovery state:

```python
# SQLite Persistence (Production)
persistence = SQLitePersistence("/path/to/recovery.db")

# Memory Persistence (Testing)
persistence = MemoryPersistence()

# Custom Persistence
class CustomPersistence(StatePersistence):
    async def save(self, recovery_data: RecoveryData):
        # Custom persistence logic
```

**Persistence Schema:**
```sql
CREATE TABLE recovery_data (
    operation_id TEXT PRIMARY KEY,
    function_name TEXT NOT NULL,
    state TEXT NOT NULL,
    attempt INTEGER DEFAULT 0,
    args BLOB,
    kwargs BLOB,
    error TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. Circuit Breaker Pattern

Prevents cascading failures during systemic issues:

```python
class CircuitBreaker:
    def __init__(self, threshold: int = 5, timeout: float = 300.0):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
```

**States:**
- **CLOSED**: Normal operation, failures counted
- **OPEN**: Circuit tripped, operations blocked
- **HALF_OPEN**: Testing if system has recovered

### Data Models

#### RecoveryData
```python
@dataclass
class RecoveryData:
    operation_id: str
    function_name: str
    args: tuple
    kwargs: dict
    state: RecoveryState
    attempt: int
    error: Optional[Exception]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

#### RecoveryState
```python
class RecoveryState(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RECOVERING = "recovering"
    SUCCESS = "success"
    FAILED = "failed"
    EXHAUSTED = "exhausted"
```

### Integration Patterns

#### 1. Function Decoration
```python
# Simple retry
@recoverable(max_retries=3)
def download_file(url: str, destination: str):
    # Download logic
    pass

# With state persistence
@recoverable(persistence=SQLitePersistence())
async def install_project(project_id: str):
    # Installation logic
    pass
```

#### 2. Integration Layer
```python
class RecoveryIntegrator:
    def __init__(self, config: RecoveryConfig):
        self.config = config
        self.persistence = SQLitePersistence()
        self.strategy = ExponentialBackoffStrategy()
        self.classifier = ErrorClassifier()
    
    def apply_to_operation(self, operation_func):
        """Apply recovery to an existing operation"""
        return recoverable(
            max_retries=self.config.max_retries,
            persistence=self.persistence,
            strategy=self.strategy,
            classifier=self.classifier
        )(operation_func)
```

#### 3. WebSocket Integration
```python
# Real-time recovery updates
async def emit_recovery_update(operation_id: str, state: RecoveryState):
    await socket.emit('recovery_update', {
        'operation_id': operation_id,
        'state': state.value,
        'timestamp': datetime.now().isoformat()
    })
```

### Performance Considerations

#### 1. Persistence Overhead
- **SQLite**: Minimal overhead, suitable for production
- **Memory**: Zero overhead, lost on restart
- **Caching**: In-memory caching for frequently accessed data

#### 2. Memory Management
- **State Serialization**: Efficient serialization of operation state
- **Cleanup**: Automatic cleanup of old recovery data
- **Garbage Collection**: Periodic cleanup of completed operations

#### 3. Concurrency Control
- **Operation Isolation**: Each operation has independent recovery state
- **Lock Management**: Minimal locking for critical sections
- **Async Support**: Native async/await support

### Error Handling Patterns

#### 1. Retry Decisions
```python
def should_retry(error: Exception, attempt: int, max_attempts: int) -> bool:
    # Check if error is retryable
    if not is_retryable_error(error):
        return False
    
    # Check if attempts exhausted
    if attempt >= max_attempts:
        return False
    
    # Check circuit breaker state
    if circuit_breaker.is_open():
        return False
    
    return True
```

#### 2. Error Classification
```python
class ErrorClassifier:
    def classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error based on type and message"""
        if isinstance(error, ConnectionError):
            return ErrorCategory.NETWORK
        elif isinstance(error, TimeoutError):
            return ErrorCategory.TIMEOUT
        elif isinstance(error, ValidationError):
            return ErrorCategory.VALIDATION
        elif isinstance(error, PermissionError):
            return ErrorCategory.PERMISSION
        else:
            return ErrorClassifier._classify_by_message(str(error))
```

### Configuration Management

#### 1. Default Configuration
```python
DEFAULT_CONFIG = RecoveryConfig(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    max_delay=60.0,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=300.0,
    persistence_enabled=True
)
```

#### 2. Environment Variables
```bash
RECOVERY_MAX_RETRIES=5
RECOVERY_INITIAL_DELAY=2.0
RECOVERY_BACKOFF_FACTOR=2.5
RECOVERY_CIRCUIT_BREAKER_THRESHOLD=10
RECOVERY_PERSISTENCE_PATH=/var/lib/comfyui/recovery.db
```

#### 3. Runtime Configuration
```python
# Update configuration at runtime
integrator = get_recovery_integrator()
integrator.update_config(RecoveryConfig(
    max_retries=5,
    initial_delay=2.0
))
```

### Monitoring and Observability

#### 1. Metrics Collection
```python
class RecoveryMetrics:
    def __init__(self):
        self.total_operations = Counter()
        self.recovered_operations = Counter()
        self.failed_operations = Counter()
        self.retry_attempts = Counter()
        self.circuit_breaker_trips = Counter()
```

#### 2. Logging Strategy
```python
# Structured logging for recovery operations
logger.info(
    "Recovery operation started",
    extra={
        'operation_id': operation_id,
        'function_name': function_name,
        'attempt': attempt,
        'max_attempts': max_attempts
    }
)
```

#### 3. Health Checks
```python
async def health_check():
    """Comprehensive health check for recovery system"""
    return {
        'persistence_healthy': await check_persistence(),
        'circuit_breakers': get_circuit_breaker_status(),
        'active_operations': len(await list_active_operations()),
        'system_healthy': True
    }
```

### Testing Architecture

#### 1. Unit Tests
```python
async def test_retry_strategy():
    strategy = ExponentialBackoffStrategy()
    delay = strategy.calculate_delay(attempt=2)
    assert delay == 2.0  # initial_delay * backoff_factor^1
```

#### 2. Integration Tests
```python
async def test_full_recovery_cycle():
    """Test complete recovery cycle with persistence"""
    operation_id = await start_operation_with_failure()
    await wait_for_recovery()
    assert await operation_succeeded(operation_id)
```

#### 3. Performance Tests
```python
async def test_recovery_performance():
    """Benchmark recovery system performance"""
    results = await run_recovery_benchmark()
    assert results['average_recovery_time'] < 5.0
    assert results['success_rate'] > 0.95
```

### Security Considerations

#### 1. Data Protection
- **Sensitive Data**: Never persist sensitive information in recovery state
- **Encryption**: Optional encryption for persisted data
- **Access Control**: Restrict access to recovery data stores

#### 2. Operation Safety
- **Idempotency**: Ensure operations are safe to retry
- **State Validation**: Validate recovery state before use
- **Resource Limits**: Prevent resource exhaustion

### Future Extensions

#### 1. Distributed Recovery
- **Cluster Support**: Recovery across multiple server instances
- **Shared State**: Distributed state management
- **Coordination**: Leader election for recovery coordination

#### 2. Advanced Strategies
- **Machine Learning**: Adaptive retry strategies based on historical data
- **Predictive Recovery**: Anticipate failures before they occur
- **Context-Aware Recovery**: Operation-specific recovery strategies

This architecture provides a robust, scalable foundation for recovery operations in the ComfyUI Launcher, ensuring reliable operation even in challenging network and system conditions.