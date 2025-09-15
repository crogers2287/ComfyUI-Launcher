# ComfyUI Launcher Backend API Documentation

## Overview
This document describes the backend API endpoints and WebSocket events for ComfyUI-Launcher, including the comprehensive recovery system added in Issue #8.

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

### Recovery Events

- **Event**: `recovery_update` (server -> client)
- **Description**: Real-time updates for recovery operations
- **Payload**:
  ```json
  {
    "operation_id": "string",
    "function_name": "string",
    "state": "pending|in_progress|recovering|success|failed|exhausted",
    "attempt": "integer",
    "max_attempts": "integer",
    "error": "string (optional)",
    "timestamp": "ISO 8601 string"
  }
  ```

- **Event**: `recovery_completed` (server -> client)
- **Description**: Notification when recovery operation completes
- **Payload**:
  ```json
  {
    "operation_id": "string",
    "success": "boolean",
    "final_state": "string",
    "total_attempts": "integer",
    "duration": "number (seconds)",
    "timestamp": "ISO 8601 string"
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

### Recovery System API

#### GET /api/recovery/status
Get recovery system status and statistics.

**Response**:
```json
{
  "success": true,
  "recovery": {
    "enabled": true,
    "persistence_enabled": true,
    "max_retries": 5,
    "circuit_breaker_threshold": 5,
    "active_operations": 3,
    "total_operations": 1250,
    "recovered_operations": 1180,
    "failed_operations": 70,
    "average_recovery_time": 2.5,
    "retry_attempts": 2450
  }
}
```

#### GET /api/recovery/operations
List all active operations with recovery state.

**Response**:
```json
{
  "success": true,
  "operations": [
    {
      "operation_id": "op_123456",
      "function_name": "download_model",
      "state": "recovering",
      "attempt": 2,
      "max_attempts": 5,
      "error": "Connection timeout",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:05:00Z",
      "metadata": {
        "url": "https://example.com/model.safetensors",
        "destination": "/models/model.safetensors"
      }
    }
  ]
}
```

#### GET /api/recovery/operations/{operation_id}
Get recovery status for a specific operation.

**Response**:
```json
{
  "success": true,
  "operation": {
    "operation_id": "op_123456",
    "function_name": "download_model",
    "state": "recovering",
    "attempt": 2,
    "max_attempts": 5,
    "error": "Connection timeout",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:05:00Z",
    "metadata": {
      "url": "https://example.com/model.safetensors",
      "destination": "/models/model.safetensors",
      "progress": 75.5
    }
  }
}
```

#### POST /api/recovery/operations/{operation_id}/retry
Retry a failed operation.

**Request Body**:
```json
{
  "force": false,
  "max_attempts": 5
}
```

**Response**:
```json
{
  "success": true,
  "message": "Operation op_123456 retry initiated",
  "retry_id": "retry_789012"
}
```

#### POST /api/recovery/operations/{operation_id}/cancel
Cancel an operation with recovery.

**Response**:
```json
{
  "success": true,
  "message": "Operation op_123456 cancelled",
  "state": "cancelled"
}
```

#### POST /api/recovery/test
Test recovery system functionality.

**Response**:
```json
{
  "success": true,
  "test_results": {
    "persistence_test": true,
    "strategy_test": true,
    "classification_test": true,
    "circuit_breaker_test": true,
    "overall": "PASS"
  }
}
```

#### GET /api/recovery/performance
Get recovery system performance metrics.

**Response**:
```json
{
  "success": true,
  "performance": {
    "total_operations": 1250,
    "recovered_operations": 1180,
    "failed_operations": 70,
    "average_recovery_time": 2.5,
    "retry_attempts": 2450,
    "circuit_breaker_trips": 15,
    "success_rate": 0.944,
    "average_attempts_per_recovery": 2.08
  }
}
```

#### POST /api/recovery/performance/validate
Validate recovery system performance impact.

**Request Body**:
```json
{
  "test_duration": 60,
  "concurrent_operations": 10,
  "include_network_simulation": true
}
```

**Response**:
```json
{
  "success": true,
  "validation_results": {
    "baseline_operations_per_second": 25.5,
    "recovery_operations_per_second": 24.8,
    "performance_impact_percent": 2.7,
    "memory_overhead_mb": 12.3,
    "cpu_overhead_percent": 1.2,
    "validation_passed": true,
    "recommendations": [
      "Performance impact is within acceptable limits",
      "Memory overhead is minimal",
      "Consider increasing concurrent operations for better throughput"
    ]
  }
}
```

#### POST /api/recovery/performance/benchmark
Run comprehensive recovery system benchmark.

**Request Body**:
```json
{
  "scenarios": ["network_failures", "timeout_failures", "resource_failures"],
  "iterations": 100,
  "duration": 300
}
```

**Response**:
```json
{
  "success": true,
  "benchmark_results": {
    "overall_score": 95.5,
    "scenario_results": {
      "network_failures": {
        "success_rate": 0.98,
        "average_recovery_time": 3.2,
        "score": 96
      },
      "timeout_failures": {
        "success_rate": 0.95,
        "average_recovery_time": 2.8,
        "score": 94
      },
      "resource_failures": {
        "success_rate": 0.92,
        "average_recovery_time": 4.1,
        "score": 89
      }
    },
    "system_metrics": {
      "cpu_usage_percent": 45.2,
      "memory_usage_mb": 256.8,
      "disk_io_mb_s": 12.5
    }
  }
}
```

#### POST /api/recovery/testing/run
Run comprehensive recovery system tests.

**Response**:
```json
{
  "success": true,
  "test_results": {
    "total_tests": 156,
    "passed_tests": 152,
    "failed_tests": 4,
    "success_rate": 0.974,
    "test_summary": {
      "unit_tests": {"passed": 48, "failed": 0, "success_rate": 1.0},
      "integration_tests": {"passed": 65, "failed": 2, "success_rate": 0.97},
      "performance_tests": {"passed": 28, "failed": 1, "success_rate": 0.97},
      "end_to_end_tests": {"passed": 11, "failed": 1, "success_rate": 0.92}
    },
    "failed_test_details": [
      {
        "test_name": "test_circuit_breaker_timeout",
        "error": "Timeout exceeded",
        "category": "integration"
      }
    ]
  }
}
```

#### GET /api/recovery/testing/scenarios
Get available test scenarios.

**Response**:
```json
{
  "success": true,
  "scenarios": [
    {
      "id": "network_timeout",
      "name": "Network Timeout Recovery",
      "description": "Tests recovery from network timeout errors",
      "category": "network",
      "duration_seconds": 30
    },
    {
      "id": "connection_failure",
      "name": "Connection Failure Recovery",
      "description": "Tests recovery from connection failures",
      "category": "network",
      "duration_seconds": 45
    },
    {
      "id": "disk_space_exhausted",
      "name": "Disk Space Recovery",
      "description": "Tests recovery from disk space errors",
      "category": "resource",
      "duration_seconds": 60
    }
  ]
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

The recovery system integrates seamlessly with existing endpoints:

- `/api/create_project` and `/api/import_project` now have automatic retry capabilities
- Model downloads include progress preservation and recovery
- All operations emit recovery status updates via WebSocket
- Installation processes can be resumed after failures

## Recovery API Usage Examples

### Basic Recovery Monitoring

```javascript
// Get recovery system status
fetch('/api/recovery/status')
  .then(res => res.json())
  .then(data => {
    console.log('Recovery system:', data.recovery);
    if (data.recovery.enabled) {
      console.log(`Success rate: ${(data.recovery.recovered_operations / data.recovery.total_operations * 100).toFixed(1)}%`);
    }
  });

// List active operations
fetch('/api/recovery/operations')
  .then(res => res.json())
  .then(data => {
    data.operations.forEach(op => {
      console.log(`Operation ${op.operation_id}: ${op.state} (attempt ${op.attempt}/${op.max_attempts})`);
    });
  });
```

### Operation Recovery Management

```javascript
// Get specific operation status
async function getOperationStatus(operationId) {
  const response = await fetch(`/api/recovery/operations/${operationId}`);
  const data = await response.json();
  
  if (data.success) {
    const op = data.operation;
    console.log(`Operation ${op.function_name}: ${op.state}`);
    if (op.error) {
      console.log(`Error: ${op.error}`);
    }
    return op;
  }
  return null;
}

// Retry a failed operation
async function retryOperation(operationId, force = false) {
  const response = await fetch(`/api/recovery/operations/${operationId}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force })
  });
  
  const data = await response.json();
  if (data.success) {
    console.log(`Retry initiated: ${data.message}`);
    return data.retry_id;
  } else {
    console.error(`Retry failed: ${data.error}`);
    return null;
  }
}

// Cancel an operation
async function cancelOperation(operationId) {
  const response = await fetch(`/api/recovery/operations/${operationId}/cancel`, {
    method: 'POST'
  });
  
  const data = await response.json();
  if (data.success) {
    console.log(`Operation cancelled: ${data.message}`);
    return true;
  }
  return false;
}
```

### WebSocket Recovery Events

```javascript
// Connect to WebSocket
const socket = io('http://localhost:4000');

// Listen for recovery updates
socket.on('recovery_update', (data) => {
  console.log(`Recovery update for ${data.operation_id}:`);
  console.log(`  State: ${data.state}`);
  console.log(`  Attempt: ${data.attempt}/${data.max_attempts}`);
  if (data.error) {
    console.log(`  Error: ${data.error}`);
  }
  
  // Update UI accordingly
  updateRecoveryUI(data);
});

// Listen for recovery completion
socket.on('recovery_completed', (data) => {
  if (data.success) {
    console.log(`Operation ${data.operation_id} recovered successfully!`);
    console.log(`  Total attempts: ${data.total_attempts}`);
    console.log(`  Duration: ${data.duration}s`);
  } else {
    console.log(`Operation ${data.operation_id} failed recovery: ${data.final_state}`);
  }
  
  // Show notification to user
  showRecoveryNotification(data);
});

// Subscribe to specific operation recovery updates
socket.emit('subscribe_recovery', { operation_id: 'op_123456' });
```

### Performance Monitoring

```javascript
// Get performance metrics
async function getRecoveryPerformance() {
  const response = await fetch('/api/recovery/performance');
  const data = await response.json();
  
  if (data.success) {
    const perf = data.performance;
    console.log('Recovery Performance Metrics:');
    console.log(`  Total Operations: ${perf.total_operations}`);
    console.log(`  Success Rate: ${(perf.success_rate * 100).toFixed(1)}%`);
    console.log(`  Avg Recovery Time: ${perf.average_recovery_time}s`);
    console.log(`  Avg Attempts per Recovery: ${perf.average_attempts_per_recovery}`);
    
    return perf;
  }
  return null;
}

// Run performance validation
async function validatePerformance() {
  const response = await fetch('/api/recovery/performance/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      test_duration: 60,
      concurrent_operations: 5,
      include_network_simulation: true
    })
  });
  
  const data = await response.json();
  if (data.success) {
    const results = data.validation_results;
    console.log('Performance Validation Results:');
    console.log(`  Performance Impact: ${results.performance_impact_percent}%`);
    console.log(`  Memory Overhead: ${results.memory_overhead_mb}MB`);
    console.log(`  Validation Passed: ${results.validation_passed}`);
    
    results.recommendations.forEach(rec => {
      console.log(`  Recommendation: ${rec}`);
    });
    
    return results;
  }
  return null;
}
```

### Testing Recovery System

```javascript
// Run recovery tests
async function runRecoveryTests() {
  const response = await fetch('/api/recovery/testing/run', {
    method: 'POST'
  });
  
  const data = await response.json();
  if (data.success) {
    const results = data.test_results;
    console.log(`Recovery Test Results: ${results.passed_tests}/${results.total_tests} passed`);
    console.log(`Success Rate: ${(results.success_rate * 100).toFixed(1)}%`);
    
    // Show failed tests
    if (results.failed_tests > 0) {
      console.log('Failed Tests:');
      results.failed_test_details.forEach(test => {
        console.log(`  ${test.test_name}: ${test.error} (${test.category})`);
      });
    }
    
    return results;
  }
  return null;
}

// Get available test scenarios
async function getTestScenarios() {
  const response = await fetch('/api/recovery/testing/scenarios');
  const data = await response.json();
  
  if (data.success) {
    console.log('Available Test Scenarios:');
    data.scenarios.forEach(scenario => {
      console.log(`  ${scenario.id}: ${scenario.name}`);
      console.log(`    Description: ${scenario.description}`);
      console.log(`    Category: ${scenario.category}`);
      console.log(`    Duration: ${scenario.duration_seconds}s`);
    });
    
    return data.scenarios;
  }
  return [];
}
```

### Error Handling

```javascript
// Enhanced error handling for recovery operations
async function handleRecoveryError(error, operationId) {
  console.error(`Recovery error for operation ${operationId}:`, error);
  
  // Try to get operation status
  const status = await getOperationStatus(operationId);
  if (status) {
    switch (status.state) {
      case 'recovering':
        console.log('Operation is currently recovering, monitoring...');
        break;
      case 'failed':
      case 'exhausted':
        console.log('Operation failed, suggesting manual retry...');
        // Show retry button to user
        showRetryOption(operationId);
        break;
      default:
        console.log(`Operation in unknown state: ${status.state}`);
    }
  } else {
    console.log('Could not get operation status');
  }
}

// Circuit breaker handling
socket.on('circuit_breaker_update', (data) => {
  if (data.state === 'OPEN') {
    console.warn(`Circuit breaker is open for ${data.operation_type}`);
    console.log(`Operations blocked for ${data.timeout_remaining}s`);
    // Show circuit breaker notification to user
    showCircuitBreakerNotification(data);
  } else if (data.state === 'HALF_OPEN') {
    console.log(`Circuit breaker testing recovery for ${data.operation_type}`);
  }
});
```

## Complete Integration Example

```javascript
class RecoveryManager {
  constructor(socketUrl) {
    this.socket = io(socketUrl);
    this.setupEventListeners();
  }
  
  setupEventListeners() {
    this.socket.on('recovery_update', this.handleRecoveryUpdate.bind(this));
    this.socket.on('recovery_completed', this.handleRecoveryComplete.bind(this));
    this.socket.on('circuit_breaker_update', this.handleCircuitBreakerUpdate.bind(this));
  }
  
  async getSystemStatus() {
    const response = await fetch('/api/recovery/status');
    const data = await response.json();
    return data.success ? data.recovery : null;
  }
  
  async retryOperation(operationId, force = false) {
    const response = await fetch(`/api/recovery/operations/${operationId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force })
    });
    
    const data = await response.json();
    return data.success ? data : null;
  }
  
  handleRecoveryUpdate(data) {
    // Update UI with recovery status
    this.updateRecoveryUI(data);
    
    // Show notifications for important state changes
    if (data.state === 'recovering') {
      this.showNotification(`Operation ${data.operation_id} is recovering...`, 'info');
    } else if (data.state === 'failed') {
      this.showNotification(`Operation ${data.operation_id} failed`, 'error');
    }
  }
  
  handleRecoveryComplete(data) {
    if (data.success) {
      this.showNotification(`Operation recovered successfully!`, 'success');
    } else {
      this.showNotification(`Operation recovery failed`, 'error');
    }
  }
  
  handleCircuitBreakerUpdate(data) {
    if (data.state === 'OPEN') {
      this.showNotification(`Circuit breaker open: ${data.operation_type} operations blocked`, 'warning');
    }
  }
  
  updateRecoveryUI(data) {
    // Update progress bars, status indicators, etc.
    const element = document.getElementById(`recovery-${data.operation_id}`);
    if (element) {
      element.dataset.state = data.state;
      element.dataset.attempt = data.attempt;
      element.dataset.maxAttempts = data.max_attempts;
    }
  }
  
  showNotification(message, type) {
    // Show toast or other notification
    console.log(`[${type.toUpperCase()}] ${message}`);
  }
}

// Usage
const recoveryManager = new RecoveryManager('http://localhost:4000');

// Monitor system status
recoveryManager.getSystemStatus().then(status => {
  console.log('Recovery system status:', status);
});
```