"""
Example usage of the enhanced download system.
"""
import asyncio
from pathlib import Path

from .download_manager import RecoverableDownloadManager
from .download_persistence import DownloadPersistence
from .verification import ChecksumVerifier, ChecksumType
from .integrations import enhance_download_manager, apply_recovery_to_auto_downloader


async def example_basic_download():
    """Example of basic download with recovery."""
    # Create download manager
    config = {
        'credentials': {
            'civitai': {'apikey': 'your-api-key'}
        }
    }
    
    download_manager = RecoverableDownloadManager(
        project_path="/path/to/project",
        config=config,
        progress_callback=lambda **kwargs: print(f"Progress: {kwargs['bytes_downloaded']}/{kwargs['total_bytes']}")
    )
    
    try:
        result = await download_manager.download_file(
            url="https://example.com/model.safetensors",
            dest_path="/path/to/models/model.safetensors",
            sha256_checksum="expected_checksum_here",
            alternate_urls=[
                "https://backup.example.com/model.safetensors",
                "https://mirror.example.com/model.safetensors"
            ]
        )
        
        print(f"Download successful: {result['path']}")
        
    except Exception as e:
        print(f"Download failed: {e}")
        
        # Check status for debugging
        status = await download_manager.get_download_status(
            "https://example.com/model.safetensors",
            "/path/to/models/model.safetensors"
        )
        print(f"Download status: {status}")


async def example_batch_download():
    """Example of downloading multiple files with recovery."""
    downloads = [
        {
            'url': 'https://example.com/model1.safetensors',
            'dest_path': '/models/model1.safetensors',
            'checksum': 'checksum1'
        },
        {
            'url': 'https://example.com/model2.safetensors', 
            'dest_path': '/models/model2.safetensors',
            'checksum': 'checksum2'
        },
        {
            'url': 'https://example.com/model3.safetensors',
            'dest_path': '/models/model3.safetensors',
            'checksum': 'checksum3'
        }
    ]
    
    config = {'credentials': {}}
    download_manager = RecoverableDownloadManager("/project", config)
    
    # Download all files concurrently
    tasks = []
    for download in downloads:
        task = download_manager.download_file(
            url=download['url'],
            dest_path=download['dest_path'],
            sha256_checksum=download['checksum']
        )
        tasks.append(task)
    
    # Wait for all downloads
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check results
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Download {i+1} failed: {result}")
        else:
            print(f"Download {i+1} successful: {result['path']}")


async def example_download_monitoring():
    """Example of monitoring download progress and status."""
    persistence = DownloadPersistence()
    
    # Get active downloads
    active_downloads = await persistence.get_active_downloads()
    print(f"Active downloads: {len(active_downloads)}")
    
    for download in active_downloads:
        print(f"  {download['dest_path']}: {download['progress']:.1%}")
    
    # Get download statistics
    stats = await persistence.get_download_statistics()
    print(f"Total downloads: {stats['total_downloads']}")
    print(f"Success rate: {stats['by_status'].get('completed', 0) / stats['total_downloads']:.1%}")
    print(f"Average speed: {stats['average_speed_mbps']:.2f} MB/s")
    
    # Cleanup old downloads
    cleaned = await persistence.cleanup_completed_downloads(days=30)
    print(f"Cleaned up {cleaned} old download records")


def example_checksum_verification():
    """Example of using the checksum verification system."""
    verifier = ChecksumVerifier(
        max_workers=4,
        progress_callback=lambda **kwargs: print(f"Verifying {kwargs['file_path']}: {kwargs['progress']:.1%}")
    )
    
    # Verify single file
    result = verifier.verify_checksum(
        file_path="/models/model.safetensors",
        expected_checksum="expected_sha256_here",
        checksum_type=ChecksumType.SHA256
    )
    
    if result.verified:
        print(f"✓ Checksum verified in {result.verification_time:.2f}s")
    else:
        print(f"✗ Checksum mismatch: expected {result.expected_checksum}, got {result.actual_checksum}")
    
    # Validate complete download
    validation = verifier.validate_download(
        file_path="/models/model.safetensors",
        expected_size=1024*1024*500,  # 500MB
        expected_checksum="expected_sha256_here"
    )
    
    if validation['valid']:
        print("✓ Download validation passed")
    else:
        print("✗ Download validation failed:")
        for error in validation['errors']:
            print(f"  - {error}")


async def example_batch_verification():
    """Example of batch checksum verification."""
    verifier = ChecksumVerifier()
    
    # Files to verify
    files_to_verify = [
        {
            'file_path': '/models/model1.safetensors',
            'expected_checksum': 'checksum1',
            'checksum_type': ChecksumType.SHA256
        },
        {
            'file_path': '/models/model2.safetensors',
            'expected_checksum': 'checksum2',
            'checksum_type': ChecksumType.SHA256
        }
    ]
    
    # Verify all files concurrently
    results = await verifier.batch_verify(files_to_verify, max_concurrent=2)
    
    for result in results:
        status = "✓" if result.verified else "✗"
        print(f"{status} {result.file_path}: {result.verified}")


def example_enhance_existing_system():
    """Example of enhancing existing download system."""
    # Assuming you have an existing DownloadManager
    from backend.src.utils import DownloadManager
    
    try:
        # Create existing manager (this might fail due to missing dependencies)
        existing_manager = DownloadManager(
            project_folder_path="/project",
            config={}
        )
        
        # Enhance it with recovery capabilities
        enhanced_manager = enhance_download_manager(existing_manager)
        
        # Now use it normally, but with recovery
        from backend.src.utils import DownloadTask
        
        task = DownloadTask(
            url="https://example.com/model.safetensors",
            dest_path="/models/model.safetensors",
            sha256_checksum="checksum",
            dest_relative_path="model.safetensors"
        )
        
        result = enhanced_manager.download_file(task)
        
        # Check recovery status
        status = enhanced_manager.get_recovery_status(
            task.url, 
            task.dest_path
        )
        
        if status:
            print(f"Recovery attempts: {status['attempts']}")
            print(f"Last error: {status['last_error']}")
    
    except ImportError:
        print("Could not import existing DownloadManager")


def example_integration_with_progress_tracker():
    """Example of integrating with existing progress tracker."""
    # Mock progress tracker
    class MockProgressTracker:
        def __init__(self):
            self.tasks = {}
        
        def update_progress(self, task_id, progress, message=""):
            self.tasks[task_id] = {'progress': progress, 'message': message}
            print(f"Task {task_id}: {progress:.1%} - {message}")
        
        def fail_task(self, task_id, error):
            self.tasks[task_id] = {'error': error}
            print(f"Task {task_id} failed: {error}")
    
    # Create and enhance progress tracker
    from .integrations import integrate_with_progress_tracker
    
    progress_tracker = MockProgressTracker()
    enhanced_tracker = integrate_with_progress_tracker(progress_tracker)
    
    # Use enhanced tracker (now with recovery checkpoints)
    enhanced_tracker.update_progress("download_model_1", 0.5, "Downloading...")
    enhanced_tracker.update_progress("download_model_1", 1.0, "Complete")
    
    # Can recover progress after restart
    recovered_progress = enhanced_tracker.recover_progress("download_model_1")
    print(f"Recovered progress: {recovered_progress}")


def example_startup_integration():
    """Example of integrating recovery system at startup."""
    print("Applying recovery enhancements to existing systems...")
    
    # Apply to auto downloader
    apply_recovery_to_auto_downloader()
    
    # This would typically be called in your application's startup code
    print("Recovery system initialized and integrated!")


if __name__ == "__main__":
    # Run examples
    print("=== Basic Download Example ===")
    asyncio.run(example_basic_download())
    
    print("\n=== Checksum Verification Example ===")
    example_checksum_verification()
    
    print("\n=== Download Monitoring Example ===")
    asyncio.run(example_download_monitoring())
    
    print("\n=== System Enhancement Example ===")
    example_enhance_existing_system()
    
    print("\n=== Startup Integration Example ===")
    example_startup_integration()