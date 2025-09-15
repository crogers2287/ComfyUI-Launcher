import json
import os
import shutil
import socket
import requests
import hashlib
import unicodedata
import re
import subprocess
import threading
import time
import traceback
import concurrent.futures
import zipfile
import tempfile
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from tqdm import tqdm
from urllib.parse import urlparse
from settings import PROJECT_MAX_PORT, PROJECT_MIN_PORT, PROJECTS_DIR

# Import recovery components
try:
    from .recovery import recoverable
    from .recovery.persistence import SQLitePersistence
    from .recovery.strategies import ExponentialBackoffStrategy
    RECOVERY_AVAILABLE = True
except ImportError:
    RECOVERY_AVAILABLE = False

def check_url_structure(url):
    # Check for huggingface.co URL structure (both blob and resolve URLs)
    # Allow underscores, dots, and hyphens in organization/repo names
    # Include GGUF files and other common model formats
    model_extensions = r'(safetensors|bin|ckpt|pt|pth|gguf|onnx)'
    huggingface_blob_pattern = f'^https://huggingface\\.co/[^/]+/[^/]+/blob/[^/]+/.*\\.{model_extensions}$'
    huggingface_resolve_pattern = f'^https://huggingface\\.co/[^/]+/[^/]+/resolve/[^/]+/.*\\.{model_extensions}$'
    if re.match(huggingface_blob_pattern, url) or re.match(huggingface_resolve_pattern, url):
        return True

    # Check for civitai.com URL structure
    civitai_pattern = r'^https://civitai\.com/models/\d+$'
    if re.match(civitai_pattern, url):
        return True

    return False

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


COMFYUI_REPO_URL = "https://github.com/comfyanonymous/ComfyUI.git"

MAX_DOWNLOAD_ATTEMPTS = 5
DOWNLOAD_RETRY_DELAY = 2  # seconds
DOWNLOAD_TIMEOUT = 300  # 5 minutes per file
MAX_CONCURRENT_DOWNLOADS = 3
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for downloads

CUSTOM_NODES_TO_IGNORE_FROM_SNAPSHOTS = ["ComfyUI-ComfyWorkflows", "ComfyUI-Manager"]

CW_ENDPOINT = os.environ.get("CW_ENDPOINT", "https://comfyworkflows.com")

CONFIG_FILEPATH = "./config.json"

DEFAULT_CONFIG = {"credentials": {"civitai": {"apikey": ""}}}

import os
from typing import List, Dict, Optional, Union
import json

class ModelFileWithNodeInfo:
    def __init__(self, filename: str, original_filepath: str, normalized_filepath: str):
        self.filename = filename
        self.original_filepath = original_filepath
        self.normalized_filepath = normalized_filepath

def convert_to_unix_path(path: str) -> str:
    return path.replace("\\\\", "/").replace("\\", "/")

def convert_to_windows_path(path: str) -> str:
    return path.replace("/", "\\")

def extract_model_file_names_with_node_info(json_data: Union[Dict, List], is_windows: bool = False) -> List[ModelFileWithNodeInfo]:
    file_names = []
    model_filename_extensions = {'.safetensors', '.ckpt', '.pt', '.pth', '.bin'}

    def recursive_search(data: Union[Dict, List, str], in_nodes: bool, node_type: Optional[str]):
        if isinstance(data, dict):
            for key, value in data.items():
                type_ = value.get('type') if isinstance(value, dict) else None
                recursive_search(value, key == 'nodes' if not in_nodes else in_nodes, type_ if in_nodes and not node_type else node_type)
        elif isinstance(data, list):
            for item in data:
                type_ = item.get('type') if isinstance(item, dict) else None
                recursive_search(item, in_nodes, type_ if in_nodes and not node_type else node_type)
        elif isinstance(data, str) and '.' in data:
            original_filepath = data
            normalized_filepath = convert_to_windows_path(original_filepath) if is_windows else convert_to_unix_path(original_filepath)
            filename = os.path.basename(data)

            if '.' + original_filepath.split('.')[-1] in model_filename_extensions:
                file_names.append(ModelFileWithNodeInfo(filename, original_filepath, normalized_filepath))

    recursive_search(json_data, False, None)
    return file_names


def print_process_output(process, log_callback=None):
    for line in iter(process.stdout.readline, b''):
        decoded_line = line.decode()
        print(decoded_line, end='')
        if log_callback:
            log_callback('info', decoded_line.strip())
    process.stdout.close()

def run_command(cmd: List[str], cwd: Optional[str] = None, bg: bool = False, log_callback=None) -> None:
    process = subprocess.Popen(" ".join(cmd), cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    if bg:
        # Create a separate thread to handle the printing of the process's output
        threading.Thread(target=print_process_output, args=(process, log_callback), daemon=True).start()
        return process.pid
    else:
        print_process_output(process, log_callback)
        assert process.wait() == 0

def get_ckpt_names_with_node_info(workflow_json: Union[Dict, List], is_windows: bool) -> List[ModelFileWithNodeInfo]:
    ckpt_names = []
    if isinstance(workflow_json, dict):
        ckpt_names = extract_model_file_names_with_node_info(workflow_json, is_windows)
    elif isinstance(workflow_json, list):
        for item in workflow_json:
            ckpt_names.extend(get_ckpt_names_with_node_info(item, is_windows))
    return ckpt_names

def normalize_model_filepaths_in_workflow_json(workflow_json: dict) -> dict:
    is_windows = os.name == "nt"
    ckpt_names = get_ckpt_names_with_node_info(workflow_json, is_windows)
    for ckpt_name in ckpt_names:
        workflow_json = json.dumps(workflow_json).replace(ckpt_name.original_filepath.replace("\\", "\\\\"), ckpt_name.normalized_filepath.replace("\\", "\\\\"))
        workflow_json = json.loads(workflow_json)
    return workflow_json


def run_command_in_project_venv(project_folder_path, command):
    if os.name == "nt":  # Check if running on Windows
        venv_activate = os.path.join(project_folder_path, "venv", "Scripts", "activate.bat")
    else:
        venv_activate = os.path.join(project_folder_path, "venv", "bin", "activate")
    
    assert os.path.exists(venv_activate), f"Virtualenv does not exist in project folder: {project_folder_path}"
    
    if os.name == "nt":
        command = ["call", venv_activate, "&&", command]
    else:
        command = [".", venv_activate, "&&", command]
    
    # Run the command using subprocess and capture stdout
    run_command(command)

def run_command_in_project_comfyui_venv(project_folder_path, command, in_bg=False):
    venv_activate = os.path.join(project_folder_path, "venv", "Scripts", "activate.bat") if os.name == "nt" else os.path.join(project_folder_path, "venv", "bin", "activate")
    comfyui_dir = os.path.join(project_folder_path, "comfyui")
    
    assert os.path.exists(venv_activate), f"Virtualenv does not exist in project folder: {project_folder_path}"

    if os.name == "nt":
        return run_command([venv_activate, "&&", "cd", comfyui_dir, "&&", command], bg=in_bg)
    else:
        return run_command([".", venv_activate, "&&", "cd", comfyui_dir, "&&", command], bg=in_bg)


def install_default_custom_nodes(project_folder_path, launcher_json=None):
    # install default custom nodes
    # comfyui-manager
    run_command(["git", "clone", f"https://github.com/ltdrdata/ComfyUI-Manager", os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-Manager')])

    # pip install comfyui-manager
    run_command_in_project_venv(
        project_folder_path,
        f"pip install -r {os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-Manager', 'requirements.txt')}",
    )

    run_command(["git", "clone", f"https://github.com/thecooltechguy/ComfyUI-ComfyWorkflows", os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-ComfyWorkflows')])

    # pip install comfyui-comfyworkflows
    run_command_in_project_venv(
        project_folder_path,
        f"pip install -r {os.path.join(project_folder_path, 'comfyui', 'custom_nodes', 'ComfyUI-ComfyWorkflows', 'requirements.txt')}",
    )

def setup_initial_models_folder(models_folder_path):
    assert not os.path.exists(
        models_folder_path
    ), f"Models folder already exists: {models_folder_path}"
    
    tmp_dir = os.path.join(os.path.dirname(models_folder_path), "tmp_comfyui")
    run_command(["git", "clone", COMFYUI_REPO_URL, tmp_dir])

    shutil.move(os.path.join(tmp_dir, "models"), models_folder_path)
    shutil.rmtree(tmp_dir)


def is_launcher_json_format(import_json):
    if "format" in import_json and import_json["format"] == "comfyui_launcher":
        return True
    return False

# Apply recovery decorator to setup_custom_nodes_from_snapshot if available
if RECOVERY_AVAILABLE:
    setup_custom_nodes_from_snapshot = recoverable(
        max_retries=3,
        initial_delay=5.0,
        backoff_factor=2.0,
        max_delay=600.0,
        timeout=1800.0,  # 30 minutes for custom node installation
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=600.0  # 10 minutes
    )(setup_custom_nodes_from_snapshot)

def setup_custom_nodes_from_snapshot(project_folder_path, launcher_json, progress_callback=None, log_callback=None):
    """Install custom nodes with improved dependency resolution and error handling."""
    if not launcher_json or "snapshot_json" not in launcher_json:
        return set()
    
    git_custom_nodes = launcher_json.get("snapshot_json", {}).get("git_custom_nodes", {})
    if not git_custom_nodes:
        return set()
    
    resolver = CustomNodeDependencyResolver(project_folder_path)
    
    # Filter and sort nodes for installation
    nodes_to_install = []
    for repo_url, node_info in git_custom_nodes.items():
        # Skip ignored nodes
        if any(ignore in repo_url for ignore in CUSTOM_NODES_TO_IGNORE_FROM_SNAPSHOTS):
            continue
        
        if not node_info.get("disabled", False):
            nodes_to_install.append((repo_url, node_info))
    
    print(f"\nInstalling {len(nodes_to_install)} custom nodes...")
    if log_callback:
        log_callback('info', f'Installing {len(nodes_to_install)} custom nodes')
    
    # Install nodes with better error handling
    successful_count = 0
    for repo_url, node_info in nodes_to_install:
        node_name = repo_url.split("/")[-1].replace(".git", "")
        print(f"\n[{successful_count + 1}/{len(nodes_to_install)}] Installing: {node_name}")
        if progress_callback:
            progress_callback({
                'stage': 'custom_nodes',
                'current': successful_count + 1,
                'total': len(nodes_to_install),
                'current_item': node_name
            })
        if log_callback:
            log_callback('info', f'Installing custom node: {node_name}')
        
        if resolver.install_custom_node(repo_url, node_info, log_callback=log_callback):
            successful_count += 1
        else:
            print(f"WARNING: Failed to fully install {node_name}")
            if log_callback:
                log_callback('warning', f'Failed to fully install {node_name}')
    
    # Summary
    print(f"\nCustom Nodes Installation Summary:")
    print(f"  Successfully installed: {successful_count}/{len(nodes_to_install)} nodes")
    
    if resolver.failed_nodes:
        print(f"\nFailed nodes ({len(resolver.failed_nodes)}):")
        for node in resolver.failed_nodes:
            print(f"  - {node}")
    
    return resolver.failed_nodes

def compute_sha256_checksum(file_path):
    """Compute SHA256 checksum with larger buffer for better performance."""
    buf_size = 65536  # 64KB buffer
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest().lower()
    except Exception as e:
        print(f"Error computing checksum for {file_path}: {e}")
        return None


@dataclass
class DownloadTask:
    """Represents a file download task with all necessary metadata."""
    url: str
    dest_path: str
    sha256_checksum: str
    dest_relative_path: str
    attempts: int = 0
    success: bool = False
    error: Optional[str] = None
    alternate_urls: List[str] = field(default_factory=list)


class DownloadManager:
    """Manages file downloads with retry logic, progress tracking, and verification."""
    
    def __init__(self, project_folder_path: str, config: dict):
        self.project_folder_path = project_folder_path
        self.config = config
        self.download_cache = {}
        self.failed_downloads: Set[str] = set()
        self.progress_callback = None
        
        # Recovery system integration
        self.recovery_enabled = RECOVERY_AVAILABLE
        self.active_downloads = {}  # Track active downloads for recovery
        self.download_settings = {
            "max_concurrent_downloads": 3,
            "max_retries": 5,
            "chunk_size": 1024 * 1024,
            "timeout": 30,
            "bandwidth_limit": 0,
            "auto_resume": True,
            "verify_checksums": True
        }
        
        # Initialize recovery components if available
        if self.recovery_enabled:
            try:
                self.persistence = SQLitePersistence()
                self.recovery_strategy = ExponentialBackoffStrategy(
                    initial_delay=2.0,
                    backoff_factor=2.0,
                    max_delay=60.0,
                    jitter=True
                )
                print("Recovery system initialized for DownloadManager")
            except Exception as e:
                print(f"Failed to initialize recovery system: {e}")
                self.recovery_enabled = False
        
    def set_progress_callback(self, callback):
        """Set a callback function for progress updates."""
        self.progress_callback = callback
        
    # Recovery system methods
    def get_instance():
        """Get singleton instance of DownloadManager."""
        if not hasattr(DownloadManager, '_instance'):
            DownloadManager._instance = None
        return DownloadManager._instance
    
    @classmethod
    def initialize(cls, project_folder_path: str, config: dict):
        """Initialize the singleton instance."""
        cls._instance = cls(project_folder_path, config)
        return cls._instance
        
    def _generate_download_id(self, url: str, dest_path: str) -> str:
        """Generate unique download ID."""
        import hashlib
        content = f"{url}:{dest_path}"
        return hashlib.sha256(content.encode()).hexdigest()
        
    def _register_download(self, url: str, dest_path: str, task_id: str = None):
        """Register a download for tracking and recovery."""
        download_id = task_id or self._generate_download_id(url, dest_path)
        
        self.active_downloads[download_id] = {
            "id": download_id,
            "url": url,
            "dest_path": dest_path,
            "status": "pending",
            "progress": 0,
            "bytes_downloaded": 0,
            "total_bytes": 0,
            "speed": 0,
            "eta": 0,
            "attempts": 0,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time(),
            "can_resume": True,
            "can_pause": True
        }
        
        return download_id
        
    def _update_download_status(self, download_id: str, **kwargs):
        """Update download status."""
        if download_id in self.active_downloads:
            self.active_downloads[download_id].update(kwargs)
            self.active_downloads[download_id]["updated_at"] = time.time()
            
    def pause_download(self, download_id: str):
        """Pause a specific download."""
        if download_id in self.active_downloads:
            download = self.active_downloads[download_id]
            if download["status"] == "downloading":
                download["status"] = "paused"
                download["can_resume"] = True
                download["can_pause"] = False
                print(f"Download {download_id} paused")
                return True
        return False
        
    def resume_download(self, download_id: str):
        """Resume a paused download."""
        if download_id in self.active_downloads:
            download = self.active_downloads[download_id]
            if download["status"] == "paused":
                download["status"] = "downloading"
                download["can_resume"] = False
                download["can_pause"] = True
                download["attempts"] += 1
                print(f"Download {download_id} resumed")
                return True
        return False
        
    def cancel_download(self, download_id: str):
        """Cancel a download."""
        if download_id in self.active_downloads:
            download = self.active_downloads[download_id]
            download["status"] = "cancelled"
            download["can_resume"] = False
            download["can_pause"] = False
            print(f"Download {download_id} cancelled")
            # Remove from active downloads
            del self.active_downloads[download_id]
            return True
        return False
        
    def _get_cached_file_path(self, sha256_checksum: str) -> Optional[str]:
        """Check if a file with the given checksum already exists in the models directory."""
        models_dir = os.path.join(self.project_folder_path, "comfyui", "models")
        if not os.path.exists(models_dir):
            return None
            
        # Check cache first
        if sha256_checksum in self.download_cache:
            cached_path = self.download_cache[sha256_checksum]
            if os.path.exists(cached_path) and compute_sha256_checksum(cached_path) == sha256_checksum:
                return cached_path
                
        # Search for file with matching checksum
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if compute_sha256_checksum(file_path) == sha256_checksum:
                    self.download_cache[sha256_checksum] = file_path
                    return file_path
        return None
        
    def _download_file_with_progress(self, url: str, dest_path: str, headers: dict = None, download_id: str = None) -> bool:
        """Download a file with progress bar, timeout handling, and resume support."""
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            temp_path = f"{dest_path}.tmp"
            
            # Check if partial download exists
            resume_pos = 0
            if os.path.exists(temp_path):
                resume_pos = os.path.getsize(temp_path)
                headers = headers or {}
                headers['Range'] = f'bytes={resume_pos}-'
                print(f"Resuming download from {resume_pos} bytes")
            
            # Make request with retry logic for connection issues
            max_retries = 3
            retry_delay = 1
            
            for retry in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True)
                    
                    # Check if server supports resume
                    if resume_pos > 0 and response.status_code == 416:
                        # Range not satisfiable, file might be complete
                        print("Server indicates file is complete, starting fresh download")
                        resume_pos = 0
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        headers.pop('Range', None)
                        response = requests.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True)
                    
                    response.raise_for_status()
                    break
                    
                except requests.exceptions.ConnectionError as e:
                    if retry < max_retries - 1:
                        print(f"Connection error, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise
            
            # Get total size
            if response.status_code == 206:  # Partial content
                content_range = response.headers.get('content-range', '')
                if content_range:
                    total_size = int(content_range.split('/')[-1])
                else:
                    total_size = int(response.headers.get("content-length", 0)) + resume_pos
            else:
                total_size = int(response.headers.get("content-length", 0))
            
            # Update recovery status with total size
            if download_id and download_id in self.active_downloads:
                self._update_download_status(download_id, total_bytes=total_size)
            
            # Download with progress
            mode = 'ab' if resume_pos > 0 else 'wb'
            with tqdm(total=total_size, initial=resume_pos, unit="B", unit_scale=True, 
                     desc=os.path.basename(dest_path)) as pbar:
                with open(temp_path, mode) as f:
                    downloaded = resume_pos
                    start_time = time.time()
                    last_progress_time = time.time()
                    last_recovery_update = time.time()
                    
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            pbar.update(len(chunk))
                            
                            # Check for timeout
                            if time.time() - start_time > DOWNLOAD_TIMEOUT:
                                raise TimeoutError(f"Download exceeded {DOWNLOAD_TIMEOUT} seconds")
                            
                            # Progress callback (throttled to once per second)
                            if self.progress_callback and time.time() - last_progress_time > 1:
                                self.progress_callback(dest_path, downloaded, total_size)
                                last_progress_time = time.time()
                            
                            # Update recovery status (throttled to every 2 seconds)
                            if download_id and time.time() - last_recovery_update > 2:
                                progress = (downloaded / total_size * 100) if total_size > 0 else 0
                                speed = downloaded / (time.time() - start_time) if time.time() > start_time else 0
                                eta = (total_size - downloaded) / speed if speed > 0 else 0
                                
                                self._update_download_status(
                                    download_id, 
                                    progress=progress,
                                    bytes_downloaded=downloaded,
                                    speed=speed,
                                    eta=eta
                                )
                                last_recovery_update = time.time()
            
            # Verify download completed
            if total_size > 0 and os.path.getsize(temp_path) != total_size:
                raise ValueError(f"Downloaded file size mismatch: expected {total_size}, got {os.path.getsize(temp_path)}")
            
            # Move temp file to final destination
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(temp_path, dest_path)
            return True
            
        except Exception as e:
            # Keep temp file for resume on certain errors
            if not isinstance(e, (ValueError, requests.exceptions.HTTPError)):
                print(f"Download interrupted, keeping partial file for resume: {temp_path}")
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            print(f"Download error for {url}: {str(e)}")
            return False
            
    def _prepare_download_headers(self, url: str) -> dict:
        """Prepare headers for download based on the URL."""
        headers = {}
        hostname = urlparse(url).hostname
        
        if hostname == "civitai.com" and self.config.get('credentials', {}).get('civitai', {}).get('apikey'):
            headers["Authorization"] = f"Bearer {self.config['credentials']['civitai']['apikey']}"
            
        return headers
        
    def download_file(self, task: DownloadTask) -> DownloadTask:
        """Download a single file with retry logic and verification."""
        # Register download for recovery tracking
        download_id = self._register_download(task.url, task.dest_path)
        self._update_download_status(download_id, status="downloading")
        
        try:
            # Check if file already exists with correct checksum
            if os.path.exists(task.dest_path):
                existing_checksum = compute_sha256_checksum(task.dest_path)
                if existing_checksum == task.sha256_checksum:
                    print(f"File already exists with correct checksum: {task.dest_relative_path}")
                    task.success = True
                    self._update_download_status(download_id, status="completed", progress=100)
                    return task
                    
            # Check cache for file with matching checksum
            cached_path = self._get_cached_file_path(task.sha256_checksum)
            if cached_path:
                print(f"Found cached file with matching checksum, creating hard link: {task.dest_relative_path}")
                try:
                    os.makedirs(os.path.dirname(task.dest_path), exist_ok=True)
                    # Try hard link first, fall back to copy
                    try:
                        os.link(cached_path, task.dest_path)
                    except:
                        shutil.copy2(cached_path, task.dest_path)
                    task.success = True
                    self._update_download_status(download_id, status="completed", progress=100)
                    return task
                except Exception as e:
                    print(f"Failed to link/copy cached file: {e}")
                    
            # Try all URLs (main + alternates)
            all_urls = [task.url] + task.alternate_urls
            headers = self._prepare_download_headers(task.url)
            
            for attempt in range(MAX_DOWNLOAD_ATTEMPTS):
                for url in all_urls:
                    print(f"Downloading {task.dest_relative_path} - Attempt {attempt + 1}/{MAX_DOWNLOAD_ATTEMPTS}")
                    self._update_download_status(download_id, attempts=attempt + 1)
                    
                    if self._download_file_with_progress(url, task.dest_path, headers, download_id):
                        # Verify checksum
                        downloaded_checksum = compute_sha256_checksum(task.dest_path)
                        if downloaded_checksum == task.sha256_checksum:
                            print(f"Successfully downloaded and verified: {task.dest_relative_path}")
                            task.success = True
                            self.download_cache[task.sha256_checksum] = task.dest_path
                            self._update_download_status(download_id, status="completed", progress=100)
                            return task
                        else:
                            print(f"Checksum mismatch for {task.dest_relative_path}: expected {task.sha256_checksum}, got {downloaded_checksum}")
                            os.remove(task.dest_path)
                            
                # Delay before retry
                if attempt < MAX_DOWNLOAD_ATTEMPTS - 1:
                    time.sleep(DOWNLOAD_RETRY_DELAY * (attempt + 1))
                    
            task.error = f"Failed after {MAX_DOWNLOAD_ATTEMPTS} attempts"
            self.failed_downloads.add(task.dest_relative_path)
            self._update_download_status(download_id, status="failed", error=task.error)
            return task
            
        except Exception as e:
            task.error = str(e)
            self.failed_downloads.add(task.dest_relative_path)
            self._update_download_status(download_id, status="failed", error=task.error)
            return task
        
    def download_files_parallel(self, tasks: List[DownloadTask]) -> Tuple[List[DownloadTask], Set[str]]:
        """Download multiple files in parallel with proper error handling."""
        successful_tasks = []
        failed_tasks = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
            future_to_task = {executor.submit(self.download_file, task): task for task in tasks}
            
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result.success:
                        successful_tasks.append(result)
                    else:
                        failed_tasks.append(result)
                except Exception as e:
                    print(f"Exception downloading {task.dest_relative_path}: {e}")
                    task.error = str(e)
                    failed_tasks.append(task)
                    
        return successful_tasks, self.failed_downloads


class CustomNodeDependencyResolver:
    """Resolves and installs dependencies for custom nodes."""
    
    def __init__(self, project_folder_path: str):
        self.project_folder_path = project_folder_path
        self.installed_nodes = set()
        self.failed_nodes = set()
        
    def _get_node_dependencies(self, node_path: str) -> Dict[str, List[str]]:
        """Extract dependencies from a custom node."""
        deps = {
            'pip': [],
            'pip_post': [],
            'system': []
        }
        
        # Check for requirements.txt
        req_path = os.path.join(node_path, 'requirements.txt')
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                deps['pip'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
        # Check for requirements_post.txt
        req_post_path = os.path.join(node_path, 'requirements_post.txt')
        if os.path.exists(req_post_path):
            with open(req_post_path, 'r') as f:
                deps['pip_post'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
        # Check for install.py script
        install_script = os.path.join(node_path, 'install.py')
        if os.path.exists(install_script):
            deps['install_script'] = install_script
            
        return deps
        
    def _install_pip_requirements(self, requirements: List[str], node_name: str, post: bool = False) -> bool:
        """Install pip requirements with proper error handling."""
        if not requirements:
            return True
            
        req_type = "post-requirements" if post else "requirements"
        print(f"Installing {req_type} for {node_name}: {', '.join(requirements)}")
        
        # Create temporary requirements file
        temp_req_file = os.path.join(self.project_folder_path, f"temp_{node_name}_{'post_' if post else ''}requirements.txt")
        try:
            with open(temp_req_file, 'w') as f:
                f.write('\n'.join(requirements))
                
            # Install with pip
            try:
                run_command_in_project_venv(
                    self.project_folder_path,
                    f"pip install -r {temp_req_file} --upgrade"
                )
                return True
            except Exception as e:
                print(f"Failed to install {req_type} for {node_name}: {e}")
                # Try installing requirements one by one
                failed_reqs = []
                for req in requirements:
                    try:
                        run_command_in_project_venv(
                            self.project_folder_path,
                            f"pip install {req} --upgrade"
                        )
                    except:
                        failed_reqs.append(req)
                        
                if failed_reqs:
                    print(f"Failed to install these requirements for {node_name}: {', '.join(failed_reqs)}")
                    return False
                return True
                
        finally:
            if os.path.exists(temp_req_file):
                os.remove(temp_req_file)
                
    # Apply recovery decorator to install_custom_node if available
if RECOVERY_AVAILABLE:
    install_custom_node = recoverable(
        max_retries=3,
        initial_delay=3.0,
        backoff_factor=2.0,
        max_delay=300.0,
        timeout=600.0,  # 10 minutes for custom node install
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=300.0  # 5 minutes
    )(install_custom_node)

def install_custom_node(self, node_url: str, node_info: dict, log_callback=None) -> bool:
        """Install a single custom node with all its dependencies."""
        node_name = node_url.split("/")[-1].replace(".git", "")
        
        if node_name in self.installed_nodes:
            return True
            
        if node_info.get("disabled", False):
            print(f"Skipping disabled node: {node_name}")
            return True
            
        node_path = os.path.join(self.project_folder_path, "comfyui", "custom_nodes", node_name)
        
        try:
            # Clone repository
            print(f"Installing custom node: {node_name}")
            if log_callback:
                log_callback('info', f'Cloning repository: {node_url}')
            if not os.path.exists(node_path):
                run_command(["git", "clone", node_url, node_path, "--recursive"], log_callback=log_callback)
                
            # Checkout specific commit if specified
            if node_info.get("hash"):
                if log_callback:
                    log_callback('info', f'Checking out commit: {node_info["hash"]}')
                run_command(["git", "checkout", node_info["hash"]], cwd=node_path, log_callback=log_callback)
                
            # Get dependencies
            deps = self._get_node_dependencies(node_path)
            
            # Install pip requirements
            if deps['pip']:
                if not self._install_pip_requirements(deps['pip'], node_name):
                    self.failed_nodes.add(node_name)
                    return False
                    
            # Run install script if exists
            if deps.get('install_script'):
                try:
                    print(f"Running install script for {node_name}")
                    run_command_in_project_venv(self.project_folder_path, f"python {deps['install_script']}")
                except Exception as e:
                    print(f"Install script failed for {node_name}: {e}")
                    # Continue anyway as some scripts fail but node still works
                    
            # Install post requirements
            if deps['pip_post']:
                if not self._install_pip_requirements(deps['pip_post'], node_name, post=True):
                    self.failed_nodes.add(node_name)
                    return False
                    
            # Handle special cases
            if node_name == "ComfyUI-CLIPSeg":
                clipseg_file = os.path.join(node_path, "custom_nodes", "clipseg.py")
                if os.path.exists(clipseg_file):
                    shutil.copy(clipseg_file, os.path.join(self.project_folder_path, "comfyui", "custom_nodes", "clipseg.py"))
                    
            self.installed_nodes.add(node_name)
            return True
            
        except Exception as e:
            print(f"Failed to install custom node {node_name}: {e}")
            traceback.print_exc()
            if log_callback:
                log_callback('error', f'Failed to install {node_name}: {str(e)}')
            self.failed_nodes.add(node_name)
            return False


class InstallationValidator:
    """Validates that all dependencies were installed correctly."""
    
    def __init__(self, project_folder_path: str):
        self.project_folder_path = project_folder_path
        self.validation_results = {
            "models": {"total": 0, "valid": 0, "invalid": []},
            "custom_nodes": {"total": 0, "valid": 0, "invalid": []},
            "python_packages": {"total": 0, "valid": 0, "invalid": []}
        }
    
    def validate_model_files(self, launcher_json: dict) -> dict:
        """Validate that all model files were downloaded correctly."""
        if not launcher_json or "files" not in launcher_json:
            return self.validation_results["models"]
        
        print("\nValidating model files...")
        
        for file_infos in launcher_json["files"]:
            if not file_infos:
                continue
                
            primary_info = file_infos[0]
            dest_relative_path = primary_info.get("dest_relative_path")
            sha256_checksum = primary_info.get("sha256_checksum", "").lower()
            
            if not dest_relative_path or not sha256_checksum:
                continue
                
            self.validation_results["models"]["total"] += 1
            dest_path = os.path.join(self.project_folder_path, "comfyui", dest_relative_path)
            
            if os.path.exists(dest_path):
                actual_checksum = compute_sha256_checksum(dest_path)
                if actual_checksum == sha256_checksum:
                    self.validation_results["models"]["valid"] += 1
                else:
                    self.validation_results["models"]["invalid"].append({
                        "path": dest_relative_path,
                        "reason": f"Checksum mismatch: expected {sha256_checksum}, got {actual_checksum}"
                    })
            else:
                self.validation_results["models"]["invalid"].append({
                    "path": dest_relative_path,
                    "reason": "File not found"
                })
        
        return self.validation_results["models"]
    
    def validate_custom_nodes(self, launcher_json: dict) -> dict:
        """Validate that all custom nodes were installed correctly."""
        if not launcher_json or "snapshot_json" not in launcher_json:
            return self.validation_results["custom_nodes"]
        
        git_custom_nodes = launcher_json.get("snapshot_json", {}).get("git_custom_nodes", {})
        
        print("\nValidating custom nodes...")
        
        for repo_url, node_info in git_custom_nodes.items():
            if any(ignore in repo_url for ignore in CUSTOM_NODES_TO_IGNORE_FROM_SNAPSHOTS):
                continue
                
            if node_info.get("disabled", False):
                continue
                
            self.validation_results["custom_nodes"]["total"] += 1
            node_name = repo_url.split("/")[-1].replace(".git", "")
            node_path = os.path.join(self.project_folder_path, "comfyui", "custom_nodes", node_name)
            
            if os.path.exists(node_path):
                # Check if it's a valid git repository
                git_dir = os.path.join(node_path, ".git")
                if os.path.exists(git_dir):
                    self.validation_results["custom_nodes"]["valid"] += 1
                else:
                    self.validation_results["custom_nodes"]["invalid"].append({
                        "name": node_name,
                        "reason": "Not a valid git repository"
                    })
            else:
                self.validation_results["custom_nodes"]["invalid"].append({
                    "name": node_name,
                    "reason": "Directory not found"
                })
        
        return self.validation_results["custom_nodes"]
    
    def validate_python_packages(self, launcher_json: dict) -> dict:
        """Validate that required Python packages are installed."""
        if not launcher_json:
            return self.validation_results["python_packages"]
        
        print("\nValidating Python packages...")
        
        # Get pip requirements from launcher json
        pip_reqs = launcher_json.get("pip_requirements", [])
        
        # Also check requirements from installed custom nodes
        custom_nodes_dir = os.path.join(self.project_folder_path, "comfyui", "custom_nodes")
        if os.path.exists(custom_nodes_dir):
            for node_dir in os.listdir(custom_nodes_dir):
                node_path = os.path.join(custom_nodes_dir, node_dir)
                if os.path.isdir(node_path):
                    req_file = os.path.join(node_path, "requirements.txt")
                    if os.path.exists(req_file):
                        with open(req_file, 'r') as f:
                            node_reqs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                            pip_reqs.extend(node_reqs)
        
        # Check if packages are installed
        if pip_reqs:
            try:
                # Get list of installed packages
                pip_path = os.path.join(self.project_folder_path, "venv", "Scripts" if os.name == "nt" else "bin", "pip")
                result = subprocess.run(
                    [pip_path, "list", "--format=json"],
                    capture_output=True,
                    text=True
                )
                installed_packages = {pkg["name"].lower(): pkg["version"] for pkg in json.loads(result.stdout)}
                
                for req in pip_reqs:
                    self.validation_results["python_packages"]["total"] += 1
                    # Parse package name from requirement string
                    pkg_name = req.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].strip().lower()
                    
                    if pkg_name in installed_packages:
                        self.validation_results["python_packages"]["valid"] += 1
                    else:
                        self.validation_results["python_packages"]["invalid"].append({
                            "package": req,
                            "reason": "Not installed"
                        })
                        
            except Exception as e:
                print(f"Error checking installed packages: {e}")
        
        return self.validation_results["python_packages"]
    
    def validate_all(self, launcher_json: dict) -> dict:
        """Run all validations and return comprehensive results."""
        self.validate_model_files(launcher_json)
        self.validate_custom_nodes(launcher_json)
        self.validate_python_packages(launcher_json)
        
        # Calculate overall success rate
        total_items = sum(v["total"] for v in self.validation_results.values())
        valid_items = sum(v["valid"] for v in self.validation_results.values())
        success_rate = (valid_items / total_items * 100) if total_items > 0 else 100
        
        self.validation_results["summary"] = {
            "total_items": total_items,
            "valid_items": valid_items,
            "success_rate": success_rate,
            "all_valid": all(v["total"] == v["valid"] for v in self.validation_results.values())
        }
        
        return self.validation_results
    
    def print_validation_report(self):
        """Print a detailed validation report."""
        print("\n" + "="*60)
        print("INSTALLATION VALIDATION REPORT")
        print("="*60)
        
        for category, results in self.validation_results.items():
            if category == "summary":
                continue
                
            print(f"\n{category.upper()}:")
            print(f"  Total: {results['total']}")
            print(f"  Valid: {results['valid']}")
            print(f"  Invalid: {len(results['invalid'])}")
            
            if results['invalid']:
                print(f"\n  Failed {category}:")
                for item in results['invalid'][:5]:  # Show first 5 failures
                    if 'path' in item:
                        print(f"    - {item['path']}: {item['reason']}")
                    elif 'name' in item:
                        print(f"    - {item['name']}: {item['reason']}")
                    elif 'package' in item:
                        print(f"    - {item['package']}: {item['reason']}")
                        
                if len(results['invalid']) > 5:
                    print(f"    ... and {len(results['invalid']) - 5} more")
        
        if "summary" in self.validation_results:
            summary = self.validation_results["summary"]
            print(f"\nOVERALL SUMMARY:")
            print(f"  Total items: {summary['total_items']}")
            print(f"  Valid items: {summary['valid_items']}")
            print(f"  Success rate: {summary['success_rate']:.1f}%")
            print(f"  Installation {'SUCCESSFUL' if summary['all_valid'] else 'INCOMPLETE'}")
        
        print("="*60 + "\n")


def get_config():
    with open(CONFIG_FILEPATH, "r") as f:
        return json.load(f)
    
def update_config(config_update):
    config = get_config()
    config.update(config_update)
    with open(CONFIG_FILEPATH, "w") as f:
        json.dump(config, f)
    return config

def set_config(config):
    with open(CONFIG_FILEPATH, "w") as f:
        json.dump(config, f)

# Apply recovery decorator to setup_files_from_launcher_json if available
if RECOVERY_AVAILABLE:
    setup_files_from_launcher_json = recoverable(
        max_retries=3,
        initial_delay=5.0,
        backoff_factor=2.0,
        max_delay=900.0,
        timeout=3600.0,  # 1 hour for file downloads
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=600.0  # 10 minutes
    )(setup_files_from_launcher_json)

def setup_files_from_launcher_json(project_folder_path, launcher_json, progress_callback=None):
    """Download all files specified in launcher JSON with improved error handling and parallel downloads."""
    if not launcher_json or "files" not in launcher_json:
        return set()

    config = get_config()
    download_manager = DownloadManager(project_folder_path, config)
    
    if progress_callback:
        download_manager.set_progress_callback(progress_callback)
    
    # Prepare download tasks
    download_tasks = []
    file_rename_map = {}  # Track renamed files
    
    print(f"Preparing to download {len(launcher_json['files'])} files...")
    
    for file_infos in launcher_json["files"]:
        if not file_infos:  # Skip empty file info
            continue
            
        # Collect all possible URLs for this file
        primary_info = file_infos[0] if file_infos else None
        if not primary_info:
            continue
            
        dest_relative_path = primary_info.get("dest_relative_path")
        sha256_checksum = primary_info.get("sha256_checksum", "")
        if sha256_checksum:
            sha256_checksum = sha256_checksum.lower()
        
        if not dest_relative_path or not sha256_checksum:
            print(f"WARNING: Missing required info for file: {primary_info}")
            continue
            
        dest_path = os.path.join(project_folder_path, "comfyui", dest_relative_path)
        
        # Check if file needs renaming due to conflicts
        if os.path.exists(dest_path):
            existing_checksum = compute_sha256_checksum(dest_path)
            if existing_checksum and existing_checksum != sha256_checksum:
                old_filename = os.path.basename(dest_path)
                new_dest_path = generate_incrementing_filename(dest_path)
                new_filename = os.path.basename(new_dest_path)
                dest_path = new_dest_path
                dest_relative_path = os.path.join(os.path.dirname(dest_relative_path), new_filename)
                file_rename_map[old_filename] = new_filename
                print(f"File conflict detected: renaming {old_filename} to {new_filename}")
        
        # Collect all download URLs
        all_urls = []
        primary_url = primary_info.get("download_url")
        
        if primary_url:
            # Handle ComfyWorkflows launcher URLs
            if "/comfyui-launcher/" in primary_url:
                try:
                    response = requests.get(primary_url, timeout=10)
                    response.raise_for_status()
                    response_json = response.json()
                    all_urls.extend(response_json.get("urls", []))
                except Exception as e:
                    print(f"Failed to fetch download URLs from {primary_url}: {e}")
                    all_urls.append(primary_url)
            else:
                all_urls.append(primary_url)
        
        # Add alternate URLs from other file_info entries
        alternate_urls = []
        for file_info in file_infos[1:]:
            alt_url = file_info.get("download_url")
            if alt_url and alt_url not in all_urls:
                alternate_urls.append(alt_url)
        
        if not all_urls:
            print(f"WARNING: No download URL found for: {dest_relative_path}")
            continue
        
        # Create download task
        task = DownloadTask(
            url=all_urls[0],
            dest_path=dest_path,
            sha256_checksum=sha256_checksum,
            dest_relative_path=dest_relative_path,
            alternate_urls=all_urls[1:] + alternate_urls
        )
        download_tasks.append(task)
    
    # Update launcher JSON with renamed files
    for old_name, new_name in file_rename_map.items():
        rename_file_in_launcher_json(launcher_json, old_name, new_name)
    
    # Execute downloads in parallel
    print(f"Starting parallel download of {len(download_tasks)} files...")
    successful_tasks, failed_files = download_manager.download_files_parallel(download_tasks)
    
    # Report results
    print(f"\nDownload Summary:")
    print(f"  Successfully downloaded: {len(successful_tasks)} files")
    print(f"  Failed downloads: {len(failed_files)} files")
    
    if failed_files:
        print("\nFailed files:")
        for file_path in failed_files:
            print(f"  - {file_path}")
    
    return failed_files


def get_launcher_json_for_workflow_json(workflow_json, resolved_missing_models, skip_model_validation):
    """Convert workflow JSON to launcher JSON format locally"""
    try:
        print(f"[WORKFLOW CONVERSION] Starting conversion with skip_validation={skip_model_validation}")
        
        # Validate input
        if not workflow_json:
            return {
                "success": False,
                "launcher_json": None,
                "error": "No workflow JSON provided"
            }
        
        # If validation is required and no models were resolved, check if workflow needs models
        if not skip_model_validation and not resolved_missing_models:
            # Import model detection to check if models are needed
            from auto_model_downloader import detect_missing_models
            import os
            
            # Detect if workflow has missing models
            models_dir = os.environ.get("MODELS_DIR", "/home/crogers2287/comfy/ComfyUI-Launcher/models")
            missing_models = detect_missing_models(workflow_json, models_dir)
            
            if missing_models:
                print(f"[WORKFLOW CONVERSION] Found {len(missing_models)} missing models")
                # Return error indicating missing models need to be resolved
                return {
                    "success": False,
                    "launcher_json": None,
                    "error": "MISSING_MODELS",
                    "missing_models": missing_models
                }
        
        # Create a basic launcher JSON structure
        launcher_json = {
            "name": "Imported Workflow",
            "description": "Imported workflow from JSON",
            "workflow_json": workflow_json,
            "files": [],
            "requirements": [],
            "models": [],
            "pip_packages": []
        }
        
        # Extract basic metadata from workflow
        if isinstance(workflow_json, dict):
            # Get workflow title if available
            extra = workflow_json.get("extra", {})
            if "title" in extra:
                launcher_json["name"] = extra["title"]
            
            # Add resolved models to files list
            if resolved_missing_models and isinstance(resolved_missing_models, list):
                for model in resolved_missing_models:
                    if isinstance(model, dict) and model.get("source", {}).get("url"):
                        file_entry = {
                            "url": model["source"]["url"],
                            "dest": model["dest_relative_path"],
                            "filename": model["filename"]
                        }
                        if model["source"].get("file_id"):
                            file_entry["hf_file_id"] = model["source"]["file_id"]
                        launcher_json["files"].append(file_entry)
                        
                        # Also add to models list
                        launcher_json["models"].append({
                            "name": model["filename"],
                            "type": model.get("node_type", "unknown"),
                            "path": model["dest_relative_path"]
                        })
        
        # Add default snapshot_json if missing
        if "snapshot_json" not in launcher_json:
            launcher_json["snapshot_json"] = {
                "comfyui": None,
                "git_custom_nodes": {},
                "pip_packages": []
            }
        
        print(f"[WORKFLOW CONVERSION] Successfully converted workflow to launcher format")
        return {
            "success": True,
            "launcher_json": launcher_json,
            "error": None
        }
        
    except Exception as e:
        print(f"[WORKFLOW CONVERSION ERROR] Failed to convert workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "launcher_json": None,
            "error": f"Failed to convert workflow to launcher format: {str(e)}"
        }

def generate_incrementing_filename(filepath):
    filename, file_extension = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{filename} ({counter}){file_extension}"
        counter += 1
    return filepath

def rename_file_in_workflow_json(workflow_json, old_filename, new_filename):
    workflow_json_str = json.dumps(workflow_json)
    workflow_json_str = workflow_json_str.replace(old_filename, new_filename)
    return json.loads(workflow_json_str)

def rename_file_in_launcher_json(launcher_json, old_filename, new_filename):
    workflow_json = launcher_json["workflow_json"]
    workflow_json_str = json.dumps(workflow_json)
    workflow_json_str = workflow_json_str.replace(old_filename, new_filename)
    workflow_json = json.loads(workflow_json_str)
    launcher_json["workflow_json"] = workflow_json


def set_default_workflow_from_launcher_json(project_folder_path, launcher_json):
    if not launcher_json:
        return
    workflow_json = launcher_json["workflow_json"]
    with open(
        os.path.join(
            project_folder_path, "comfyui", "web", "scripts", "defaultGraph.js"
        ),
        "w",
    ) as f:
        f.write(f"export const defaultGraph = {json.dumps(workflow_json, indent=2)};")

    with open(
        os.path.join(
            project_folder_path, "comfyui", "custom_nodes", "ComfyUI-ComfyWorkflows", "current_graph.json"
        ),
        "w",
    ) as f:
        json.dump(workflow_json, f)


def get_launcher_state(project_folder_path):
    state = {}
    launcher_folder_path = os.path.join(project_folder_path, ".launcher")
    os.makedirs(launcher_folder_path, exist_ok=True)

    state_path = os.path.join(launcher_folder_path, "state.json")

    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)

    return state, state_path


def set_launcher_state_data(project_folder_path, data: dict):
    launcher_folder_path = os.path.join(project_folder_path, ".launcher")
    os.makedirs(launcher_folder_path, exist_ok=True)

    existing_state, existing_state_path = get_launcher_state(project_folder_path)
    existing_state.update(data)

    with open(existing_state_path, "w") as f:
        json.dump(existing_state, f)

def install_pip_reqs(project_folder_path, pip_reqs):
    if not pip_reqs:
        return
    print("Installing pip requirements...")
    with open(os.path.join(project_folder_path, "requirements.txt"), "w") as f:
        for req in pip_reqs:
            if isinstance(req, str):
                f.write(req + "\n")
            elif isinstance(req, dict):
                f.write(f"{req['_key']}=={req['_version']}\n")
    run_command_in_project_venv(
        project_folder_path,
        f"pip install -r {os.path.join(project_folder_path, 'requirements.txt')}",
    )

def get_project_port(id):
    project_path = os.path.join(PROJECTS_DIR, id)
    if os.path.exists(os.path.join(project_path, "port.txt")):
        with open(os.path.join(project_path, "port.txt"), "r") as f:
            return int(f.read().strip())
    return find_free_port(PROJECT_MIN_PORT, PROJECT_MAX_PORT)

def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0
    
def find_free_port(start_port, end_port):
    for port in range(start_port, end_port + 1):
        with socket.socket() as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                pass  # Port is already in use, try the next one
    return None  # No free port found in the range

def create_symlink(source, target):
    if os.name == 'nt':  # Check if running on Windows
        run_command(['mklink', '/D', target, source])
    else:
        os.symlink(source, target, target_is_directory=True)

def create_virtualenv(venv_path):
    run_command(['python', '-m', 'venv', venv_path])


def extract_workflow_from_zip(zip_file_path: str) -> Tuple[Optional[dict], Optional[str], List[str]]:
    """
    Extract workflow JSON from a ZIP file.
    
    Args:
        zip_file_path: Path to the ZIP file
        
    Returns:
        Tuple of (workflow_json, temp_dir, extracted_files)
        - workflow_json: The parsed workflow JSON or None if not found
        - temp_dir: Path to temporary directory containing extracted files
        - extracted_files: List of all extracted file paths
    """
    temp_dir = tempfile.mkdtemp(prefix="comfyui_workflow_")
    extracted_files = []
    workflow_json = None
    
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Extract all files
            zip_ref.extractall(temp_dir)
            
            # Get list of extracted files
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    extracted_files.append(file_path)
            
            # Find workflow JSON files
            workflow_candidates = []
            for file_path in extracted_files:
                if file_path.endswith('.json'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                            
                        # Check if it's a ComfyUI workflow
                        if is_comfyui_workflow(json_data):
                            workflow_candidates.append((file_path, json_data))
                    except Exception as e:
                        print(f"Error reading JSON file {file_path}: {e}")
                        continue
            
            # Select the best workflow candidate
            if workflow_candidates:
                # Prefer files named workflow.json or similar
                for file_path, json_data in workflow_candidates:
                    basename = os.path.basename(file_path).lower()
                    if 'workflow' in basename:
                        workflow_json = json_data
                        break
                
                # If no workflow.json found, use the first valid workflow
                if not workflow_json:
                    workflow_json = workflow_candidates[0][1]
        
        return workflow_json, temp_dir, extracted_files
        
    except Exception as e:
        print(f"Error extracting ZIP file: {e}")
        # Clean up on error
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None, None, []


def is_comfyui_workflow(json_data: Union[dict, list]) -> bool:
    """
    Check if a JSON object is a ComfyUI workflow.
    
    Args:
        json_data: Parsed JSON data
        
    Returns:
        True if it appears to be a ComfyUI workflow, False otherwise
    """
    if not isinstance(json_data, dict):
        return False
    
    # Check for launcher format
    if "format" in json_data and json_data["format"] == "comfyui_launcher":
        return True
    
    # Check for standard ComfyUI workflow structure
    # ComfyUI workflows typically have nodes with specific structure
    if "nodes" in json_data and isinstance(json_data["nodes"], list):
        # Check if nodes have ComfyUI-like structure
        for node in json_data["nodes"]:
            if isinstance(node, dict) and "type" in node:
                return True
    
    # Check for numbered node format (alternative ComfyUI format)
    # Some workflows use numbered keys like "1", "2", etc.
    has_numbered_nodes = False
    for key, value in json_data.items():
        if key.isdigit() and isinstance(value, dict):
            if "class_type" in value or "inputs" in value:
                has_numbered_nodes = True
                break
    
    return has_numbered_nodes


def find_workflow_assets(extracted_files: List[str], workflow_json: dict) -> Dict[str, str]:
    """
    Find assets (images, etc.) referenced in the workflow among extracted files.
    
    Args:
        extracted_files: List of extracted file paths
        workflow_json: The workflow JSON
        
    Returns:
        Dictionary mapping referenced filenames to their extracted paths
    """
    assets = {}
    
    # Extract all string values that might be file references
    file_references = set()
    
    def extract_file_references(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                extract_file_references(value)
        elif isinstance(obj, list):
            for item in obj:
                extract_file_references(item)
        elif isinstance(obj, str):
            # Check if it looks like a filename
            if '.' in obj and len(obj) < 256:  # Reasonable filename length
                # Check for common asset extensions
                extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.mp4', '.avi', '.mov']
                if any(obj.lower().endswith(ext) for ext in extensions):
                    file_references.add(obj)
    
    extract_file_references(workflow_json)
    
    # Match references with extracted files
    for ref in file_references:
        ref_basename = os.path.basename(ref)
        for file_path in extracted_files:
            if os.path.basename(file_path) == ref_basename:
                assets[ref] = file_path
                break
    
    return assets


def copy_workflow_assets(assets: Dict[str, str], project_path: str) -> Dict[str, str]:
    """
    Copy workflow assets to appropriate directories in the project.
    
    Args:
        assets: Dictionary mapping referenced filenames to their extracted paths
        project_path: Path to the ComfyUI project
        
    Returns:
        Dictionary mapping original references to new paths
    """
    new_paths = {}
    
    # Ensure input directory exists
    input_dir = os.path.join(project_path, "comfyui", "input")
    os.makedirs(input_dir, exist_ok=True)
    
    for ref, src_path in assets.items():
        try:
            # Determine destination based on file type
            basename = os.path.basename(src_path)
            
            # Copy to input directory (you might want to organize by type)
            dest_path = os.path.join(input_dir, basename)
            
            # Handle naming conflicts
            if os.path.exists(dest_path):
                name, ext = os.path.splitext(basename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(input_dir, f"{name}_{counter}{ext}")
                    counter += 1
            
            # Copy the file
            shutil.copy2(src_path, dest_path)
            
            # Store the new reference
            new_paths[ref] = os.path.basename(dest_path)
            
        except Exception as e:
            print(f"Error copying asset {src_path}: {e}")
    
    return new_paths