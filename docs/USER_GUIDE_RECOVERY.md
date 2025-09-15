# Recovery System User Guide

## Overview

The ComfyUI Launcher Recovery System provides robust automatic recovery capabilities for critical operations, ensuring that failed downloads, interrupted installations, and network issues are automatically handled with minimal user intervention.

## Key Features

- **Automatic Retry**: Failed operations automatically retry with intelligent backoff strategies
- **Progress Preservation**: Download progress and operation state are preserved across interruptions
- **User Controls**: Manual retry, pause, resume, and cancel options for all operations
- **Real-time Monitoring**: Live status updates and recovery indicators
- **Smart Error Handling**: Intelligent error classification determines when retry is appropriate
- **Circuit Breaker Protection**: Prevents cascading failures during systemic issues

## Recovery Indicators and Status

### Operation Status States

| Status | Description | Recovery Action |
|--------|-------------|-----------------|
| **Pending** | Operation is queued or waiting to start | No action needed |
| **In Progress** | Operation is actively running | Monitor progress |
| **Recovering** | Operation failed and is automatically retrying | Monitor retry attempts |
| **Success** | Operation completed successfully | No action needed |
| **Failed** | Operation failed after all retry attempts | Manual retry recommended |
| **Exhausted** | All automatic retries exhausted | Manual intervention required |

### Retry Indicators

The system provides clear visual indicators when recovery is active:

- **Attempt Counter**: Shows current retry attempt (e.g., "Attempt 3/5")
- **Recovery Progress**: Progress bars show recovery status
- **Error Messages**: Detailed error information with suggestions
- **Retry Timer**: Countdown until next retry attempt

## User Controls

### Download Manager Controls

The Download Dashboard provides comprehensive recovery controls:

![Download Dashboard](../../assets/download_dashboard.png)

#### Automatic Controls
- **Pause**: Temporarily stop an operation (preserves state)
- **Resume**: Continue a paused operation
- **Cancel**: Stop an operation and clear its state

#### Manual Recovery Controls
- **Retry Now**: Immediately retry a failed operation
- **Cancel Recovery**: Stop automatic retry attempts
- **Force Retry**: Retry regardless of error classification

### Project Operation Recovery

Project creation, import, and management operations include recovery features:

- **Automatic Retry**: Failed operations automatically retry
- **State Persistence**: Operation progress preserved across server restarts
- **User Notifications**: Real-time updates via WebSocket events

## Recovery in Action

### Typical Recovery Scenario

1. **Operation Starts**: User initiates a download or installation
2. **Network Failure**: Connection drops during operation
3. **Automatic Detection**: System detects failure and classifies error
4. **Retry Initiation**: System waits according to backoff strategy, then retries
5. **Progress Preservation**: Operation continues from where it left off
6. **Success**: Operation completes successfully
7. **User Notification**: User receives completion notification

### Manual Recovery Steps

If automatic recovery doesn't resolve the issue:

1. **Check Error Details**: Review the specific error message
2. **Assess Retry Worthiness**: Determine if the error is temporary
3. **Manual Retry**: Click "Retry Now" in the Download Dashboard
4. **Monitor Progress**: Watch the operation status in real-time
5. **Contact Support**: If issues persist, check logs or contact support

## Troubleshooting Recovery Issues

### Common Recovery Scenarios

#### Network Timeouts
**Symptoms**: Operations fail with "Connection timeout" or "Network unreachable"
**Solutions**:
- Check internet connection
- Verify firewall settings
- Use manual retry after network is restored

#### Disk Space Issues
**Symptoms**: Operations fail with "No space left on device"
**Solutions**:
- Free up disk space
- Clear temporary files
- Reduce concurrent operations

#### Permission Errors
**Symptoms**: Operations fail with "Permission denied" or "Access denied"
**Solutions**:
- Check file/folder permissions
- Run with appropriate user privileges
- Verify installation directory access

#### Server Overload
**Symptoms**: Multiple operations failing simultaneously
**Solutions**:
- Reduce concurrent operations
- Increase retry delays
- Check server resources

### Recovery Configuration

Users can adjust recovery behavior through the Download Settings:

![Recovery Settings](../../assets/recovery_settings.png)

#### Key Settings
- **Max Retries**: Maximum automatic retry attempts (default: 5)
- **Initial Delay**: Time before first retry attempt (default: 2.0 seconds)
- **Backoff Factor**: Multiplier for each subsequent retry delay (default: 2.0)
- **Max Delay**: Maximum time between retries (default: 300 seconds)
- **Circuit Breaker**: Threshold for stopping retries during systemic failures

### Best Practices for Users

#### During Operations
1. **Monitor Progress**: Keep an eye on the Download Dashboard
2. **Check Error Messages**: Review specific error details when operations fail
3. **Use Pause/Resume**: Pause operations when needed rather than cancelling
4. **Manage Concurrent Operations**: Avoid running too many operations simultaneously

#### After Failures
1. **Review Error Details**: Understand why the operation failed
2. **Check System Resources**: Ensure sufficient disk space and network connectivity
3. **Manual Retry**: Use "Retry Now" for appropriate failures
4. **Contact Support**: Provide error details and logs if issues persist

#### Configuration Optimization
1. **Adjust Retry Settings**: Customize based on your network conditions
2. **Monitor Performance**: Watch for patterns in operation failures
3. **Update Settings**: Modify settings as your usage patterns change

## Recovery System Statistics

The system provides detailed statistics about recovery performance:

- **Total Operations**: Number of operations processed
- **Recovered Operations**: Operations that succeeded after retry
- **Failed Operations**: Operations that failed despite recovery attempts
- **Average Recovery Time**: Typical time for successful recovery
- **Retry Attempts**: Total number of retry attempts made

Access statistics through:
- Download Dashboard overview cards
- API endpoint: `/api/recovery/performance`
- System logs and monitoring

## Getting Help

### Support Resources
- **Error Messages**: Detailed error information with actionable suggestions
- **System Logs**: Comprehensive logging of all recovery operations
- **Performance Metrics**: Real-time and historical performance data
- **Community Support**: Forums and documentation for common issues

### When to Contact Support
Contact support if you experience:
- Repeated failures of the same operation
- Recovery system not functioning
- Performance degradation
- Unexpected error messages

### Providing Useful Information
When reporting recovery issues, include:
- Operation type (download, installation, etc.)
- Error message and code
- Number of retry attempts
- System resource status (disk, network, memory)
- Recovery configuration settings

## Conclusion

The ComfyUI Launcher Recovery System is designed to handle the complexities of real-world network operations automatically. By understanding how recovery works and using the available controls effectively, users can minimize downtime and ensure successful completion of their operations.

The system's intelligent error classification, combined with user-configurable settings and comprehensive monitoring, provides a robust foundation for reliable operation in various network and system conditions.