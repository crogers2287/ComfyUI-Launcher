"""
Recovery system for handling failures and retries with enhanced download capabilities.
"""
# Core recovery system (from issue #2 - use stub if not available)
try:
    from .decorator import recoverable
    from .types import (
        RecoveryConfig,
        RecoveryData,
        RecoveryState,
        ErrorCategory,
        RecoveryStrategy,
        StatePersistence
    )
    from .exceptions import (
        RecoveryError,
        RecoveryExhaustedError,
        CircuitBreakerOpenError,
        RecoveryTimeoutError,
        RecoveryStateError
    )
    _FULL_RECOVERY_AVAILABLE = True
except ImportError:
    # Use stub implementation
    from .decorator_stub import (
        recoverable,
        RecoveryConfig,
        RecoveryState,
        ErrorCategory,
        RecoveryError,
        RecoveryExhaustedError,
        CircuitBreakerOpenError,
        RecoveryTimeoutError,
        RecoveryStateError
    )
    _FULL_RECOVERY_AVAILABLE = False
    
    # Stub for missing types
    RecoveryData = None
    RecoveryStrategy = None
    StatePersistence = None

# Download enhancements (issue #5)
from .download_manager import RecoverableDownloadManager, DownloadState
from .download_persistence import DownloadPersistence
from .verification import ChecksumVerifier, ChecksumType, ChecksumInfo
from .integrations import (
    enhance_download_manager,
    create_recoverable_download_function,
    apply_recovery_to_auto_downloader,
    integrate_with_progress_tracker
)


__all__ = [
    # Core decorator (if available)
    'recoverable',
    
    # Types (if available)
    'RecoveryConfig',
    'RecoveryData', 
    'RecoveryState',
    'ErrorCategory',
    'RecoveryStrategy',
    'StatePersistence',
    
    # Exceptions (if available)
    'RecoveryError',
    'RecoveryExhaustedError',
    'CircuitBreakerOpenError',
    'RecoveryTimeoutError',
    'RecoveryStateError',
    
    # Download Enhancement
    'RecoverableDownloadManager',
    'DownloadState',
    'DownloadPersistence',
    
    # Verification
    'ChecksumVerifier',
    'ChecksumType',
    'ChecksumInfo',
    
    # Integration utilities
    'enhance_download_manager',
    'create_recoverable_download_function',
    'apply_recovery_to_auto_downloader',
    'integrate_with_progress_tracker'
]