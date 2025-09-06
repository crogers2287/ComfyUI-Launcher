"""
Enhanced checksum verification system for downloads.
"""
import hashlib
import os
import time
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import asyncio
import concurrent.futures

# Import from stub if main recovery system not available
try:
    from .decorator import recoverable
    from .types import ErrorCategory
except ImportError:
    from .decorator_stub import recoverable, ErrorCategory


class ChecksumType(Enum):
    """Supported checksum types."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


@dataclass
class ChecksumInfo:
    """Information about a file's checksum."""
    file_path: str
    checksum_type: ChecksumType
    expected_checksum: str
    actual_checksum: Optional[str] = None
    verified: Optional[bool] = None
    verification_time: Optional[float] = None
    file_size: Optional[int] = None


class ChecksumVerifier:
    """
    Enhanced checksum verification with parallel processing and recovery.
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        buffer_size: int = 65536,  # 64KB
        progress_callback: Optional[Callable] = None
    ):
        self.max_workers = max_workers
        self.buffer_size = buffer_size
        self.progress_callback = progress_callback
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    def __del__(self):
        """Clean up executor."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
    
    @recoverable(
        max_retries=2,
        initial_delay=1.0,
        timeout=3600,  # 1 hour for large files
        strategy=None  # Use default strategy
    )
    def compute_checksum(
        self,
        file_path: str,
        checksum_type: ChecksumType = ChecksumType.SHA256,
        verify_size: bool = True
    ) -> str:
        """
        Compute checksum for a file with recovery.
        
        Args:
            file_path: Path to the file
            checksum_type: Type of checksum to compute
            verify_size: Whether to verify file size during computation
            
        Returns:
            Computed checksum as hexadecimal string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
            ValueError: If checksum type is unsupported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Cannot read file: {file_path}")
        
        # Get hasher
        hasher = self._get_hasher(checksum_type)
        
        # Get file info
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        
        if file_size == 0:
            return hasher.hexdigest()
        
        bytes_processed = 0
        start_time = time.time()
        last_progress_time = start_time
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.buffer_size):
                    hasher.update(chunk)
                    bytes_processed += len(chunk)
                    
                    # Progress callback (throttled)
                    current_time = time.time()
                    if (self.progress_callback and 
                        current_time - last_progress_time > 1):  # Every second
                        
                        progress = bytes_processed / file_size
                        speed = bytes_processed / (current_time - start_time)
                        
                        self.progress_callback(
                            file_path=file_path,
                            progress=progress,
                            bytes_processed=bytes_processed,
                            total_bytes=file_size,
                            speed_bps=speed,
                            checksum_type=checksum_type.value
                        )
                        
                        last_progress_time = current_time
            
            # Verify final size if requested
            if verify_size and bytes_processed != file_size:
                raise ValueError(f"File size changed during computation: {file_path}")
            
            return hasher.hexdigest().lower()
            
        except Exception as e:
            # Classify error for recovery decision
            if isinstance(e, (PermissionError, FileNotFoundError)):
                # Don't retry permission/missing file errors
                e.category = ErrorCategory.PERMISSION
            elif isinstance(e, OSError):
                # Retry I/O errors
                e.category = ErrorCategory.RESOURCE
            else:
                e.category = ErrorCategory.UNKNOWN
            
            raise e
    
    def _get_hasher(self, checksum_type: ChecksumType):
        """Get appropriate hasher for checksum type."""
        hashers = {
            ChecksumType.MD5: hashlib.md5,
            ChecksumType.SHA1: hashlib.sha1,
            ChecksumType.SHA256: hashlib.sha256,
            ChecksumType.SHA512: hashlib.sha512
        }
        
        if checksum_type not in hashers:
            raise ValueError(f"Unsupported checksum type: {checksum_type}")
        
        return hashers[checksum_type]()
    
    async def compute_checksum_async(
        self,
        file_path: str,
        checksum_type: ChecksumType = ChecksumType.SHA256
    ) -> str:
        """Compute checksum asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.compute_checksum,
            file_path,
            checksum_type
        )
    
    @recoverable(max_retries=1, timeout=3600)
    def verify_checksum(
        self,
        file_path: str,
        expected_checksum: str,
        checksum_type: ChecksumType = ChecksumType.SHA256
    ) -> ChecksumInfo:
        """
        Verify file against expected checksum.
        
        Args:
            file_path: Path to the file
            expected_checksum: Expected checksum value
            checksum_type: Type of checksum
            
        Returns:
            ChecksumInfo with verification results
        """
        start_time = time.time()
        
        try:
            actual_checksum = self.compute_checksum(file_path, checksum_type)
            verified = actual_checksum == expected_checksum.lower()
            
            return ChecksumInfo(
                file_path=file_path,
                checksum_type=checksum_type,
                expected_checksum=expected_checksum.lower(),
                actual_checksum=actual_checksum,
                verified=verified,
                verification_time=time.time() - start_time,
                file_size=os.path.getsize(file_path)
            )
            
        except Exception as e:
            return ChecksumInfo(
                file_path=file_path,
                checksum_type=checksum_type,
                expected_checksum=expected_checksum.lower(),
                verified=False,
                verification_time=time.time() - start_time,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else None
            )
    
    async def verify_checksum_async(
        self,
        file_path: str,
        expected_checksum: str,
        checksum_type: ChecksumType = ChecksumType.SHA256
    ) -> ChecksumInfo:
        """Verify checksum asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.verify_checksum,
            file_path,
            expected_checksum,
            checksum_type
        )
    
    async def batch_verify(
        self,
        files: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> List[ChecksumInfo]:
        """
        Verify multiple files concurrently.
        
        Args:
            files: List of dicts with keys: file_path, expected_checksum, checksum_type
            max_concurrent: Maximum concurrent verifications
            
        Returns:
            List of ChecksumInfo results
        """
        if max_concurrent is None:
            max_concurrent = self.max_workers
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_single(file_info):
            async with semaphore:
                return await self.verify_checksum_async(
                    file_info['file_path'],
                    file_info['expected_checksum'],
                    file_info.get('checksum_type', ChecksumType.SHA256)
                )
        
        tasks = [verify_single(file_info) for file_info in files]
        return await asyncio.gather(*tasks)
    
    def find_files_by_checksum(
        self,
        directory: str,
        expected_checksum: str,
        checksum_type: ChecksumType = ChecksumType.SHA256,
        max_files: Optional[int] = None
    ) -> List[str]:
        """
        Find files in directory that match the given checksum.
        
        Args:
            directory: Directory to search
            expected_checksum: Checksum to match
            checksum_type: Type of checksum
            max_files: Maximum number of files to return
            
        Returns:
            List of file paths that match the checksum
        """
        matching_files = []
        files_checked = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    actual_checksum = self.compute_checksum(file_path, checksum_type)
                    if actual_checksum == expected_checksum.lower():
                        matching_files.append(file_path)
                        
                        if max_files and len(matching_files) >= max_files:
                            return matching_files
                            
                except Exception:
                    # Skip files that can't be read
                    continue
                
                files_checked += 1
                
                # Progress callback for search
                if self.progress_callback and files_checked % 10 == 0:
                    self.progress_callback(
                        operation="search",
                        files_checked=files_checked,
                        matches_found=len(matching_files),
                        current_file=file_path
                    )
        
        return matching_files
    
    def validate_download(
        self,
        file_path: str,
        expected_size: Optional[int] = None,
        expected_checksum: Optional[str] = None,
        checksum_type: ChecksumType = ChecksumType.SHA256
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of a downloaded file.
        
        Args:
            file_path: Path to the downloaded file
            expected_size: Expected file size in bytes
            expected_checksum: Expected checksum
            checksum_type: Type of checksum
            
        Returns:
            Validation result dictionary
        """
        result = {
            'file_path': file_path,
            'exists': False,
            'size_valid': None,
            'checksum_valid': None,
            'errors': [],
            'warnings': []
        }
        
        # Check existence
        if not os.path.exists(file_path):
            result['errors'].append("File does not exist")
            return result
        
        result['exists'] = True
        
        try:
            # Check size
            actual_size = os.path.getsize(file_path)
            result['actual_size'] = actual_size
            
            if expected_size is not None:
                result['expected_size'] = expected_size
                result['size_valid'] = actual_size == expected_size
                
                if not result['size_valid']:
                    result['errors'].append(
                        f"Size mismatch: expected {expected_size}, got {actual_size}"
                    )
            else:
                result['warnings'].append("No expected size provided for validation")
            
            # Check checksum
            if expected_checksum:
                verification = self.verify_checksum(file_path, expected_checksum, checksum_type)
                result['checksum_valid'] = verification.verified
                result['expected_checksum'] = verification.expected_checksum
                result['actual_checksum'] = verification.actual_checksum
                result['verification_time'] = verification.verification_time
                
                if not result['checksum_valid']:
                    result['errors'].append(
                        f"Checksum mismatch: expected {verification.expected_checksum}, "
                        f"got {verification.actual_checksum}"
                    )
            else:
                result['warnings'].append("No expected checksum provided for validation")
            
            # Overall validity
            result['valid'] = (
                result['exists'] and
                (result['size_valid'] is not False) and
                (result['checksum_valid'] is not False)
            )
            
        except Exception as e:
            result['errors'].append(f"Validation error: {str(e)}")
            result['valid'] = False
        
        return result


# Utility function for backward compatibility
def compute_sha256_checksum(file_path: str) -> Optional[str]:
    """
    Compute SHA256 checksum (backward compatible with existing code).
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA256 checksum or None if error
    """
    verifier = ChecksumVerifier()
    
    try:
        return verifier.compute_checksum(file_path, ChecksumType.SHA256)
    except Exception:
        return None