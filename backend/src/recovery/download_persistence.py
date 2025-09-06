"""
Download-specific persistence layer for recovery system.
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio

# Import from stub if main recovery system not available
try:
    from .persistence.sqlite import SQLitePersistence
    from .types import RecoveryData, RecoveryState
except ImportError:
    # Create stub implementations
    from .decorator_stub import RecoveryState
    
    class SQLitePersistence:
        def __init__(self, db_path=None):
            self.db_path = db_path
            self._lock = None
        
        async def initialize(self):
            pass
        
        async def _setup(self):
            pass
        
        async def _run_in_thread(self, func, *args):
            return func(*args)
        
        async def save(self, recovery_data):
            pass
        
        async def load(self, operation_id):
            return None
        
        async def cleanup_old(self, days=7):
            return 0
    
    class RecoveryData:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


class DownloadPersistence(SQLitePersistence):
    """
    Extended persistence specifically for download operations.
    
    Adds download-specific tables and queries.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        # Use dedicated download database
        if db_path is None:
            data_dir = Path.home() / ".comfyui-launcher" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "downloads.db")
        
        super().__init__(db_path)
    
    async def _setup(self) -> None:
        """Create extended schema for downloads."""
        await super()._setup()
        
        # Add download-specific tables
        async with self._lock:
            await self._run_in_thread(self._create_download_schema)
    
    def _create_download_schema(self):
        """Create download-specific schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Downloads table for tracking all downloads
            conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    dest_path TEXT NOT NULL,
                    sha256_checksum TEXT,
                    file_size INTEGER,
                    bytes_downloaded INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    attempts INTEGER DEFAULT 0,
                    recovery_data_id TEXT,
                    FOREIGN KEY (recovery_data_id) REFERENCES recovery_data(operation_id),
                    UNIQUE(url, dest_path)
                )
            """)
            
            # Download checkpoints for resume
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    download_id INTEGER NOT NULL,
                    bytes_downloaded INTEGER NOT NULL,
                    checkpoint_time TEXT NOT NULL,
                    speed_bps REAL,
                    FOREIGN KEY (download_id) REFERENCES downloads(id)
                )
            """)
            
            # Alternative URLs for fallback
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_alternate_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    download_id INTEGER NOT NULL,
                    alternate_url TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    FOREIGN KEY (download_id) REFERENCES downloads(id)
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_downloads_status 
                ON downloads(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_downloads_dest_path 
                ON downloads(dest_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_download 
                ON download_checkpoints(download_id)
            """)
            
            conn.commit()
    
    async def save_download(
        self,
        url: str,
        dest_path: str,
        sha256_checksum: Optional[str] = None,
        file_size: Optional[int] = None,
        alternate_urls: List[str] = None
    ) -> int:
        """Save or update download record."""
        async with self._lock:
            return await self._run_in_thread(
                self._save_download_sync,
                url, dest_path, sha256_checksum, file_size, alternate_urls
            )
    
    def _save_download_sync(
        self,
        url: str,
        dest_path: str,
        sha256_checksum: Optional[str],
        file_size: Optional[int],
        alternate_urls: Optional[List[str]]
    ) -> int:
        """Synchronous save download."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO downloads 
                (url, dest_path, sha256_checksum, file_size, started_at)
                VALUES (?, ?, ?, ?, ?)
            """, (url, dest_path, sha256_checksum, file_size, datetime.utcnow().isoformat()))
            
            download_id = cursor.lastrowid
            
            # Save alternate URLs if provided
            if alternate_urls:
                for priority, alt_url in enumerate(alternate_urls):
                    conn.execute("""
                        INSERT INTO download_alternate_urls
                        (download_id, alternate_url, priority)
                        VALUES (?, ?, ?)
                    """, (download_id, alt_url, priority))
            
            conn.commit()
            return download_id
    
    async def update_download_progress(
        self,
        url: str,
        dest_path: str,
        bytes_downloaded: int,
        speed_bps: Optional[float] = None
    ):
        """Update download progress and create checkpoint."""
        async with self._lock:
            await self._run_in_thread(
                self._update_progress_sync,
                url, dest_path, bytes_downloaded, speed_bps
            )
    
    def _update_progress_sync(
        self,
        url: str,
        dest_path: str,
        bytes_downloaded: int,
        speed_bps: Optional[float]
    ):
        """Synchronous update progress."""
        with sqlite3.connect(self.db_path) as conn:
            # Update download record
            cursor = conn.execute("""
                UPDATE downloads 
                SET bytes_downloaded = ?, status = 'downloading'
                WHERE url = ? AND dest_path = ?
            """, (bytes_downloaded, url, dest_path))
            
            # Get download ID
            cursor = conn.execute("""
                SELECT id FROM downloads WHERE url = ? AND dest_path = ?
            """, (url, dest_path))
            
            row = cursor.fetchone()
            if row:
                download_id = row[0]
                
                # Create checkpoint
                conn.execute("""
                    INSERT INTO download_checkpoints
                    (download_id, bytes_downloaded, checkpoint_time, speed_bps)
                    VALUES (?, ?, ?, ?)
                """, (download_id, bytes_downloaded, datetime.utcnow().isoformat(), speed_bps))
            
            conn.commit()
    
    async def complete_download(self, url: str, dest_path: str):
        """Mark download as completed."""
        async with self._lock:
            await self._run_in_thread(self._complete_download_sync, url, dest_path)
    
    def _complete_download_sync(self, url: str, dest_path: str):
        """Synchronous complete download."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE downloads 
                SET status = 'completed', completed_at = ?
                WHERE url = ? AND dest_path = ?
            """, (datetime.utcnow().isoformat(), url, dest_path))
            conn.commit()
    
    async def fail_download(self, url: str, dest_path: str, error: str):
        """Mark download as failed."""
        async with self._lock:
            await self._run_in_thread(self._fail_download_sync, url, dest_path, error)
    
    def _fail_download_sync(self, url: str, dest_path: str, error: str):
        """Synchronous fail download."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE downloads 
                SET status = 'failed', error_message = ?, 
                    attempts = attempts + 1
                WHERE url = ? AND dest_path = ?
            """, (error, url, dest_path))
            conn.commit()
    
    async def get_download_info(self, url: str, dest_path: str) -> Optional[Dict[str, Any]]:
        """Get download information including progress."""
        async with self._lock:
            return await self._run_in_thread(self._get_download_info_sync, url, dest_path)
    
    def _get_download_info_sync(self, url: str, dest_path: str) -> Optional[Dict[str, Any]]:
        """Synchronous get download info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM downloads WHERE url = ? AND dest_path = ?
            """, (url, dest_path))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            download_id = row['id']
            
            # Get latest checkpoint
            cursor = conn.execute("""
                SELECT * FROM download_checkpoints 
                WHERE download_id = ?
                ORDER BY checkpoint_time DESC
                LIMIT 1
            """, (download_id,))
            
            checkpoint = cursor.fetchone()
            
            # Get alternate URLs
            cursor = conn.execute("""
                SELECT alternate_url FROM download_alternate_urls
                WHERE download_id = ?
                ORDER BY priority
            """, (download_id,))
            
            alternate_urls = [r[0] for r in cursor.fetchall()]
            
            return {
                'url': row['url'],
                'dest_path': row['dest_path'],
                'sha256_checksum': row['sha256_checksum'],
                'file_size': row['file_size'],
                'bytes_downloaded': row['bytes_downloaded'],
                'status': row['status'],
                'started_at': row['started_at'],
                'completed_at': row['completed_at'],
                'error_message': row['error_message'],
                'attempts': row['attempts'],
                'alternate_urls': alternate_urls,
                'latest_checkpoint': {
                    'bytes_downloaded': checkpoint['bytes_downloaded'],
                    'time': checkpoint['checkpoint_time'],
                    'speed_bps': checkpoint['speed_bps']
                } if checkpoint else None,
                'progress': row['bytes_downloaded'] / row['file_size'] if row['file_size'] else 0
            }
    
    async def get_active_downloads(self) -> List[Dict[str, Any]]:
        """Get all active (downloading/pending) downloads."""
        async with self._lock:
            return await self._run_in_thread(self._get_active_downloads_sync)
    
    def _get_active_downloads_sync(self) -> List[Dict[str, Any]]:
        """Synchronous get active downloads."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM downloads 
                WHERE status IN ('pending', 'downloading')
                ORDER BY started_at DESC
            """)
            
            downloads = []
            for row in cursor.fetchall():
                downloads.append({
                    'url': row['url'],
                    'dest_path': row['dest_path'],
                    'status': row['status'],
                    'bytes_downloaded': row['bytes_downloaded'],
                    'file_size': row['file_size'],
                    'progress': row['bytes_downloaded'] / row['file_size'] if row['file_size'] else 0,
                    'attempts': row['attempts']
                })
            
            return downloads
    
    async def cleanup_completed_downloads(self, days: int = 30) -> int:
        """Clean up old completed download records."""
        async with self._lock:
            return await self._run_in_thread(self._cleanup_completed_sync, days)
    
    def _cleanup_completed_sync(self, days: int) -> int:
        """Synchronous cleanup completed downloads."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete old checkpoints first
            conn.execute("""
                DELETE FROM download_checkpoints
                WHERE download_id IN (
                    SELECT id FROM downloads 
                    WHERE status = 'completed' 
                    AND completed_at < ?
                )
            """, (cutoff_date.isoformat(),))
            
            # Delete alternate URLs
            conn.execute("""
                DELETE FROM download_alternate_urls
                WHERE download_id IN (
                    SELECT id FROM downloads 
                    WHERE status = 'completed' 
                    AND completed_at < ?
                )
            """, (cutoff_date.isoformat(),))
            
            # Delete downloads
            cursor = conn.execute("""
                DELETE FROM downloads 
                WHERE status = 'completed' 
                AND completed_at < ?
            """, (cutoff_date.isoformat(),))
            
            conn.commit()
            return cursor.rowcount
    
    async def get_download_statistics(self) -> Dict[str, Any]:
        """Get download statistics."""
        async with self._lock:
            return await self._run_in_thread(self._get_statistics_sync)
    
    def _get_statistics_sync(self) -> Dict[str, Any]:
        """Synchronous get statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Count by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM downloads
                GROUP BY status
            """)
            
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Total bytes downloaded
            cursor = conn.execute("""
                SELECT SUM(bytes_downloaded) FROM downloads
            """)
            total_bytes = cursor.fetchone()[0] or 0
            
            # Average download speed
            cursor = conn.execute("""
                SELECT AVG(speed_bps) FROM download_checkpoints
                WHERE speed_bps > 0
            """)
            avg_speed = cursor.fetchone()[0] or 0
            
            return {
                'total_downloads': sum(status_counts.values()),
                'by_status': status_counts,
                'total_bytes_downloaded': total_bytes,
                'average_speed_bps': avg_speed,
                'average_speed_mbps': avg_speed / (1024 * 1024) if avg_speed > 0 else 0
            }