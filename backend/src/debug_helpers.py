import json
import os
from datetime import datetime

DEBUG_DIR = "/tmp/comfyui_launcher_debug"

def ensure_debug_dir():
    """Ensure debug directory exists"""
    os.makedirs(DEBUG_DIR, exist_ok=True)

def debug_log(category, data, request_id=None):
    """Log debug data to file for analysis"""
    ensure_debug_dir()
    
    timestamp = datetime.now().isoformat()
    filename = f"{category}_{timestamp.replace(':', '-')}.json"
    if request_id:
        filename = f"{category}_{request_id}_{timestamp.replace(':', '-')}.json"
    
    filepath = os.path.join(DEBUG_DIR, filename)
    
    debug_data = {
        "timestamp": timestamp,
        "category": category,
        "request_id": request_id,
        "data": data
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(debug_data, f, indent=2)
        print(f"[DEBUG] Logged {category} to {filepath}")
    except Exception as e:
        print(f"[DEBUG ERROR] Failed to log {category}: {e}")

def debug_workflow_import(request_data):
    """Debug helper specifically for workflow imports"""
    import uuid
    request_id = str(uuid.uuid4())[:8]
    
    # Log the raw request
    debug_log("import_request", request_data, request_id)
    
    # Extract and log workflow separately if present
    if "import_json" in request_data:
        workflow = request_data["import_json"]
        debug_log("import_workflow", {
            "node_count": len(workflow.get("nodes", [])),
            "link_count": len(workflow.get("links", [])),
            "has_models": bool(workflow.get("models", [])),
            "workflow_id": workflow.get("id", "unknown"),
            "version": workflow.get("version", "unknown")
        }, request_id)
    
    # Log resolved models
    if "resolved_missing_models" in request_data:
        debug_log("resolved_models", request_data["resolved_missing_models"], request_id)
    
    return request_id

def get_debug_logs(limit=10):
    """Get recent debug logs"""
    ensure_debug_dir()
    
    files = []
    for filename in os.listdir(DEBUG_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(DEBUG_DIR, filename)
            stat = os.stat(filepath)
            files.append({
                "filename": filename,
                "filepath": filepath,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
    
    # Sort by modified time, newest first
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    # Return limited results
    return files[:limit]