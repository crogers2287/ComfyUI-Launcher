"""
Progress and logging tracker for ComfyUI Launcher
Provides shared functionality for tracking installation progress and logs
"""
import json
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, Optional

# Store active progress tracking
active_progress: Dict[str, Dict[str, Any]] = defaultdict(dict)
installation_logs: Dict[str, list] = defaultdict(list)

# WebSocket emitter will be set by the server
socketio_instance = None

def set_socketio(socketio):
    """Set the SocketIO instance for emitting events"""
    global socketio_instance
    socketio_instance = socketio

def update_progress(project_id: str, progress_data: Dict[str, Any]) -> None:
    """Update progress and emit to connected clients"""
    active_progress[project_id].update(progress_data)
    
    if socketio_instance:
        socketio_instance.emit('progress_update', {
            'project_id': project_id,
            'progress': progress_data
        }, room=None)

def add_log_entry(project_id: str, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Add a log entry and emit to connected clients"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message
    }
    if extra_data:
        log_entry['data'] = extra_data
    
    installation_logs[project_id].append(log_entry)
    
    # Also write to file
    from backend.src.settings import PROJECTS_DIR
    log_dir = os.path.join(PROJECTS_DIR, project_id, ".launcher")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "install.log")
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # Emit to connected clients
    if socketio_instance:
        socketio_instance.emit('log_entry', {
            'project_id': project_id,
            'log': log_entry
        }, room=None)

def get_progress(project_id: str) -> Dict[str, Any]:
    """Get current progress for a project"""
    return active_progress.get(project_id, {})

def get_logs(project_id: str) -> list:
    """Get logs for a project"""
    return installation_logs.get(project_id, [])

def clear_progress(project_id: str) -> None:
    """Clear progress for a project"""
    if project_id in active_progress:
        del active_progress[project_id]

def clear_logs(project_id: str) -> None:
    """Clear logs for a project"""
    if project_id in installation_logs:
        del installation_logs[project_id]