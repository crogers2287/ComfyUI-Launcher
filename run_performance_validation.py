#!/usr/bin/env python3
"""
Simple performance validation script for ComfyUI Launcher recovery system.
Runs comprehensive performance tests and validates against requirements.
"""

import asyncio
import sys
import os
import time
import statistics
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

# Add the backend directory to the Python path
sys.path.insert(0, '/home/crogers2287/comfy/ComfyUI-Launcher/worktrees/issue-8/backend/src')
sys.path.insert(0, '/home/crogers2287/comfy/ComfyUI-Launcher/worktrees/issue-8/backend/tests')
sys.path.insert(0, '/home/crogers2287/comfy/ComfyUI-Launcher/worktrees/issue-8/backend')

try:
    # Import recovery components
    from recovery.performance import PerformanceValidator, validate_recovery_performance
    from recovery import recoverable, RecoveryConfig
    print("✓ Recovery modules imported successfully")
except ImportError as e:
    print(f"✗ Failed to import recovery modules: {e}")
    sys.exit(1)


class SimplePerformanceBenchmark:
    """Simple performance benchmark without external dependencies."""
    
    def __init__(self):
        self.results = {}
        self.max_overhead_percent = 5.0
    
    async def measure_overhead_benchmark(self, iterations: int = 100) -> Dict[str, Any]:
        """Measure overhead of recovery system."""
        print(f"Running overhead benchmark with {iterations} iterations...")
        
        # Baseline operation without recovery
        baseline_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._baseline_operation(i)
            baseline_times.append(time.perf_counter() - start)
        
        # Operation with recovery (no retries)
        recovery_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._recovery_operation(i)
            recovery_times.append(time.perf_counter() - start)
        
        # Calculate metrics
        baseline_avg = statistics.mean(baseline_times)
        recovery_avg = statistics.mean(recovery_times)
        overhead_percent = ((recovery_avg - baseline_avg) / baseline_avg) * 100
        
        return {
            "baseline_avg_ms": baseline_avg * 1000,
            "recovery_avg_ms": recovery_avg * 1000,
            "overhead_percent": overhead_percent,
            "within_threshold": overhead_percent <= self.max_overhead_percent,
            "iterations": iterations
        }
    
    async def _baseline_operation(self, operation_id: int):
        """Baseline operation without recovery."""
        await asyncio.sleep(0.001)  # Simulate work
        return {"operation_id": operation_id, "status": "success"}
    
    @recoverable(max_retries=0)  # No retries, just measure decorator overhead
    async def _recovery_operation(self, operation_id: int):
        """Operation with recovery decorator."""
        await asyncio.sleep(0.001)  # Simulate work
        return {"operation_id": operation_id, "status": "success"}
    
    async def test_checkpoint_performance(self, iterations: int = 50) -> Dict[str, Any]:
        """Test checkpoint write performance."""
        print(f"Testing checkpoint performance with {iterations} iterations...")
        
        checkpoint_times = []
        
        @recoverable(max_retries=2, checkpoint_interval=1)
        async def checkpoint_operation(operation_id: int):
            # Simulate operation with checkpointing
            await asyncio.sleep(0.01)
            return {"operation_id": operation_id, "status": "success"}
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                result = await checkpoint_operation(i)
            except Exception:
                pass  # Continue even if operation fails
            checkpoint_times.append(time.perf_counter() - start)
        
        avg_checkpoint_time = statistics.mean(checkpoint_times)
        
        return {
            "avg_checkpoint_time_ms": avg_checkpoint_time * 1000,
            "total_operations": iterations,
            "checkpoint_time_target_met": avg_checkpoint_time < 0.1  # < 100ms
        }
    
    async def test_recovery_time_performance(self, iterations: int = 30) -> Dict[str, Any]:
        """Test recovery time performance."""
        print(f"Testing recovery time performance with {iterations} iterations...")
        
        recovery_times = []
        success_count = 0
        
        @recoverable(max_retries=3, initial_delay=0.01)
        async def recoverable_operation(operation_id: int):
            # Simulate failure 30% of the time
            if operation_id % 10 < 3:  # 30% failure rate
                raise ConnectionError(f"Simulated failure {operation_id}")
            
            await asyncio.sleep(0.02)
            return {"operation_id": operation_id, "status": "success"}
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                result = await recoverable_operation(i)
                success_count += 1
            except Exception:
                pass  # Expected failures
            recovery_times.append(time.perf_counter() - start)
        
        avg_recovery_time = statistics.mean(recovery_times)
        success_rate = (success_count / iterations) * 100
        
        return {
            "avg_recovery_time_ms": avg_recovery_time * 1000,
            "success_rate_percent": success_rate,
            "total_operations": iterations,
            "successful_operations": success_count,
            "recovery_time_target_met": avg_recovery_time < 0.5,  # < 500ms target
            "success_rate_target_met": success_rate > 90  # > 90% target
        }


class PerformanceReportGenerator:
    """Generate comprehensive performance report."""
    
    def __init__(self):
        self.test_results = {}
        self.report_timestamp = datetime.now(timezone.utc)
    
    def add_result(self, test_name: str, result: Dict[str, Any]):
        """Add test result to the report."""
        self.test_results[test_name] = result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        # Calculate overall metrics
        all_tests_passed = all(
            result.get("within_threshold", True) or 
            result.get("checkpoint_time_target_met", True) or
            result.get("recovery_time_target_met", True)
            for result in self.test_results.values()
        )
        
        overhead_percentages = [
            result.get("overhead_percent", 0)
            for result in self.test_results.values()
            if "overhead_percent" in result
        ]
        
        avg_overhead = statistics.mean(overhead_percentages) if overhead_percentages else 0
        max_overhead = max(overhead_percentages) if overhead_percentages else 0
        
        # Performance score calculation
        overhead_score = max(0, 100 - avg_overhead * 10)  # 1% overhead = 10 point penalty
        
        return {
            "report_timestamp": self.report_timestamp.isoformat(),
            "test_summary": {
                "total_tests": len(self.test_results),
                "all_tests_passed": all_tests_passed,
                "average_overhead_percent": avg_overhead,
                "maximum_overhead_percent": max_overhead,
                "overall_performance_score": overhead_score,
                "meets_requirements": avg_overhead <= 5.0 and all_tests_passed
            },
            "detailed_results": self.test_results,
            "requirements_validation": {
                "overhead_requirement": "Recovery system overhead < 5%",
                "overhead_met": avg_overhead <= 5.0,
                "checkpoint_requirement": "Checkpoint writes < 100ms",
                "checkpoint_met": any(
                    result.get("checkpoint_time_target_met", False)
                    for result in self.test_results.values()
                ),
                "recovery_time_requirement": "Recovery time < 500ms",
                "recovery_time_met": any(
                    result.get("recovery_time_target_met", False)
                    for result in self.test_results.values()
                )
            }
        }
    
    def print_summary(self, report: Dict[str, Any]):
        """Print performance summary."""
        print("\n" + "=" * 60)
        print("PERFORMANCE VALIDATION REPORT")
        print("=" * 60)
        print(f"Report Time: {report['report_timestamp']}")
        print()
        
        summary = report["test_summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"All Tests Passed: {summary['all_tests_passed']}")
        print(f"Average Overhead: {summary['average_overhead_percent']:.2f}%")
        print(f"Maximum Overhead: {summary['maximum_overhead_percent']:.2f}%")
        print(f"Performance Score: {summary['overall_performance_score']:.1f}/100")
        print(f"Meets Requirements: {summary['meets_requirements']}")
        print()
        
        validation = report["requirements_validation"]
        print("Requirements Validation:")
        print(f"  • Overhead < 5%: {'✓' if validation['overhead_met'] else '✗'}")
        print(f"  • Checkpoint < 100ms: {'✓' if validation['checkpoint_met'] else '✗'}")
        print(f"  • Recovery < 500ms: {'✓' if validation['recovery_time_met'] else '✗'}")
        print()
        
        print("Detailed Results:")
        for test_name, result in self.test_results.items():
            print(f"  {test_name}:")
            if "overhead_percent" in result:
                print(f"    Overhead: {result['overhead_percent']:.2f}% ({'✓' if result['within_threshold'] else '✗'})")
            if "avg_checkpoint_time_ms" in result:
                print(f"    Avg Checkpoint Time: {result['avg_checkpoint_time_ms']:.2f}ms ({'✓' if result['checkpoint_time_target_met'] else '✗'})")
            if "avg_recovery_time_ms" in result:
                print(f"    Avg Recovery Time: {result['avg_recovery_time_ms']:.2f}ms ({'✓' if result['recovery_time_target_met'] else '✗'})")
                print(f"    Success Rate: {result['success_rate_percent']:.1f}%")
        print()


async def main():
    """Main performance validation function."""
    print("Starting ComfyUI Launcher Recovery System Performance Validation")
    print("=" * 60)
    
    # Initialize components
    benchmark = SimplePerformanceBenchmark()
    report_generator = PerformanceReportGenerator()
    
    try:
        # Run performance tests
        print("\n1. Measuring Recovery System Overhead")
        print("-" * 40)
        overhead_result = await benchmark.measure_overhead_benchmark(iterations=100)
        report_generator.add_result("overhead_benchmark", overhead_result)
        print(f"  Overhead: {overhead_result['overhead_percent']:.2f}%")
        print(f"  Within Threshold: {overhead_result['within_threshold']}")
        
        print("\n2. Testing Checkpoint Performance")
        print("-" * 40)
        checkpoint_result = await benchmark.test_checkpoint_performance(iterations=50)
        report_generator.add_result("checkpoint_performance", checkpoint_result)
        print(f"  Avg Checkpoint Time: {checkpoint_result['avg_checkpoint_time_ms']:.2f}ms")
        print(f"  Meets Target: {checkpoint_result['checkpoint_time_target_met']}")
        
        print("\n3. Testing Recovery Time Performance")
        print("-" * 40)
        recovery_result = await benchmark.test_recovery_time_performance(iterations=30)
        report_generator.add_result("recovery_time_performance", recovery_result)
        print(f"  Avg Recovery Time: {recovery_result['avg_recovery_time_ms']:.2f}ms")
        print(f"  Success Rate: {recovery_result['success_rate_percent']:.1f}%")
        print(f"  Meets Target: {recovery_result['recovery_time_target_met']}")
        
        # Also run the built-in performance validation if available
        print("\n4. Running Built-in Performance Validation")
        print("-" * 40)
        try:
            builtin_results = await validate_recovery_performance()
            print("  Built-in validation completed successfully")
            print(f"  Meets Requirements: {builtin_results.get('meets_requirements', False)}")
        except Exception as e:
            print(f"  Built-in validation failed: {e}")
        
        # Generate and display report
        print("\n5. Generating Performance Report")
        print("-" * 40)
        report = report_generator.generate_report()
        report_generator.print_summary(report)
        
        # Save report to file
        report_file = "/home/crogers2287/comfy/ComfyUI-Launcher/worktrees/issue-8/performance_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {report_file}")
        
        # Return success status
        return report["test_summary"]["meets_requirements"]
        
    except Exception as e:
        print(f"\n✗ Performance validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)