"""
Enhanced download manager with recovery capabilities.
"""
import os
import time
import hashlib
import json
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
import requests
from urllib.parse import urlparse

# Import from stub if main recovery system not available
try:
    from .decorator import recoverable
    from .persistence import SQLitePersistence
    from .strategies import ExponentialBackoffStrategy
    from .types import RecoveryState, ErrorCategory
except ImportError:
    from .decorator_stub import (
        recoverable, RecoveryState, ErrorCategory,
        RecoveryExhaustedError, CircuitBreakerOpenError, RecoveryTimeoutError
    )
    # Create stub for SQLitePersistence
    class SQLitePersistence:
        def __init__(self, *args, **kwargs):
            pass
        async def load(self, *args): return None
        async def save(self, *args): pass
        async def cleanup_old(self, *args): return 0
    
    # Create stub for strategy
    class ExponentialBackoffStrategy:
        def __init__(self, *args, **kwargs):
            pass


@dataclass
class DownloadState:
    """State information for a download operation."""
    url: str
    dest_path: str
    sha256_checksum: Optional[str] = None
    bytes_downloaded: int = 0
    total_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    attempts: int = 0
    status: str = "pending"  # pending, downloading, completed, failed
    error: Optional[str] = None
    alternate_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DownloadState':
        """Create from dictionary."""
        return cls(**data)


class RecoverableDownloadManager:
    """
    Enhanced download manager with automatic recovery and resume capabilities.
    """
    
    def __init__(
        self, 
        project_path: str,
        config: dict,
        persistence: Optional[SQLitePersistence] = None,
        progress_callback: Optional[Callable] = None
    ):
        self.project_path = Path(project_path)
        self.config = config
        self.persistence = persistence or SQLitePersistence()
        self.progress_callback = progress_callback
        self.chunk_size = 8192
        self.timeout = 30
        
        # Recovery strategy for downloads
        self.download_strategy = ExponentialBackoffStrategy(
            initial_delay=2.0,
            backoff_factor=2.0,
            max_delay=60.0,
            jitter=True,
            retryable_categories={
                ErrorCategory.NETWORK,
                ErrorCategory.TIMEOUT,
                ErrorCategory.RESOURCE
            }
        )
    
    def _get_download_state_key(self, url: str, dest_path: str) -> str:
        """Generate unique key for download state."""
        return hashlib.sha256(f"{url}:{dest_path}".encode()).hexdigest()
    
    async def _load_download_state(self, url: str, dest_path: str) -> Optional[DownloadState]:
        """Load download state from persistence."""
        key = self._get_download_state_key(url, dest_path)
        
        if self.persistence:
            recovery_data = await self.persistence.load(key)
            if recovery_data and recovery_data.metadata.get('download_state'):
                return DownloadState.from_dict(recovery_data.metadata['download_state'])
        
        return None
    
    async def _save_download_state(self, state: DownloadState):
        """Save download state to persistence."""
        if not self.persistence:
            return
        
        from .types import RecoveryData
        
        key = self._get_download_state_key(state.url, state.dest_path)
        
        recovery_data = RecoveryData(
            operation_id=key,
            function_name="download_file",
            args=(state.url, state.dest_path),
            kwargs={},
            state=RecoveryState.IN_PROGRESS if state.status == "downloading" else RecoveryState.SUCCESS,
            attempt=state.attempts,
            metadata={'download_state': state.to_dict()}
        )
        
        await self.persistence.save(recovery_data)
    
    def _prepare_headers(self, url: str, resume_pos: int = 0) -> dict:
        """Prepare headers for download request."""
        headers = {}
        
        # Add range header for resume
        if resume_pos > 0:
            headers['Range'] = f'bytes={resume_pos}-'
        
        # Add authentication if needed
        hostname = urlparse(url).hostname
        if hostname == "civitai.com":
            api_key = self.config.get('credentials', {}).get('civitai', {}).get('apikey')
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        
        return headers
    
    def _verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """Verify file checksum."""
        if not expected_checksum:
            return True
        
        actual_checksum = self._compute_checksum(file_path)
        return actual_checksum == expected_checksum.lower()
    
    def _compute_checksum(self, file_path: str) -> str:
        """Compute SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(65536):
                    sha256.update(chunk)
            return sha256.hexdigest().lower()
        except Exception as e:
            raise IOError(f"Failed to compute checksum: {e}")
    
    @recoverable(
        max_retries=5,
        strategy=None,  # Use instance strategy
        timeout=3600,  # 1 hour timeout for downloads
        circuit_breaker_threshold=10
    )
    async def download_file(
        self,
        url: str,
        dest_path: str,
        sha256_checksum: Optional[str] = None,
        alternate_urls: List[str] = None,
        force_redownload: bool = False
    ) -> Dict[str, Any]:
        """
        Download file with automatic recovery and resume.
        
        Args:
            url: Primary download URL
            dest_path: Destination file path
            sha256_checksum: Expected SHA256 checksum
            alternate_urls: Alternative URLs to try if primary fails
            force_redownload: Force redownload even if file exists
            
        Returns:
            Dictionary with download result
        """
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists with correct checksum
        if not force_redownload and dest_path.exists():
            if not sha256_checksum or self._verify_checksum(str(dest_path), sha256_checksum):
                return {
                    'success': True,
                    'path': str(dest_path),
                    'message': 'File already exists with correct checksum'
                }
        
        # Load or create download state
        state = await self._load_download_state(url, str(dest_path))
        if not state:
            state = DownloadState(
                url=url,
                dest_path=str(dest_path),
                sha256_checksum=sha256_checksum,
                alternate_urls=alternate_urls or []
            )
        
        # Try download with all available URLs
        urls_to_try = [state.url] + state.alternate_urls
        last_error = None
        
        for try_url in urls_to_try:
            try:
                result = await self._download_with_resume(try_url, state)
                if result['success']:
                    # Verify checksum if provided
                    if sha256_checksum and not self._verify_checksum(str(dest_path), sha256_checksum):
                        raise ValueError("Downloaded file checksum mismatch")
                    
                    state.status = "completed"
                    await self._save_download_state(state)
                    
                    return result
                    
            except Exception as e:
                last_error = e
                state.error = str(e)
                state.attempts += 1
                await self._save_download_state(state)
                
                # If it's a permanent error, don't try other URLs
                if isinstance(e, (ValueError, PermissionError)):
                    break
        
        # All attempts failed
        state.status = "failed"
        await self._save_download_state(state)
        
        raise Exception(f"Download failed after all attempts: {last_error}")
    
    async def _download_with_resume(self, url: str, state: DownloadState) -> Dict[str, Any]:
        """
        Download file with resume support.
        """
        temp_path = Path(state.dest_path).with_suffix('.tmp')
        
        # Check for existing partial download
        resume_pos = 0
        if temp_path.exists():
            resume_pos = temp_path.stat().st_size
            state.bytes_downloaded = resume_pos
        
        headers = self._prepare_headers(url, resume_pos)
        
        # Make request
        response = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=self.timeout,
            allow_redirects=True
        )
        
        # Handle 416 Range Not Satisfiable
        if resume_pos > 0 and response.status_code == 416:
            # File might be complete, start fresh
            resume_pos = 0
            state.bytes_downloaded = 0
            temp_path.unlink(missing_ok=True)
            
            headers = self._prepare_headers(url, 0)
            response = requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=self.timeout,
                allow_redirects=True
            )
        
        response.raise_for_status()
        
        # Get total size
        if response.status_code == 206:  # Partial content
            content_range = response.headers.get('content-range', '')
            if content_range:
                state.total_bytes = int(content_range.split('/')[-1])
            else:
                state.total_bytes = int(response.headers.get('content-length', 0)) + resume_pos
        else:
            state.total_bytes = int(response.headers.get('content-length', 0))
        
        # Download with progress tracking
        state.status = "downloading"
        mode = 'ab' if resume_pos > 0 else 'wb'
        
        with open(temp_path, mode) as f:
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if chunk:
                    f.write(chunk)
                    state.bytes_downloaded += len(chunk)
                    state.last_update_time = time.time()
                    
                    # Progress callback
                    if self.progress_callback:
                        self.progress_callback(
                            url=url,
                            bytes_downloaded=state.bytes_downloaded,
                            total_bytes=state.total_bytes,
                            speed=self._calculate_speed(state)
                        )
                    
                    # Periodically save state
                    if time.time() - state.last_update_time > 5:
                        await self._save_download_state(state)
        
        # Verify size
        if state.total_bytes > 0 and temp_path.stat().st_size != state.total_bytes:
            raise ValueError(f"Downloaded file size mismatch")
        
        # Move to final destination
        dest_path = Path(state.dest_path)
        dest_path.unlink(missing_ok=True)
        temp_path.rename(dest_path)
        
        return {
            'success': True,
            'path': str(dest_path),
            'bytes_downloaded': state.bytes_downloaded,
            'message': 'Download completed successfully'
        }
    
    def _calculate_speed(self, state: DownloadState) -> float:
        """Calculate download speed in bytes per second."""
        elapsed = time.time() - state.start_time
        if elapsed > 0:
            return state.bytes_downloaded / elapsed
        return 0.0
    
    async def get_download_status(self, url: str, dest_path: str) -> Optional[Dict[str, Any]]:
        """Get status of a download."""
        state = await self._load_download_state(url, dest_path)
        if not state:
            return None
        
        return {
            'url': state.url,
            'dest_path': state.dest_path,
            'status': state.status,
            'bytes_downloaded': state.bytes_downloaded,
            'total_bytes': state.total_bytes,
            'progress': state.bytes_downloaded / state.total_bytes if state.total_bytes > 0 else 0,
            'attempts': state.attempts,
            'error': state.error
        }
    
    async def cleanup_failed_downloads(self, days: int = 7):
        """Clean up old failed download states."""
        if self.persistence:
            return await self.persistence.cleanup_old(days)