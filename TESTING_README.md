# ComfyUI Launcher Recovery Test Suite

This comprehensive test suite covers all recovery scenarios for ComfyUI Launcher Issue #8, ensuring robust handling of network interruptions, application crashes, browser refreshes, and concurrent operations.

## 🎯 Test Coverage

### 1. **Network Interruption Recovery**
- **Network interruption during download with resume capability**
- **Partial download recovery with progress tracking**
- **Connection failure classification and retry strategies**
- **Bandwidth throttling scenarios**
- **Multiple concurrent network failures**

### 2. **Application Crash Recovery**
- **Workflow import crash recovery**
- **Installation crash recovery**
- **Process state restoration**
- **Transaction rollback during crashes**
- **Crash point detection and recovery**

### 3. **Browser Refresh Recovery**
- **WebSocket reconnection recovery**
- **Session state restoration**
- **Form data recovery**
- **UI state persistence**
- **Real-time collaboration recovery**

### 4. **Concurrent Operation Recovery**
- **Multiple concurrent download recoveries**
- **Mixed operation concurrent recovery**
- **Resource contention handling**
- **State synchronization across operations**
- **Deadlock prevention**

### 5. **Advanced Recovery Mechanisms**
- **Circuit breaker activation and recovery**
- **Error classification and intelligent retry**
- **Custom recovery strategies**
- **State persistence across sessions**
- **Performance monitoring during recovery**

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- 4GB RAM minimum
- 2GB free disk space

### Installation
```bash
# Install Python dependencies
pip install pytest pytest-asyncio pytest-timeout aiohttp psutil asyncio-mqtt

# Install Node.js dependencies (for frontend tests)
cd web
npm install
cd ..

# Make test runner executable
chmod +x test_runner.sh
```

### Running Tests

#### **All Tests**
```bash
# Run complete test suite
./test_runner.sh --all

# Or using Python runner
python run_recovery_tests.py --all
```

#### **Specific Test Categories**
```bash
# Unit tests only
./test_runner.sh --unit

# Integration tests only
./test_runner.sh --integration

# End-to-end tests only
./test_runner.sh --e2e

# Performance tests only
./test_runner.sh --performance
```

#### **Quick Test Run**
```bash
# Run essential tests (unit + integration)
./test_runner.sh --quick

# Run tests in parallel
./test_runner.sh --quick --parallel
```

#### **Advanced Options**
```bash
# Generate detailed reports
./test_runner.sh --all --report --verbose

# Custom configuration
python run_recovery_tests.py --config custom_config.json --parallel

# Timeout customization
python run_recovery_tests.py --timeout 600 --unit --integration
```

## 📊 Test Structure

### Backend Tests (`backend/tests/recovery/`)

#### **Core Recovery Tests**
- `test_comprehensive_recovery.py` - Complete backend recovery scenarios
- `test_integration_scenarios.py` - Frontend-backend integration tests
- `test_end_to_end_scenarios.py` - End-to-end recovery workflows
- `test_performance_benchmarks.py` - Performance and load testing

#### **Component Tests**
- `test_decorator.py` - Recovery decorator functionality
- `test_persistence.py` - State persistence mechanisms
- `test_strategies.py` - Recovery strategy implementations
- `test_classification.py` - Error classification system

### Frontend Tests (`web/src/test/`)

#### **React Component Tests**
- `recovery.test.tsx` - Frontend recovery behavior testing
- Component state recovery testing
- WebSocket reconnection testing
- UI state persistence testing

### Configuration and Utilities

#### **Configuration Files**
- `test_config.json` - Comprehensive test configuration
- `conftest.py` - Pytest fixtures and utilities
- `run_recovery_tests.py` - Advanced test runner

#### **Test Utilities**
- `test_runner.sh` - Simple test runner script
- Performance monitoring utilities
- Mock data generators
- Test report generators

## 🎯 Test Scenarios

### Network Interruption Scenarios
1. **Download Recovery**
   - Simulate connection loss during model download
   - Test resume capability from partial downloads
   - Verify progress tracking across interruptions

2. **API Call Recovery**
   - Test API endpoint failures
   - Verify retry logic with different error types
   - Test circuit breaker activation

### Application Crash Scenarios
1. **Workflow Import Crash**
   - Simulate crash during workflow parsing
   - Test state restoration on restart
   - Verify data integrity after recovery

2. **Installation Crash**
   - Simulate installation process crashes
   - Test installation resume capability
   - Verify system state after recovery

### Browser Refresh Scenarios
1. **WebSocket Reconnection**
   - Test automatic reconnection logic
   - Verify state synchronization
   - Test missed message recovery

2. **UI State Recovery**
   - Test form data persistence
   - Verify UI state restoration
   - Test user experience continuity

### Concurrent Operation Scenarios
1. **Multiple Downloads**
   - Test concurrent download recovery
   - Verify resource management
   - Test performance under load

2. **Mixed Operations**
   - Test different operation types concurrently
   - Verify state isolation
   - Test deadlock prevention

## 📈 Performance Testing

### Benchmark Categories
1. **Recovery Overhead**
   - Measure performance impact of recovery system
   - Compare different recovery strategies
   - Test memory usage patterns

2. **Load Testing**
   - Concurrent user simulation
   - Scaling analysis
   - Resource utilization monitoring

3. **Failure Injection**
   - Network failure simulation
   - Service outage testing
   - Resource constraint testing

### Performance Metrics
- **Recovery Time**: Time to recover from failures
- **Success Rate**: Percentage of successful recoveries
- **Resource Usage**: CPU, memory, disk I/O during recovery
- **Throughput**: Operations per second under load
- **Latency**: Response time percentiles

## 🔧 Configuration

### Test Configuration (`test_config.json`)
```json
{
  "test_execution": {
    "timeout_seconds": 300,
    "max_parallel_workers": 8,
    "enable_performance_profiling": true
  },
  "performance_thresholds": {
    "max_overhead_percentage": 20.0,
    "min_success_rate": 90.0,
    "max_recovery_time_ms": 5000.0
  }
}
```

### Environment Variables
```bash
# Enable recovery debugging
export COMFYUI_RECOVERY_DEBUG=true

# Set test timeout
export COMFYUI_TEST_TIMEOUT=600

# Configure parallel execution
export COMFYUI_MAX_WORKERS=8

# Enable performance monitoring
export COMFYUI_PERFORMANCE_MONITORING=true
```

## 📋 Test Reports

### Report Types
1. **JSON Reports** - Machine-readable detailed results
2. **HTML Reports** - Interactive web-based reports
3. **CSV Summaries** - Spreadsheet-compatible summaries
4. **Console Output** - Real-time test progress

### Report Location
```
test_reports/
├── recovery_test_report_20240115_143022.json
├── test_summary_20240115_143022.txt
└── html_reports/
    └── recovery_test_report_20240115_143022.html
```

### Report Contents
- Test execution summary
- Performance metrics
- System resource usage
- Error analysis
- Recommendations for improvement

## 🧪 Test Development

### Adding New Tests

#### **Backend Recovery Test**
```python
@pytest.mark.asyncio
async def test_new_recovery_scenario():
    """Test description"""
    
    @recoverable(max_retries=2, persistence=persistence)
    async def test_operation():
        # Your test logic here
        pass
    
    result = await test_operation()
    assert result["status"] == "success"
```

#### **Frontend Recovery Test**
```typescript
test('should recover from network error', async () => {
  render(<RecoveryComponent />);
  
  // Simulate network failure
  mockApi.getDownloads.mockRejectedValue(new Error('Network error'));
  
  // Verify recovery behavior
  await waitFor(() => {
    expect(screen.getByText(/recovering/i)).toBeInTheDocument();
  });
});
```

### Best Practices
1. **Isolate Tests**: Each test should be independent
2. **Use Mocks**: Mock external dependencies
3. **Cleanup**: Clean up test data after each test
4. **Assert**: Verify both success and failure scenarios
5. **Document**: Add clear documentation for complex tests

## 🔍 Debugging

### Common Issues
1. **Timeout Errors**: Increase timeout in test configuration
2. **Resource Contention**: Reduce parallel worker count
3. **Dependency Issues**: Verify all dependencies are installed
4. **Permission Errors**: Check file and directory permissions

### Debugging Tools
```bash
# Enable verbose logging
./test_runner.sh --verbose

# Run specific test file
python -m pytest backend/tests/recovery/test_comprehensive_recovery.py -v

# Debug with breakpoints
python -m pytest --pdb -x

# Monitor system resources
htop  # Linux/Mac
tasklist  # Windows
```

## 📚 Documentation

### Additional Resources
- **API Documentation**: `backend/src/API_DOCUMENTATION.md`
- **Recovery System**: `backend/src/recovery/README.md`
- **Testing Guidelines**: `TESTING_SUMMARY.md`

### Getting Help
1. **Check Logs**: Review test output and error messages
2. **Review Configuration**: Verify test configuration settings
3. **Check Dependencies**: Ensure all required packages are installed
4. **Community**: Open an issue with detailed error information

## 🏆 Success Criteria

The recovery test suite is considered successful when:

### **Functional Requirements**
- ✅ All recovery scenarios pass with ≥ 90% success rate
- ✅ Performance overhead ≤ 20%
- ✅ Recovery time ≤ 5 seconds for typical scenarios
- ✅ Memory usage increase ≤ 50MB during recovery

### **Performance Requirements**
- ✅ Handle 50+ concurrent operations
- ✅ Maintain ≥ 10 operations/second throughput
- ✅ ≤ 10% error rate under load
- ✅ ≤ 1 second 95th percentile response time

### **Reliability Requirements**
- ✅ Automatic recovery from all simulated failures
- ✅ State consistency across recoveries
- ✅ No data loss during recovery scenarios
- ✅ Graceful degradation under extreme conditions

---

**Note**: This test suite is designed to be comprehensive and may take several minutes to complete when running all tests. Use the `--quick` option for faster execution during development.