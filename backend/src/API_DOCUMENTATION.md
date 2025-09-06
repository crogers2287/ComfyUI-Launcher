# ComfyUI Launcher Backend API Documentation

## Overview
This document describes the new backend API endpoints and WebSocket events added to support enhanced UI features for ComfyUI-Launcher.

## WebSocket Events

### Connection
- **Event**: `connect`
- **Description**: Fired when a client connects to the WebSocket server
- **Response**: `connected` event with connection confirmation

### Progress Tracking
- **Event**: `subscribe_project`
- **Payload**: `{ project_id: string }`
- **Description**: Subscribe to real-time progress updates for a specific project
- **Response**: Current progress state if available

- **Event**: `progress_update` (server -> client)
- **Payload**: 
  ```json
  {
    "project_id": "string",
    "progress": {
      "stage": "string",
      "progress": "number (0-100)",
      "current_file": "string (optional)",
      "file_progress": "number (optional)",
      "current": "number (optional)",
      "total": "number (optional)"
    }
  }
  ```

### Log Streaming
- **Event**: `subscribe_logs`
- **Payload**: `{ project_id: string }`
- **Description**: Subscribe to real-time log updates for a specific project

- **Event**: `log_entry` (server -> client)
- **Payload**:
  ```json
  {
    "project_id": "string",
    "log": {
      "timestamp": "ISO 8601 string",
      "level": "info|warning|error",
      "message": "string",
      "data": "object (optional)"
    }
  }
  ```

## REST API Endpoints

### Storage Management

#### GET /api/storage/usage
Get model storage usage broken down by type and project.

**Response**:
```json
{
  "total_size": 123456789,
  "total_human_readable": "117.74 MB",
  "by_type": {
    "checkpoints": {
      "size": 50000000,
      "human_readable": "47.68 MB"
    },
    "loras": {
      "size": 20000000,
      "human_readable": "19.07 MB"
    }
  },
  "by_project": {
    "project-id": {
      "size": 10000000,
      "human_readable": "9.54 MB"
    }
  },
  "disk": {
    "total": 1000000000000,
    "used": 500000000000,
    "free": 500000000000,
    "percent": 50.0,
    "total_human_readable": "931.32 GB",
    "used_human_readable": "465.66 GB",
    "free_human_readable": "465.66 GB"
  }
}
```

### Logs API

#### GET /api/logs/{project_id}
Get installation logs for a specific project with pagination and filtering.

**Query Parameters**:
- `page` (int, default: 1): Page number
- `per_page` (int, default: 100): Items per page
- `level` (string, optional): Filter by log level (info|warning|error)

**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00",
      "level": "info",
      "message": "Starting installation",
      "data": {}
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 100,
    "total": 250,
    "pages": 3
  }
}
```

### Workflow Preview API

#### POST /api/workflow/preview
Parse workflow JSON and extract metadata.

**Request Body**:
```json
{
  "workflow_json": { /* ComfyUI workflow JSON */ }
}
```

**Response**:
```json
{
  "success": true,
  "metadata": {
    "nodes": [
      {
        "id": "1",
        "type": "CheckpointLoaderSimple",
        "title": "Load Checkpoint"
      }
    ],
    "required_models": [
      {
        "filename": "model.safetensors",
        "node_type": "CheckpointLoaderSimple",
        "node_id": "1"
      }
    ],
    "required_custom_nodes": [],
    "estimated_vram": 7500,
    "workflow_type": "txt2img"
  }
}
```

#### POST /api/workflow/validate
Validate workflow before import.

**Request Body**:
```json
{
  "workflow_json": { /* ComfyUI workflow JSON */ }
}
```

**Response**:
```json
{
  "success": true,
  "launcher_json": { /* Processed launcher JSON */ },
  "missing_models": []
}
```

### Model Management API

#### GET /api/models
List all available models with metadata.

**Response**:
```json
{
  "models": [
    {
      "filename": "model.safetensors",
      "path": "checkpoints/model.safetensors",
      "type": "checkpoints",
      "size": 4294967296,
      "size_human": "4.00 GB",
      "modified": "2024-01-01T12:00:00",
      "created": "2024-01-01T10:00:00",
      "used_by_projects": ["project-1", "project-2"]
    }
  ],
  "total_count": 10,
  "total_size": 42949672960,
  "total_size_human": "40.00 GB"
}
```

#### DELETE /api/models/{model_path}
Delete a specific model file.

**Response**:
```json
{
  "success": true,
  "message": "Model checkpoints/model.safetensors deleted successfully"
}
```

**Error Response** (if model is in use):
```json
{
  "error": "Model is in use by projects",
  "projects": ["project-1", "project-2"]
}
```

#### GET /api/models/check-updates
Check for model updates (placeholder for future implementation).

**Response**:
```json
{
  "updates_available": [],
  "message": "Model update checking not yet implemented"
}
```

## Enhanced Error Handling

All endpoints now return detailed error responses with actionable suggestions:

```json
{
  "error": "Port 4001 is already in use",
  "type": "PortInUseError",
  "traceback": "...",
  "suggestions": [
    "Try stopping other ComfyUI instances or change the port range in settings"
  ]
}
```

## Integration with Existing Endpoints

The new features integrate seamlessly with existing endpoints:

- `/api/create_project` and `/api/import_project` now emit real-time progress updates
- Installation logs are automatically captured and stored
- Model downloads include progress tracking
- Custom node installations are logged with detailed status

## Usage Example

```javascript
// Connect to WebSocket
const socket = io('http://localhost:4000');

// Subscribe to project progress
socket.emit('subscribe_project', { project_id: 'my-project' });

// Listen for progress updates
socket.on('progress_update', (data) => {
  console.log(`Project ${data.project_id}: ${data.progress.stage} - ${data.progress.progress}%`);
});

// Subscribe to logs
socket.emit('subscribe_logs', { project_id: 'my-project' });

// Listen for log entries
socket.on('log_entry', (data) => {
  console.log(`[${data.log.level}] ${data.log.message}`);
});

// Get storage usage
fetch('/api/storage/usage')
  .then(res => res.json())
  .then(data => console.log('Storage:', data));

// List models
fetch('/api/models')
  .then(res => res.json())
  .then(data => console.log('Models:', data));
```