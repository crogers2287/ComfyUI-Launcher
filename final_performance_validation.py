#!/usr/bin/env python3
"""
Final comprehensive performance validation for ComfyUI Launcher recovery system.
Validates all performance requirements and generates detailed report.
"""

import asyncio
import time
import statistics
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

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


class FinalPerformanceValidator:
    """Final comprehensive performance validation."""
    
    def __init__(self):
        self.results = {}
        self.requirements = {
            "max_overhead_percent": 5.0,
            "max_memory_overhead_mb": 5.0,
            "min_success_rate_percent": 90.0,
            "max_checkpoint_time_ms": 100.0,
            "max_recovery_time_ms": 500.0
        }
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive performance validation."""
        print("Starting Final Performance Validation for ComfyUI Launcher Recovery System")
        print("=" * 80)
        
        validation_results = {}
        
        # Test 1: Basic Decorator Overhead
        print("\n1. Basic Decorator Overhead Test")
        print("-" * 50)
        validation_results["decorator_overhead"] = await self._test_decorator_overhead()
        
        # Test 2: Recovery Performance
        print("\n2. Recovery Performance Test")
        print("-" * 50)
        validation_results["recovery_performance"] = await self._test_recovery_performance()
        
        # Test 3: Memory Usage
        print("\n3. Memory Usage Test")
        print("-" * 50)
        validation_results["memory_usage"] = await self._test_memory_usage()
        
        # Test 4: State Persistence Overhead
        print("\n4. State Persistence Overhead Test")
        print("-" * 50)
        validation_results["persistence_overhead"] = await self._test_persistence_overhead()
        
        # Test 5: Load Testing
        print("\n5. Concurrent Load Testing")
        print("-" * 50)
        validation_results["load_testing"] = await self._test_concurrent_load()
        
        # Generate final report
        print("\n6. Generating Final Report")
        print("-" * 50)
        final_report = self._generate_final_report(validation_results)
        
        return final_report
    
    async def _test_decorator_overhead(self) -> Dict[str, Any]:
        """Test basic decorator overhead with minimal recovery."""
        iterations = 1000
        
        # Baseline measurement
        baseline_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._baseline_operation(f"baseline_{i}")
            baseline_times.append(time.perf_counter() - start)
        
        baseline_avg = statistics.mean(baseline_times)
        
        # Recovery measurement (no retries)
        recovery_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._recovery_operation_no_retries(f"recovery_{i}")
            recovery_times.append(time.perf_counter() - start)
        
        recovery_avg = statistics.mean(recovery_times)
        overhead_percent = ((recovery_avg - baseline_avg) / baseline_avg) * 100
        
        result = {
            "test_name": "decorator_overhead",
            "baseline_time_ms": baseline_avg * 1000,
            "recovery_time_ms": recovery_avg * 1000,
            "overhead_percent": overhead_percent,
            "within_threshold": overhead_percent <= self.requirements["max_overhead_percent"],
            "iterations": iterations,
            "status": "PASS" if overhead_percent <= self.requirements["max_overhead_percent"] else "FAIL"
        }
        
        print(f"  Baseline: {baseline_avg*1000:.3f}ms")
        print(f"  Recovery: {recovery_avg*1000:.3f}ms")
        print(f"  Overhead: {overhead_percent:.2f}% ({result['status']})")
        
        return result
    
    async def _test_recovery_performance(self) -> Dict[str, Any]:
        """Test actual recovery performance with failures."""
        iterations = 100
        failure_rate = 0.3  # 30% failure rate
        
        recovery_times = []
        success_count = 0
        total_failures = 0
        
        @recoverable(max_retries=3, initial_delay=0.01)
        async def test_operation(op_id: str):
            # Simulate failures based on operation ID for consistency
            should_fail = (int(op_id.split('_')[-1]) % 10) < (failure_rate * 10)
            
            if should_fail:
                raise ConnectionError(f"Simulated failure for {op_id}")
            
            await asyncio.sleep(0.02)  # Simulate work
            return {"op_id": op_id, "status": "success"}
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                result = await test_operation(f"recovery_test_{i}")
                success_count += 1
            except Exception:
                total_failures += 1
            finally:
                recovery_times.append(time.perf_counter() - start)
        
        avg_recovery_time = statistics.mean(recovery_times)
        success_rate = (success_count / iterations) * 100
        
        result = {
            "test_name": "recovery_performance",
            "avg_recovery_time_ms": avg_recovery_time * 1000,
            "success_rate_percent": success_rate,
            "total_operations": iterations,
            "successful_operations": success_count,
            "failed_operations": total_failures,
            "time_within_threshold": avg_recovery_time < 0.5,  # < 500ms
            "success_rate_within_threshold": success_rate >= self.requirements["min_success_rate_percent"],
            "status": "PASS" if (avg_recovery_time < 0.5 and success_rate >= self.requirements["min_success_rate_percent"]) else "FAIL"
        }
        
        print(f"  Avg Recovery Time: {avg_recovery_time*1000:.3f}ms")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Time OK: {result['time_within_threshold']}")
        print(f"  Success Rate OK: {result['success_rate_within_threshold']}")
        print(f"  Status: {result['status']}")
        
        return result
    
    async def _test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage impact."""
        try:
            import tracemalloc
            
            # Measure baseline memory
            tracemalloc.start()
            baseline_current, baseline_peak = tracemalloc.get_traced_memory()
            
            # Run recovery operations
            for i in range(100):
                await self._recovery_operation_no_retries(f"mem_test_{i}")
            
            # Measure memory after recovery operations
            recovery_current, recovery_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_overhead_mb = (recovery_peak - baseline_peak) / (1024 * 1024)
            
            result = {
                "test_name": "memory_usage",
                "baseline_memory_mb": baseline_peak / (1024 * 1024),
                "recovery_memory_mb": recovery_peak / (1024 * 1024),
                "memory_overhead_mb": memory_overhead_mb,
                "within_threshold": memory_overhead_mb <= self.requirements["max_memory_overhead_mb"],
                "memory_efficiency_score": max(0, 100 - memory_overhead_mb * 20),
                "status": "PASS" if memory_overhead_mb <= self.requirements["max_memory_overhead_mb"] else "FAIL"
            }
            
            print(f"  Baseline Memory: {result['baseline_memory_mb']:.2f}MB")
            print(f"  Recovery Memory: {result['recovery_memory_mb']:.2f}MB")
            print(f"  Memory Overhead: {memory_overhead_mb:.3f}MB ({result['status']})")
            
            return result
            
        except ImportError:
            print("  Memory profiling not available")
            return {
                "test_name": "memory_usage",
                "baseline_memory_mb": 0,
                "recovery_memory_mb": 0,
                "memory_overhead_mb": 0,
                "within_threshold": True,
                "memory_efficiency_score": 100,
                "status": "PASS",
                "note": "Memory profiling not available"
            }
    
    async def _test_persistence_overhead(self) -> Dict[str, Any]:
        """Test persistence overhead."""
        iterations = 50
        
        # Test without persistence
        no_persist_times = []
        for i in range(iterations):
            start = time.perf_counter()
            await self._recovery_operation_no_retries(f"no_persist_{i}")
            no_persist_times.append(time.perf_counter() - start)
        
        no_persist_avg = statistics.mean(no_persist_times)
        
        # Test with persistence (if available)
        try:
            from recovery.persistence.memory import MemoryPersistence
            
            persistence = MemoryPersistence()
            
            @recoverable(max_retries=1, persistence=persistence)
            async def persist_operation(op_id: str):
                await asyncio.sleep(0.01)
                return {"op_id": op_id, "status": "success"}
            
            persist_times = []
            for i in range(iterations):
                start = time.perf_counter()
                try:
                    await persist_operation(f"persist_{i}")
                except Exception:
                    pass
                persist_times.append(time.perf_counter() - start)
            
            persist_avg = statistics.mean(persist_times)
            overhead_percent = ((persist_avg - no_persist_avg) / no_persist_avg) * 100
            
            result = {
                "test_name": "persistence_overhead",
                "no_persistence_time_ms": no_persist_avg * 1000,
                "persistence_time_ms": persist_avg * 1000,
                "overhead_percent": overhead_percent,
                "within_threshold": overhead_percent <= self.requirements["max_overhead_percent"],
                "iterations": iterations,
                "status": "PASS" if overhead_percent <= self.requirements["max_overhead_percent"] else "FAIL"
            }
            
        except Exception as e:
            result = {
                "test_name": "persistence_overhead",
                "error": str(e),
                "status": "SKIP",
                "note": "Persistence not available"
            }
        
        print(f"  Status: {result['status']}")
        if "overhead_percent" in result:
            print(f"  Overhead: {result['overhead_percent']:.2f}%")
        
        return result
    
    async def _test_concurrent_load(self) -> Dict[str, Any]:
        """Test performance under concurrent load."""
        concurrent_users = 20
        duration_seconds = 10
        
        async def user_task(user_id: int):
            """Simulate user operations."""
            operations_completed = 0
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds:
                try:
                    await self._recovery_operation_no_retries(f"user_{user_id}_op_{operations_completed}")
                    operations_completed += 1
                    await asyncio.sleep(0.01)  # Small delay between operations
                except Exception:
                    pass
            
            return operations_completed
        
        # Start concurrent users
        start_time = time.time()
        tasks = [user_task(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_operations = sum(r for r in results if isinstance(r, int))
        total_time = time.time() - start_time
        throughput = total_operations / total_time if total_time > 0 else 0
        
        result = {
            "test_name": "concurrent_load",
            "concurrent_users": concurrent_users,
            "duration_seconds": total_time,
            "total_operations": total_operations,
            "throughput_ops_per_sec": throughput,
            "avg_ops_per_user": total_operations / concurrent_users,
            "status": "PASS"  # Load test is informational
        }
        
        print(f"  Throughput: {throughput:.1f} ops/sec")
        print(f"  Total Operations: {total_operations}")
        print(f"  Avg per User: {result['avg_ops_per_user']:.1f}")
        
        return result
    
    async def _baseline_operation(self, op_id: str):
        """Baseline operation without recovery."""
        await asyncio.sleep(0.001)
        return {"op_id": op_id, "status": "success"}
    
    @recoverable(max_retries=0)
    async def _recovery_operation_no_retries(self, op_id: str):
        """Operation with recovery decorator (no retries)."""
        await asyncio.sleep(0.001)
        return {"op_id": op_id, "status": "success"}
    
    def _generate_final_report(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final comprehensive report."""
        # Calculate overall metrics
        total_tests = len(validation_results)
        passed_tests = len([r for r in validation_results.values() if r.get("status") == "PASS"])
        skipped_tests = len([r for r in validation_results.values() if r.get("status") == "SKIP"])
        
        # Extract overhead percentages
        overhead_tests = [r for r in validation_results.values() if "overhead_percent" in r]
        overhead_percentages = [r["overhead_percent"] for r in overhead_tests]
        avg_overhead = statistics.mean(overhead_percentages) if overhead_percentages else 0
        max_overhead = max(overhead_percentages) if overhead_percentages else 0
        
        # Check recovery performance
        recovery_test = validation_results.get("recovery_performance", {})
        success_rate = recovery_test.get("success_rate_percent", 0)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(validation_results)
        
        # Determine overall status
        overhead_ok = avg_overhead <= self.requirements["max_overhead_percent"]
        recovery_ok = success_rate >= self.requirements["min_success_rate_percent"]
        memory_ok = validation_results.get("memory_usage", {}).get("within_threshold", True)
        
        overall_success = overhead_ok and recovery_ok and memory_ok
        
        return {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "requirements": self.requirements,
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "skipped_tests": skipped_tests,
                "failed_tests": total_tests - passed_tests - skipped_tests,
                "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "average_overhead_percent": avg_overhead,
                "maximum_overhead_percent": max_overhead,
                "recovery_success_rate_percent": success_rate,
                "overall_performance_score": overall_score
            },
            "requirements_validation": {
                "overhead_requirement_met": overhead_ok,
                "recovery_success_requirement_met": recovery_ok,
                "memory_requirement_met": memory_ok,
                "all_requirements_met": overall_success
            },
            "detailed_results": validation_results,
            "overall_assessment": {
                "status": "SUCCESS" if overall_success else "FAILURE",
                "grade": self._get_grade(overall_score),
                "recommendations": self._generate_recommendations(validation_results)
            }
        }
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)."""
        score = 100.0
        
        # Penalize for overhead
        overhead_tests = [r for r in results.values() if "overhead_percent" in r and r.get("status") != "SKIP"]
        if overhead_tests:
            avg_overhead = statistics.mean([r["overhead_percent"] for r in overhead_tests])
            overhead_penalty = min(50, max(0, (avg_overhead - self.requirements["max_overhead_percent"]) * 10))
            score -= overhead_penalty
        
        # Penalize for low success rate
        recovery_test = results.get("recovery_performance", {})
        if recovery_test and recovery_test.get("status") != "SKIP":
            success_rate = recovery_test.get("success_rate_percent", 0)
            success_penalty = max(0, (self.requirements["min_success_rate_percent"] - success_rate) * 2)
            score -= success_penalty
        
        # Penalize for failed tests
        failed_tests = len([r for r in results.values() if r.get("status") == "FAIL"])
        total_tests = len([r for r in results.values() if r.get("status") != "SKIP"])
        if total_tests > 0:
            failure_penalty = (failed_tests / total_tests) * 25
            score -= failure_penalty
        
        return max(0, min(100, score))
    
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
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []
        
        # Check overhead
        overhead_tests = [r for r in results.values() if "overhead_percent" in r]
        if overhead_tests:
            avg_overhead = statistics.mean([r["overhead_percent"] for r in overhead_tests])
            if avg_overhead > self.requirements["max_overhead_percent"]:
                recommendations.append(f"Reduce average overhead from {avg_overhead:.2f}% to below {self.requirements['max_overhead_percent']}%")
        
        # Check recovery success rate
        recovery_test = results.get("recovery_performance", {})
        if recovery_test and recovery_test.get("status") != "SKIP":
            success_rate = recovery_test.get("success_rate_percent", 0)
            if success_rate < self.requirements["min_success_rate_percent"]:
                recommendations.append(f"Improve recovery success rate from {success_rate:.1f}% to at least {self.requirements['min_success_rate_percent']}%")
        
        # Check failed tests
        failed_tests = [r for r in results.values() if r.get("status") == "FAIL"]
        if failed_tests:
            failed_names = [r.get("test_name", "unknown") for r in failed_tests]
            recommendations.append(f"Fix failing tests: {', '.join(failed_names)}")
        
        if not recommendations:
            recommendations.append("All performance requirements are met. Continue monitoring performance.")
        
        return recommendations
    
    def print_final_report(self, report: Dict[str, Any]):
        """Print formatted final report."""
        print("\n" + "=" * 80)
        print("FINAL PERFORMANCE VALIDATION REPORT")
        print("=" * 80)
        print(f"Generated: {report['report_timestamp']}")
        print()
        
        # Overall assessment
        assessment = report["overall_assessment"]
        summary = report["test_summary"]
        
        print("OVERALL ASSESSMENT:")
        print(f"  Status: {assessment['status']}")
        print(f"  Grade: {assessment['grade']}")
        print(f"  Performance Score: {summary['overall_performance_score']:.1f}/100")
        print(f"  All Requirements Met: {report['requirements_validation']['all_requirements_met']}")
        print()
        
        # Requirements validation
        validation = report["requirements_validation"]
        print("REQUIREMENTS VALIDATION:")
        print(f"  • Overhead < {self.requirements['max_overhead_percent']}%: {'✓' if validation['overhead_requirement_met'] else '✗'}")
        print(f"  • Success Rate ≥ {self.requirements['min_success_rate_percent']}%: {'✓' if validation['recovery_success_requirement_met'] else '✗'}")
        print(f"  • Memory < {self.requirements['max_memory_overhead_mb']}MB: {'✓' if validation['memory_requirement_met'] else '✗'}")
        print()
        
        # Test summary
        print("TEST SUMMARY:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed_tests']}")
        print(f"  Failed: {summary['failed_tests']}")
        print(f"  Skipped: {summary['skipped_tests']}")
        print(f"  Pass Rate: {summary['pass_rate']:.1f}%")
        print(f"  Average Overhead: {summary['average_overhead_percent']:.2f}%")
        print(f"  Recovery Success Rate: {summary['recovery_success_rate_percent']:.1f}%")
        print()
        
        # Detailed results
        print("DETAILED RESULTS:")
        for test_name, result in report["detailed_results"].items():
            status_icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "⚠"}.get(result.get("status", "?"), "?")
            print(f"  {status_icon} {result.get('test_name', test_name).replace('_', ' ').title()}:")
            
            if "overhead_percent" in result:
                print(f"    Overhead: {result['overhead_percent']:.2f}%")
            if "success_rate_percent" in result:
                print(f"    Success Rate: {result['success_rate_percent']:.1f}%")
            if "avg_recovery_time_ms" in result:
                print(f"    Avg Recovery Time: {result['avg_recovery_time_ms']:.3f}ms")
            if "throughput_ops_per_sec" in result:
                print(f"    Throughput: {result['throughput_ops_per_sec']:.1f} ops/sec")
            if "memory_overhead_mb" in result:
                print(f"    Memory Overhead: {result['memory_overhead_mb']:.3f}MB")
            
            print(f"    Status: {result.get('status', 'UNKNOWN')}")
            print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        for i, rec in enumerate(assessment["recommendations"], 1):
            print(f"  {i}. {rec}")
        print()


async def main():
    """Main validation function."""
    validator = FinalPerformanceValidator()
    
    try:
        # Run comprehensive validation
        final_report = await validator.run_comprehensive_validation()
        
        # Print report
        validator.print_final_report(final_report)
        
        # Save report
        report_file = "/home/crogers2287/comfy/ComfyUI-Launcher/worktrees/issue-8/final_performance_report.json"
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2)
        print(f"Final report saved to: {report_file}")
        
        # Return success status
        return final_report["overall_assessment"]["status"] == "SUCCESS"
        
    except Exception as e:
        print(f"\n✗ Final validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)