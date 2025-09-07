"""Predefined error patterns for classification."""
import asyncio
import socket
import ssl

from .categories import ErrorCategory, ErrorPattern, ErrorSeverity, RecoverabilityScore

# Network patterns
NETWORK_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        category=ErrorCategory.NETWORK_TIMEOUT,
        indicators=["timeout", "timed out", "read timeout", "connect timeout"],
        exception_types=[TimeoutError, socket.timeout, asyncio.TimeoutError],
        error_codes=["ETIMEDOUT", "408"],
        severity=ErrorSeverity.MEDIUM,
        recoverability=RecoverabilityScore.LIKELY,
        context_keys=[]
    ),
    ErrorPattern(
        category=ErrorCategory.NETWORK_CONNECTION,
        indicators=["connection refused", "connection reset", "broken pipe", "no route to host"],
        exception_types=[
            ConnectionError, ConnectionRefusedError, ConnectionResetError, BrokenPipeError
        ],
        error_codes=["ECONNREFUSED", "ECONNRESET", "EPIPE"],
        severity=ErrorSeverity.MEDIUM,
        recoverability=RecoverabilityScore.LIKELY,
        context_keys=[]
    ),
    ErrorPattern(
        category=ErrorCategory.NETWORK_DNS,
        indicators=["name resolution", "nodename nor servname", "getaddrinfo failed", "dns"],
        exception_types=[socket.gaierror],
        error_codes=["EAI_NONAME", "EAI_NODATA"],
        severity=ErrorSeverity.HIGH,
        recoverability=RecoverabilityScore.POSSIBLE,
        context_keys=[]
    ),
    ErrorPattern(
        category=ErrorCategory.NETWORK_SSL,
        indicators=["ssl", "certificate", "verify failed", "handshake"],
        exception_types=[ssl.SSLError],
        error_codes=["CERTIFICATE_VERIFY_FAILED"],
        severity=ErrorSeverity.HIGH,
        recoverability=RecoverabilityScore.UNLIKELY,
        context_keys=[]
    ),
]

# Resource patterns
RESOURCE_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        category=ErrorCategory.RESOURCE_DISK,
        indicators=["no space left", "disk full", "out of disk", "inode"],
        exception_types=[OSError],
        error_codes=["ENOSPC", "EDQUOT", "28"],
        severity=ErrorSeverity.CRITICAL,
        recoverability=RecoverabilityScore.UNLIKELY,
        context_keys=["disk_usage"]
    ),
    ErrorPattern(
        category=ErrorCategory.RESOURCE_MEMORY,
        indicators=["out of memory", "cannot allocate", "memory error"],
        exception_types=[MemoryError],
        error_codes=["ENOMEM", "12"],
        severity=ErrorSeverity.CRITICAL,
        recoverability=RecoverabilityScore.POSSIBLE,
        context_keys=["memory_usage"]
    ),
    ErrorPattern(
        category=ErrorCategory.RESOURCE_QUOTA,
        indicators=["quota exceeded", "rate limit", "too many requests"],
        exception_types=[],
        error_codes=["429", "509"],
        severity=ErrorSeverity.MEDIUM,
        recoverability=RecoverabilityScore.ALWAYS,
        context_keys=["rate_limit_reset"]
    ),
]

# Permission patterns
PERMISSION_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        category=ErrorCategory.PERMISSION_FILE,
        indicators=["permission denied", "access denied", "operation not permitted"],
        exception_types=[PermissionError],
        error_codes=["EACCES", "EPERM", "13"],
        severity=ErrorSeverity.HIGH,
        recoverability=RecoverabilityScore.NEVER,
        context_keys=["file_path"]
    ),
    ErrorPattern(
        category=ErrorCategory.PERMISSION_API,
        indicators=["403", "forbidden", "unauthorized", "401"],
        exception_types=[],
        error_codes=["403", "401"],
        severity=ErrorSeverity.HIGH,
        recoverability=RecoverabilityScore.UNLIKELY,
        context_keys=["api_endpoint"]
    ),
]

# Validation patterns
VALIDATION_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        category=ErrorCategory.VALIDATION_SCHEMA,
        indicators=["schema", "validation failed", "invalid schema"],
        exception_types=[ValueError, TypeError],
        error_codes=["400"],
        severity=ErrorSeverity.MEDIUM,
        recoverability=RecoverabilityScore.NEVER,
        context_keys=["schema_errors"]
    ),
    ErrorPattern(
        category=ErrorCategory.VALIDATION_DATA,
        indicators=["invalid data", "bad request", "malformed"],
        exception_types=[ValueError],
        error_codes=["400", "422"],
        severity=ErrorSeverity.MEDIUM,
        recoverability=RecoverabilityScore.UNLIKELY,
        context_keys=["validation_errors"]
    ),
    ErrorPattern(
        category=ErrorCategory.VALIDATION_FORMAT,
        indicators=["invalid format", "parsing error", "decode error"],
        exception_types=[ValueError, UnicodeDecodeError],
        error_codes=["400"],
        severity=ErrorSeverity.LOW,
        recoverability=RecoverabilityScore.UNLIKELY,
        context_keys=[]
    ),
]

# Service patterns
SERVICE_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        category=ErrorCategory.SERVICE_UNAVAILABLE,
        indicators=["service unavailable", "503", "temporarily unavailable"],
        exception_types=[],
        error_codes=["503"],
        severity=ErrorSeverity.HIGH,
        recoverability=RecoverabilityScore.ALWAYS,
        context_keys=["retry_after"]
    ),
    ErrorPattern(
        category=ErrorCategory.SERVICE_RATE_LIMIT,
        indicators=["rate limit", "too many requests", "throttled"],
        exception_types=[],
        error_codes=["429"],
        severity=ErrorSeverity.MEDIUM,
        recoverability=RecoverabilityScore.ALWAYS,
        context_keys=["rate_limit_reset", "retry_after"]
    ),
    ErrorPattern(
        category=ErrorCategory.SERVICE_MAINTENANCE,
        indicators=["maintenance", "scheduled downtime"],
        exception_types=[],
        error_codes=["503"],
        severity=ErrorSeverity.LOW,
        recoverability=RecoverabilityScore.ALWAYS,
        context_keys=["maintenance_end"]
    ),
]

# System patterns
SYSTEM_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        category=ErrorCategory.SYSTEM_DEPENDENCY,
        indicators=["module not found", "import error", "no such file or directory"],
        exception_types=[ImportError, ModuleNotFoundError],
        error_codes=["ENOENT"],
        severity=ErrorSeverity.CRITICAL,
        recoverability=RecoverabilityScore.NEVER,
        context_keys=["missing_dependency"]
    ),
    ErrorPattern(
        category=ErrorCategory.SYSTEM_CONFIGURATION,
        indicators=["configuration error", "config", "invalid setting"],
        exception_types=[],
        error_codes=[],
        severity=ErrorSeverity.HIGH,
        recoverability=RecoverabilityScore.NEVER,
        context_keys=["config_key"]
    ),
    ErrorPattern(
        category=ErrorCategory.SYSTEM_CORRUPTION,
        indicators=["corrupt", "checksum", "integrity", "hash mismatch"],
        exception_types=[],
        error_codes=[],
        severity=ErrorSeverity.CRITICAL,
        recoverability=RecoverabilityScore.UNLIKELY,
        context_keys=["expected_hash", "actual_hash"]
    ),
]

# All patterns combined
ALL_PATTERNS: list[ErrorPattern] = (
    NETWORK_PATTERNS +
    RESOURCE_PATTERNS +
    PERMISSION_PATTERNS +
    VALIDATION_PATTERNS +
    SERVICE_PATTERNS +
    SYSTEM_PATTERNS
)


def get_patterns_for_category(category: ErrorCategory) -> list[ErrorPattern]:
    """Get all patterns for a specific category."""
    return [p for p in ALL_PATTERNS if p.category == category]


def get_custom_patterns() -> list[ErrorPattern]:
    """Get custom patterns (to be extended by users)."""
    # This can be loaded from configuration or database
    return []
