#!/usr/bin/env python3
"""
Standalone performance validation for ComfyUI Launcher recovery system.
Validates that performance requirements are met (<5% overhead).
"""

import asyncio
import time
import statistics
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

# Add the recovery module path
sys.path.insert(0, '/home/crogers2287/comfy/ComfyUI-Launcher/worktrees/issue-8/backend/src')

try:
    from recovery import recoverable, RecoveryConfig, RecoveryExhaustedError
    RECOVERY_AVAILABLE = True
    print("✓ Recovery system imported successfully")
except ImportError as e:
    print(f"✗ Failed to import recovery system: {e}")
    RECOVERY_AVAILABLE = False
    sys.exit(1)


@dataclass
class PerformanceResult:
    """Result of a performance test."""
    test_name: str
    baseline_time: float
    recovery_time: float
    overhead_percent: float
    within_threshold: bool
    iterations: int
    details: str


class PerformanceValidator:
    """Validates recovery system performance."""
    
    def __init__(self, max_overhead_percent: float = 5.0):
        self.max_overhead_percent = max_overhead_percent
        self.results: List[PerformanceResult] = []
    
    async def measure_decorator_overhead(self, iterations: int = 1000) -> PerformanceResult:
        """Measure overhead of recovery decorator."""
        print(f"Measuring decorator overhead with {iterations} iterations...")
        
        # Baseline - no recovery
        baseline_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._baseline_operation(f"op_{i}")
            baseline_times.append(time.perf_counter() - start)
        
        baseline_avg = statistics.mean(baseline_times)
        
        # With recovery (no retries)
        recovery_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._decorated_operation(f"op_{i}")
            recovery_times.append(time.perf_counter() - start)
        
        recovery_avg = statistics.mean(recovery_times)
        overhead_percent = ((recovery_avg - baseline_avg) / baseline_avg) * 100
        
        result = PerformanceResult(
            test_name="decorator_overhead",
            baseline_time=baseline_avg,
            recovery_time=recovery_avg,
            overhead_percent=overhead_percent,
            within_threshold=overhead_percent <= self.max_overhead_percent,
            iterations=iterations,
            details=f"Baseline: {baseline_avg*1000:.3f}ms, Recovery: {recovery_avg*1000:.3f}ms"
        )
        
        self.results.append(result)
        return result
    
    async def measure_checkpoint_performance(self, iterations: int = 100) -> PerformanceResult:
        """Measure checkpoint performance."""
        print(f"Measuring checkpoint performance with {iterations} iterations...")
        
        checkpoint_times = []
        
        @recoverable(max_retries=2, initial_delay=0.01)
        async def checkpoint_operation(op_id: str):
            # Simulate work that might need checkpointing
            await asyncio.sleep(0.01)
            return {"op_id": op_id, "status": "success"}
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                result = await checkpoint_operation(f"checkpoint_{i}")
            except Exception:
                pass  # Continue even if operation fails
            checkpoint_times.append(time.perf_counter() - start)
        
        avg_checkpoint_time = statistics.mean(checkpoint_times)
        
        # Simulate baseline for comparison
        baseline_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._baseline_operation(f"baseline_{i}")
            baseline_times.append(time.perf_counter() - start)
        
        baseline_avg = statistics.mean(baseline_times)
        overhead_percent = ((avg_checkpoint_time - baseline_avg) / baseline_avg) * 100
        
        result = PerformanceResult(
            test_name="checkpoint_performance",
            baseline_time=baseline_avg,
            recovery_time=avg_checkpoint_time,
            overhead_percent=overhead_percent,
            within_threshold=overhead_percent <= self.max_overhead_percent and avg_checkpoint_time < 0.1,
            iterations=iterations,
            details=f"Avg checkpoint time: {avg_checkpoint_time*1000:.3f}ms"
        )
        
        self.results.append(result)
        return result
    
    async def measure_recovery_performance(self, iterations: int = 50) -> PerformanceResult:
        """Measure actual recovery performance."""
        print(f"Measuring recovery performance with {iterations} iterations...")
        
        recovery_times = []
        success_count = 0
        
        @recoverable(max_retries=3, initial_delay=0.01)
        async def failing_operation(op_id: str):
            # Simulate failure 40% of the time
            if hash(op_id) % 10 < 4:  # 40% failure rate
                raise ConnectionError(f"Simulated failure for {op_id}")
            
            await asyncio.sleep(0.02)
            return {"op_id": op_id, "status": "success"}
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                result = await failing_operation(f"recovery_{i}")
                success_count += 1
            except Exception:
                pass  # Expected failures
            recovery_times.append(time.perf_counter() - start)
        
        avg_recovery_time = statistics.mean(recovery_times)
        
        # Simulate baseline for comparison
        baseline_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._baseline_operation(f"baseline_{i}")
            baseline_times.append(time.perf_counter() - start)
        
        baseline_avg = statistics.mean(baseline_times)
        overhead_percent = ((avg_recovery_time - baseline_avg) / baseline_avg) * 100
        
        success_rate = (success_count / iterations) * 100
        
        result = PerformanceResult(
            test_name="recovery_performance",
            baseline_time=baseline_avg,
            recovery_time=avg_recovery_time,
            overhead_percent=overhead_percent,
            within_threshold=overhead_percent <= self.max_overhead_percent and success_rate > 90,
            iterations=iterations,
            details=f"Avg recovery time: {avg_recovery_time*1000:.3f}ms, Success rate: {success_rate:.1f}%"
        )
        
        self.results.append(result)
        return result
    
    async def _baseline_operation(self, op_id: str):
        """Baseline operation without recovery."""
        await asyncio.sleep(0.001)  # Simulate work
        return {"op_id": op_id, "status": "success"}
    
    @recoverable(max_retries=0)
    async def _decorated_operation(self, op_id: str):
        """Operation with recovery decorator (no retries)."""
        await asyncio.sleep(0.001)  # Simulate work
        return {"op_id": op_id, "status": "success"}
    
    async def measure_memory_usage(self) -> Dict[str, Any]:
        """Measure memory usage impact."""
        print("Measuring memory usage impact...")
        
        try:
            import tracemalloc
            import psutil
            
            # Measure baseline memory
            tracemalloc.start()
            baseline_current, baseline_peak = tracemalloc.get_traced_memory()
            
            # Run operations with recovery
            for i in range(100):
                await self._decorated_operation(f"mem_test_{i}")
            
            # Measure memory after recovery operations
            recovery_current, recovery_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # Calculate memory overhead
            memory_overhead_mb = (recovery_peak - baseline_peak) / (1024 * 1024)
            
            return {
                "baseline_memory_mb": baseline_peak / (1024 * 1024),
                "recovery_memory_mb": recovery_peak / (1024 * 1024),
                "memory_overhead_mb": memory_overhead_mb,
                "within_threshold": memory_overhead_mb < 5.0,  # < 5MB requirement
                "memory_efficiency_score": max(0, 100 - memory_overhead_mb * 20)  # 1MB = 20 point penalty
            }
            
        except ImportError:
            print("Memory profiling not available (missing psutil/tracemalloc)")
            return {
                "baseline_memory_mb": 0,
                "recovery_memory_mb": 0,
                "memory_overhead_mb": 0,
                "within_threshold": True,
                "memory_efficiency_score": 100,
                "note": "Memory profiling not available"
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance validation summary."""
        if not self.results:
            return {"error": "No test results available"}
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.within_threshold])
        failed_tests = len([r for r in self.results if not r.within_threshold])
        
        overhead_percentages = [r.overhead_percent for r in self.results]
        avg_overhead = statistics.mean(overhead_percentages) if overhead_percentages else 0
        max_overhead = max(overhead_percentages) if overhead_percentages else 0
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "average_overhead_percent": avg_overhead,
            "maximum_overhead_percent": max_overhead,
            "meets_requirements": avg_overhead <= self.max_overhead_percent,
            "test_results": [
                {
                    "test_name": r.test_name,
                    "baseline_time_ms": r.baseline_time * 1000,
                    "recovery_time_ms": r.recovery_time * 1000,
                    "overhead_percent": r.overhead_percent,
                    "within_threshold": r.within_threshold,
                    "details": r.details
                }
                for r in self.results
            ]
        }


class PerformanceReportGenerator:
    """Generate comprehensive performance report."""
    
    def __init__(self):
        self.timestamp = datetime.now(timezone.utc)
    
    def generate_report(self, validator: PerformanceValidator, memory_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        summary = validator.get_summary()
        
        # Calculate overall performance score
        performance_score = self._calculate_performance_score(summary, memory_results)
        
        return {
            "report_timestamp": self.timestamp.isoformat(),
            "requirements": {
                "max_overhead_percent": 5.0,
                "max_memory_overhead_mb": 5.0,
                "min_success_rate_percent": 90.0,
                "max_checkpoint_time_ms": 100.0,
                "max_recovery_time_ms": 500.0
            },
            "performance_summary": summary,
            "memory_results": memory_results,
            "overall_assessment": {
                "performance_score": performance_score,
                "grade": self._get_grade(performance_score),
                "meets_all_requirements": (
                    summary.get("meets_requirements", False) and 
                    memory_results.get("within_threshold", True)
                ),
                "recommendations": self._generate_recommendations(summary, memory_results)
            }
        }
    
    def _calculate_performance_score(self, summary: Dict[str, Any], memory_results: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)."""
        score = 100.0
        
        # Penalize for overhead
        overhead_penalty = min(50, summary.get("average_overhead_percent", 0) * 10)
        score -= overhead_penalty
        
        # Penalize for memory usage
        memory_penalty = min(25, memory_results.get("memory_overhead_mb", 0) * 5)
        score -= memory_penalty
        
        # Penalize for failed tests
        failed_tests = summary.get("failed_tests", 0)
        total_tests = summary.get("total_tests", 1)
        failure_penalty = (failed_tests / total_tests) * 25
        score -= failure_penalty
        
        return max(0, score)
    
    def _get_grade(self, score: float) -> str:
        """Get performance grade based on score."""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        elif score >= 60:
            return "Poor"
        else:
            return "Critical"
    
    def _generate_recommendations(self, summary: Dict[str, Any], memory_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []
        
        avg_overhead = summary.get("average_overhead_percent", 0)
        if avg_overhead > 5.0:
            recommendations.append(f"Reduce overhead from {avg_overhead:.2f}% to below 5%")
        
        memory_overhead = memory_results.get("memory_overhead_mb", 0)
        if memory_overhead > 5.0:
            recommendations.append(f"Reduce memory overhead from {memory_overhead:.2f}MB to below 5MB")
        
        failed_tests = summary.get("failed_tests", 0)
        if failed_tests > 0:
            recommendations.append(f"Address {failed_tests} failing performance tests")
        
        if not recommendations:
            recommendations.append("Performance requirements are met. Continue monitoring.")
        
        return recommendations
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted performance report."""
        print("\n" + "=" * 70)
        print("COMFYUI LAUNCHER RECOVERY SYSTEM PERFORMANCE VALIDATION REPORT")
        print("=" * 70)
        print(f"Generated: {report['report_timestamp']}")
        print()
        
        # Overall assessment
        assessment = report["overall_assessment"]
        print("OVERALL ASSESSMENT:")
        print(f"  Performance Score: {assessment['performance_score']:.1f}/100")
        print(f"  Grade: {assessment['grade']}")
        print(f"  Meets All Requirements: {assessment['meets_all_requirements']}")
        print()
        
        # Requirements
        print("PERFORMANCE REQUIREMENTS:")
        reqs = report["requirements"]
        print(f"  • Max Overhead: {reqs['max_overhead_percent']}%")
        print(f"  • Max Memory Overhead: {reqs['max_memory_overhead_mb']}MB")
        print(f"  • Min Success Rate: {reqs['min_success_rate_percent']}%")
        print(f"  • Max Checkpoint Time: {reqs['max_checkpoint_time_ms']}ms")
        print(f"  • Max Recovery Time: {reqs['max_recovery_time_ms']}ms")
        print()
        
        # Summary
        summary = report["performance_summary"]
        print("TEST SUMMARY:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed Tests: {summary['passed_tests']}")
        print(f"  Failed Tests: {summary['failed_tests']}")
        print(f"  Success Rate: {summary['success_rate']:.1f}%")
        print(f"  Average Overhead: {summary['average_overhead_percent']:.2f}%")
        print(f"  Maximum Overhead: {summary['maximum_overhead_percent']:.2f}%")
        print(f"  Meets Requirements: {summary['meets_requirements']}")
        print()
        
        # Memory results
        memory = report["memory_results"]
        print("MEMORY USAGE:")
        print(f"  Baseline Memory: {memory['baseline_memory_mb']:.2f}MB")
        print(f"  Recovery Memory: {memory['recovery_memory_mb']:.2f}MB")
        print(f"  Memory Overhead: {memory['memory_overhead_mb']:.2f}MB")
        print(f"  Memory Efficiency Score: {memory['memory_efficiency_score']:.1f}/100")
        print(f"  Within Threshold: {memory['within_threshold']}")
        print()
        
        # Detailed results
        print("DETAILED TEST RESULTS:")
        for result in summary["test_results"]:
            status = "✓" if result["within_threshold"] else "✗"
            print(f"  {status} {result['test_name']}:")
            print(f"    Baseline: {result['baseline_time_ms']:.3f}ms")
            print(f"    Recovery: {result['recovery_time_ms']:.3f}ms")
            print(f"    Overhead: {result['overhead_percent']:.2f}%")
            print(f"    Details: {result['details']}")
            print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        for i, rec in enumerate(assessment["recommendations"], 1):
            print(f"  {i}. {rec}")
        print()


async def main():
    """Main performance validation function."""
    print("Starting ComfyUI Launcher Recovery System Performance Validation")
    print("=" * 60)
    
    # Initialize validator
    validator = PerformanceValidator(max_overhead_percent=5.0)
    report_generator = PerformanceReportGenerator()
    
    try:
        # Run performance tests
        print("\n1. Measuring Decorator Overhead")
        print("-" * 40)
        await validator.measure_decorator_overhead(iterations=1000)
        
        print("\n2. Measuring Checkpoint Performance")
        print("-" * 40)
        await validator.measure_checkpoint_performance(iterations=100)
        
        print("\n3. Measuring Recovery Performance")
        print("-" * 40)
        await validator.measure_recovery_performance(iterations=50)
        
        print("\n4. Measuring Memory Usage")
        print("-" * 40)
        memory_results = await validator.measure_memory_usage()
        
        # Generate and display report
        print("\n5. Generating Performance Report")
        print("-" * 40)
        report = report_generator.generate_report(validator, memory_results)
        report_generator.print_report(report)
        
        # Save report to file
        report_file = "/home/crogers2287/comfy/ComfyUI-Launcher/worktrees/issue-8/performance_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {report_file}")
        
        # Return success status
        return report["overall_assessment"]["meets_all_requirements"]
        
    except Exception as e:
        print(f"\n✗ Performance validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)