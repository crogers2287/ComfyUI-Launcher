#!/bin/bash

# Quick test runner script for ComfyUI Launcher recovery tests
# This script provides easy access to common test scenarios

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  ComfyUI Launcher Recovery Test Runner  ${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "run_recovery_tests.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Default test options
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_E2E=false
RUN_PERFORMANCE=false
RUN_PARALLEL=false
GENERATE_REPORT=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --e2e)
            RUN_E2E=true
            shift
            ;;
        --performance)
            RUN_PERFORMANCE=true
            shift
            ;;
        --parallel)
            RUN_PARALLEL=true
            shift
            ;;
        --report)
            GENERATE_REPORT=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_E2E=true
            RUN_PERFORMANCE=true
            shift
            ;;
        --quick)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit          Run unit tests only"
            echo "  --integration   Run integration tests only"
            echo "  --e2e           Run end-to-end tests only"
            echo "  --performance   Run performance tests only"
            echo "  --parallel      Run tests in parallel"
            echo "  --report        Generate detailed test report"
            echo "  --verbose       Enable verbose output"
            echo "  --all           Run all test suites (default)"
            echo "  --quick         Run quick tests (unit + integration)"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --all                    # Run all tests"
            echo "  $0 --unit --integration     # Run unit and integration tests"
            echo "  $0 --performance --report   # Run performance tests with report"
            echo "  $0 --quick --parallel      # Run quick tests in parallel"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# If no options specified, run all tests
if [ "$RUN_UNIT" = false ] && [ "$RUN_INTEGRATION" = false ] && [ "$RUN_E2E" = false ] && [ "$RUN_PERFORMANCE" = false ]; then
    RUN_UNIT=true
    RUN_INTEGRATION=true
    RUN_E2E=true
    RUN_PERFORMANCE=true
fi

# Build command line arguments
PYTHON_ARGS=""

if [ "$RUN_UNIT" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --unit"
fi

if [ "$RUN_INTEGRATION" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --integration"
fi

if [ "$RUN_E2E" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --e2e"
fi

if [ "$RUN_PERFORMANCE" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --performance"
fi

if [ "$RUN_PARALLEL" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --parallel"
fi

if [ "$GENERATE_REPORT" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --report"
fi

if [ "$VERBOSE" = true ]; then
    PYTHON_ARGS="$PYTHON_ARGS --verbose"
fi

# Check dependencies
print_status "Checking dependencies..."

missing_deps=()

# Check for required Python packages
python3 -c "import pytest" 2>/dev/null || missing_deps+=("pytest")
python3 -c "import aiohttp" 2>/dev/null || missing_deps+=("aiohttp")
python3 -c "import psutil" 2>/dev/null || missing_deps+=("psutil")

if [ ${#missing_deps[@]} -gt 0 ]; then
    print_warning "Missing dependencies: ${missing_deps[*]}"
    print_status "Installing missing dependencies..."
    
    # Install missing packages
    for package in "${missing_deps[@]}"; do
        if command -v pip3 &> /dev/null; then
            pip3 install "$package" || print_error "Failed to install $package"
        else
            print_error "pip3 is required to install dependencies"
            exit 1
        fi
    done
fi

# Create test directories if they don't exist
mkdir -p test_reports
mkdir -p test_logs

# Set environment variables for testing
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export COMFYUI_TEST_MODE="true"
export COMFYUI_LOG_LEVEL="INFO"

if [ "$VERBOSE" = true ]; then
    export COMFYUI_LOG_LEVEL="DEBUG"
fi

# Run the tests
print_status "Starting recovery tests..."
print_status "Command: python3 run_recovery_tests.py $PYTHON_ARGS"
echo ""

# Execute the test runner
if python3 run_recovery_tests.py $PYTHON_ARGS; then
    echo ""
    print_status "✅ Tests completed successfully!"
    
    # Show report location if generated
    if [ "$GENERATE_REPORT" = true ] || [ "$RUN_PARALLEL" = true ]; then
        echo ""
        print_status "Test reports generated in:"
        ls -la test_reports/ | tail -5
    fi
else
    echo ""
    print_error "❌ Tests failed!"
    
    # Show error logs if they exist
    if [ -d "test_logs" ]; then
        echo ""
        print_status "Error logs available in test_logs/ directory"
        ls -la test_logs/ | tail -5
    fi
    
    exit 1
fi

# Summary of what was tested
echo ""
print_status "Test Summary:"
echo "  - Unit Tests: $([ "$RUN_UNIT" = true ] && echo "✅ Run" || echo "❌ Skipped")"
echo "  - Integration Tests: $([ "$RUN_INTEGRATION" = true ] && echo "✅ Run" || echo "❌ Skipped")"
echo "  - End-to-End Tests: $([ "$RUN_E2E" = true ] && echo "✅ Run" || echo "❌ Skipped")"
echo "  - Performance Tests: $([ "$RUN_PERFORMANCE" = true ] && echo "✅ Run" || echo "❌ Skipped")"
echo "  - Parallel Execution: $([ "$RUN_PARALLEL" = true ] && echo "✅ Enabled" || echo "❌ Disabled")"
echo "  - Report Generated: $([ "$GENERATE_REPORT" = true ] && echo "✅ Yes" || echo "❌ No")"

echo ""
print_status "🎉 Recovery testing complete!"
echo "Check the test_reports/ directory for detailed results."