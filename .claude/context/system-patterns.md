---
created: 2025-09-06T20:01:08Z
last_updated: 2025-09-06T20:01:08Z
version: 1.0
author: Claude Code PM System
---

# System Patterns

## Architectural Patterns

### Backend Architecture Pattern
- **Pattern**: Service-Oriented Architecture with Async Task Processing
- **API Layer**: Flask provides RESTful endpoints
- **Task Queue**: Celery handles long-running operations
- **Real-time Updates**: WebSocket via SocketIO for progress tracking
- **File-based Message Broker**: Filesystem transport for Celery (no Redis/RabbitMQ dependency)

### Frontend Architecture Pattern
- **Pattern**: Component-Based SPA with Server State Management
- **Routing**: File-based routing with React Router
- **State Management**: Server state via TanStack Query, local state via React hooks
- **Component Design**: Composition with Radix UI primitives
- **Styling**: Utility-first CSS with Tailwind

## Design Patterns Observed

### 1. Repository Pattern
```python
# Model management abstracts storage details
model_finder.py: ModelFinder class handles model discovery across sources
utils.py: Centralized utility functions for common operations
```

### 2. Observer Pattern
```python
# WebSocket events for real-time updates
progress_tracker.py: Emits progress updates
server.py: SocketIO event handlers
```

### 3. Factory Pattern
```python
# Project creation with isolated environments
tasks.py: create_comfyui_project() creates standardized project structure
```

### 4. Singleton Pattern
```python
# Shared instances across application
celery_app: Single Celery instance
socketio: Single SocketIO instance
```

## Data Flow Patterns

### Request Flow
1. **Frontend** → API Request → **Flask Route**
2. **Flask Route** → Validation → **Celery Task** (if async)
3. **Celery Task** → Progress Updates → **WebSocket**
4. **WebSocket** → Real-time Updates → **Frontend**

### Model Management Flow
1. **Workflow Import** → Parse Requirements
2. **Model Finder** → Check Local Cache
3. **If Missing** → Download from Source
4. **Progress Tracking** → Update Frontend
5. **Installation** → Project Virtual Environment

### Project Lifecycle
1. **Create/Import** → Generate unique project ID
2. **Setup Environment** → Isolated Python venv
3. **Install Dependencies** → ComfyUI + requirements
4. **Configure Port** → Assign from pool (4001-4100)
5. **Launch** → Subprocess management

## Communication Patterns

### Frontend-Backend Communication
- **REST API**: Standard CRUD operations
- **WebSocket**: Real-time progress and logs
- **File Upload**: Direct multipart/form-data
- **JSON Payloads**: Consistent request/response format

### Inter-Process Communication
- **Celery**: Filesystem-based message passing
- **Subprocess**: Python subprocess for ComfyUI instances
- **Port Management**: Dynamic port allocation
- **Process Monitoring**: psutil for health checks

## Error Handling Patterns

### Graceful Degradation
```python
# From server.py
try:
    from showinfm import show_in_file_manager
except ImportError:
    def show_in_file_manager(path):
        print(f"Would open file manager at: {path}")
```

### Detailed Error Responses
- Error type classification
- Actionable suggestions
- Stack trace for debugging
- User-friendly messages

## Security Patterns

### Input Validation
- Workflow JSON validation
- Path traversal prevention
- Port range restrictions
- File type verification

### Process Isolation
- Virtual environments per project
- Separate port allocation
- Subprocess sandboxing
- Resource limits

## Performance Patterns

### Caching Strategy
- Model file caching
- Shared models across projects
- Progress state caching
- Configuration caching

### Async Processing
- Long operations via Celery
- Non-blocking UI updates
- Parallel model downloads
- Concurrent project operations

## Testing Patterns

### Test Organization
- Feature-based test files
- Scenario-specific testing
- Real service integration tests
- Browser automation for E2E

### No-Mock Policy
- Tests use real services
- Actual file operations
- Real HTTP requests
- Live WebSocket connections

## Deployment Patterns

### Containerization Ready
- Dockerfile present
- nginx.conf for reverse proxy
- Environment-based configuration
- Volume mapping for persistence

### Development Workflow
- Hot-reload for frontend (Vite)
- Auto-restart scripts
- Log monitoring utilities
- Debug helper scripts