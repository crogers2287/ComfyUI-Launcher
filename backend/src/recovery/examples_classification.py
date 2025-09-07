"""Examples of using the error classification system."""
import asyncio
import logging
from typing import Dict, Any

from .decorator import recoverable
from .classification import ErrorClassifier, ErrorPattern, ErrorCategory
from .classification.categories import ErrorSeverity, RecoverabilityScore
from .persistence import MemoryPersistence

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_classification():
    """Example of basic error classification with decorator."""
    
    @recoverable(
        max_retries=5,
        initial_delay=1.0
    )
    async def download_file(url: str) -> bytes:
        """Download file with automatic error classification."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 429:
                    raise RuntimeError(f"Rate limit exceeded: {response.headers.get('Retry-After')}")
                elif response.status >= 500:
                    raise RuntimeError(f"Server error: {response.status}")
                elif response.status == 404:
                    raise FileNotFoundError(f"File not found: {url}")
                
                response.raise_for_status()
                return await response.read()
    
    try:
        # This will automatically retry network errors but not 404s
        data = await download_file("https://example.com/file.zip")
        logger.info(f"Downloaded {len(data)} bytes")
    except Exception as e:
        logger.error(f"Download failed: {e}")


async def example_custom_classifier():
    """Example of using a custom error classifier."""
    
    # Define custom patterns for your application
    custom_patterns = [
        ErrorPattern(
            category=ErrorCategory.SERVICE_RATE_LIMIT,
            indicators=["quota exceeded", "daily limit"],
            exception_types=[RuntimeError],
            error_codes=["QUOTA_EXCEEDED"],
            severity=ErrorSeverity.MEDIUM,
            recoverability=RecoverabilityScore.ALWAYS,
            context_keys=["quota_reset_time"]
        ),
        ErrorPattern(
            category=ErrorCategory.VALIDATION_DATA,
            indicators=["invalid workflow", "missing nodes"],
            exception_types=[ValueError],
            error_codes=["INVALID_WORKFLOW"],
            severity=ErrorSeverity.HIGH,
            recoverability=RecoverabilityScore.NEVER,
            context_keys=["workflow_errors"]
        ),
    ]
    
    # Create classifier with custom patterns
    classifier = ErrorClassifier(custom_patterns=custom_patterns)
    
    @recoverable(
        classifier=classifier,
        persistence=MemoryPersistence()
    )
    async def process_workflow(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process workflow with custom error handling."""
        if not workflow_data.get("nodes"):
            raise ValueError("Invalid workflow: missing nodes")
        
        if workflow_data.get("size", 0) > 1000:
            raise RuntimeError("Quota exceeded: daily limit reached")
        
        # Process workflow...
        return {"status": "processed", "id": workflow_data.get("id")}
    
    # Test with invalid workflow - won't retry
    try:
        await process_workflow({"id": "123"})
    except Exception as e:
        logger.error(f"Workflow processing failed (no retry): {e}")
    
    # Test with quota error - will retry
    try:
        await process_workflow({"id": "456", "nodes": ["a", "b"], "size": 2000})
    except Exception as e:
        logger.error(f"Workflow processing failed (after retries): {e}")


async def example_manual_classification():
    """Example of manual error classification."""
    classifier = ErrorClassifier()
    
    # Simulate various errors and classify them
    errors = [
        ConnectionError("Connection refused"),
        PermissionError("Access denied: /etc/sensitive"),
        TimeoutError("Operation timed out after 30s"),
        ValueError("Invalid JSON format"),
        MemoryError("Cannot allocate 4GB"),
        RuntimeError("Service temporarily unavailable"),
    ]
    
    for error in errors:
        # Classify the error
        classification = classifier.classify(error, context={"source": "example"})
        
        # Get recovery strategy
        strategy, config = classifier.get_recovery_strategy(classification)
        
        logger.info(f"\nError: {error}")
        logger.info(f"  Category: {classification.category.value}")
        logger.info(f"  Severity: {classification.severity.value}")
        logger.info(f"  Recoverable: {classification.is_recoverable}")
        logger.info(f"  Transient: {classification.is_transient}")
        logger.info(f"  Confidence: {classification.confidence:.2f}")
        logger.info(f"  Strategy: {config.approach.value}")
        logger.info(f"  Max retries: {config.max_retries}")


async def example_classification_with_context():
    """Example of classification with additional context."""
    classifier = ErrorClassifier()
    
    @recoverable(
        classifier=classifier,
        max_retries=10
    )
    async def api_call_with_context(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """API call that provides context for better classification."""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=data) as response:
                    if response.status == 503:
                        # Provide context for better classification
                        retry_after = response.headers.get('Retry-After')
                        maintenance_end = response.headers.get('X-Maintenance-End')
                        
                        error = RuntimeError(f"Service unavailable: {response.status}")
                        # Context will be passed to classifier
                        error.context = {
                            'retry_after': retry_after,
                            'maintenance_end': maintenance_end,
                            'endpoint': endpoint
                        }
                        raise error
                    
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            # Add context if not already present
            if not hasattr(e, 'context'):
                e.context = {}
            e.context.update({
                'endpoint': endpoint,
                'data_size': len(str(data))
            })
            raise
    
    try:
        result = await api_call_with_context(
            "https://api.example.com/process",
            {"job": "analyze", "data": "..."}
        )
        logger.info(f"API call successful: {result}")
    except Exception as e:
        logger.error(f"API call failed: {e}")


async def example_statistics():
    """Example of using classification statistics."""
    classifier = ErrorClassifier()
    persistence = MemoryPersistence()
    
    @recoverable(
        classifier=classifier,
        persistence=persistence,
        max_retries=3
    )
    async def operation_with_varied_errors(operation_type: str):
        """Operation that can fail in different ways."""
        import random
        
        error_types = {
            "network": ConnectionError("Network unreachable"),
            "timeout": TimeoutError("Request timed out"),
            "permission": PermissionError("Access denied"),
            "validation": ValueError("Invalid input"),
            "resource": MemoryError("Out of memory"),
        }
        
        # Randomly fail with different errors
        if random.random() < 0.7:  # 70% failure rate
            error_type = random.choice(list(error_types.keys()))
            raise error_types[error_type]
        
        return f"Success: {operation_type}"
    
    # Run multiple operations
    results = []
    for i in range(20):
        try:
            result = await operation_with_varied_errors(f"op_{i}")
            results.append(("success", result))
        except Exception as e:
            results.append(("failed", str(e)))
    
    # Get classification statistics
    stats = classifier.get_statistics()
    
    logger.info("\nClassification Statistics:")
    logger.info(f"Total classifications: {stats['total_classifications']}")
    logger.info(f"Recovery rate: {stats['recovery_rate']:.2%}")
    logger.info("\nErrors by category:")
    for category, count in stats['by_category'].items():
        logger.info(f"  {category}: {count}")
    logger.info("\nErrors by severity:")
    for severity, count in stats['by_severity'].items():
        logger.info(f"  {severity}: {count}")
    
    # Get persistence statistics
    saved_states = await persistence.get_all()
    logger.info(f"\nTotal recovery states saved: {len(saved_states)}")
    
    success_count = sum(1 for status, _ in results if status == "success")
    logger.info(f"\nOperation results: {success_count}/{len(results)} successful")


if __name__ == "__main__":
    async def main():
        """Run all examples."""
        logger.info("=== Basic Classification Example ===")
        await example_basic_classification()
        
        logger.info("\n=== Custom Classifier Example ===")
        await example_custom_classifier()
        
        logger.info("\n=== Manual Classification Example ===")
        await example_manual_classification()
        
        logger.info("\n=== Classification with Context Example ===")
        await example_classification_with_context()
        
        logger.info("\n=== Statistics Example ===")
        await example_statistics()
    
    asyncio.run(main())