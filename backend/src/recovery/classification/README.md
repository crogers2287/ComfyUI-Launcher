# Error Classification System

The error classification system provides intelligent error handling for the recovery decorator by automatically classifying exceptions and selecting appropriate retry strategies.

## Overview

The classification system consists of:

1. **Error Patterns** - Predefined patterns for matching and categorizing errors
2. **Error Classifier** - Main engine that matches errors to patterns
3. **Strategy Mapper** - Maps error classifications to recovery strategies
4. **Integration** - Seamless integration with the `@recoverable` decorator

## Error Categories

The system recognizes the following error categories:

### Network Errors
- `NETWORK_TIMEOUT` - Connection timeouts
- `NETWORK_CONNECTION` - Connection refused, reset, broken pipe
- `NETWORK_DNS` - DNS resolution failures
- `NETWORK_SSL` - SSL certificate errors

### Resource Errors
- `RESOURCE_DISK` - Disk space issues
- `RESOURCE_MEMORY` - Memory allocation failures
- `RESOURCE_CPU` - CPU resource constraints
- `RESOURCE_QUOTA` - Rate limiting and quotas

### Permission Errors
- `PERMISSION_FILE` - File access denied
- `PERMISSION_API` - API authorization failures
- `PERMISSION_AUTH` - Authentication errors

### Validation Errors
- `VALIDATION_SCHEMA` - Schema validation failures
- `VALIDATION_DATA` - Data format errors
- `VALIDATION_FORMAT` - Parsing errors

### Service Errors
- `SERVICE_UNAVAILABLE` - 503 errors
- `SERVICE_RATE_LIMIT` - Rate limiting (429)
- `SERVICE_MAINTENANCE` - Scheduled maintenance

### System Errors
- `SYSTEM_DEPENDENCY` - Missing dependencies
- `SYSTEM_CONFIGURATION` - Configuration errors
- `SYSTEM_CORRUPTION` - Data corruption

## Usage

### Basic Usage with Decorator

```python
from backend.src.recovery import recoverable

@recoverable()
async def download_file(url: str) -> bytes:
    # Automatically retries network errors
    # Does not retry permission errors
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
```

### Custom Classifier

```python
from backend.src.recovery import recoverable
from backend.src.recovery.classification import ErrorClassifier, ErrorPattern

# Define custom patterns
custom_pattern = ErrorPattern(
    category=ErrorCategory.SERVICE_RATE_LIMIT,
    indicators=["rate limit", "too many requests"],
    exception_types=[RuntimeError],
    error_codes=["429"],
    severity=ErrorSeverity.MEDIUM,
    recoverability=RecoverabilityScore.ALWAYS,
    context_keys=[]
)

# Create classifier with custom patterns
classifier = ErrorClassifier(custom_patterns=[custom_pattern])

@recoverable(classifier=classifier)
async def api_call(endpoint: str) -> dict:
    # Will recognize and retry custom rate limit errors
    ...
```

### Manual Classification

```python
from backend.src.recovery.classification import ErrorClassifier

classifier = ErrorClassifier()

try:
    risky_operation()
except Exception as e:
    classification = classifier.classify(e)
    
    if classification.is_recoverable:
        print(f"Error is recoverable: {classification.category.value}")
        strategy, config = classifier.get_recovery_strategy(classification)
        # Use strategy to determine retry approach
    else:
        print(f"Error is not recoverable: {classification.category.value}")
```

## Classification Process

1. **Pattern Matching** - Error is matched against predefined patterns
2. **Scoring** - Each pattern calculates a match score based on:
   - Exception type
   - Error message indicators
   - Error codes
   - Context keys
3. **Classification** - Highest scoring pattern determines classification
4. **Strategy Selection** - Classification maps to recovery strategy

## Recovery Strategies

The system automatically selects recovery strategies based on error classification:

- **Exponential Backoff** - For transient network/service errors
- **Linear Backoff** - For predictable recovery times
- **Fixed Delay** - For rate limiting scenarios
- **No Retry** - For permanent errors (permissions, validation)

## Extending the System

### Adding Custom Patterns

```python
from backend.src.recovery.classification import ErrorPattern

custom_pattern = ErrorPattern(
    category=ErrorCategory.SERVICE_UNAVAILABLE,
    indicators=["maintenance mode", "scheduled downtime"],
    exception_types=[ServiceUnavailableError],
    error_codes=["503", "MAINTENANCE"],
    severity=ErrorSeverity.LOW,
    recoverability=RecoverabilityScore.ALWAYS,
    context_keys=["maintenance_end_time"]
)

classifier.add_pattern(custom_pattern)
```

### Custom Strategy Mapping

```python
from backend.src.recovery.classification import StrategyMapper, StrategyConfig

custom_strategies = {
    ErrorCategory.SERVICE_MAINTENANCE: StrategyConfig(
        approach=RecoveryApproach.FIXED,
        max_retries=100,
        initial_delay=300.0,  # 5 minutes
        max_delay=300.0
    )
}

mapper = StrategyMapper(custom_strategies=custom_strategies)
```

## Best Practices

1. **Provide Context** - Include relevant context when errors might occur
2. **Use Specific Exceptions** - Throw specific exception types for better classification
3. **Include Error Codes** - Add error codes to exceptions when available
4. **Monitor Statistics** - Use `classifier.get_statistics()` to understand error patterns
5. **Test Classifications** - Verify custom patterns match intended errors