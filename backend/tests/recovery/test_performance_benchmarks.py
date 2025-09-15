"""
Performance benchmarks and load tests for ComfyUI Launcher recovery system.

These tests measure the performance impact of recovery mechanisms under various load conditions:
1. Recovery system overhead measurement
2. Concurrent operation scaling
3. Memory usage analysis
4. Network performance under load
5. Recovery strategy performance comparison
"""

import asyncio
import pytest
import time
import json
import psutil
import threading
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
import asyncio
import tracemalloc
import memory_profiler

# Import recovery components
from backend.src.recovery import recoverable, RecoveryConfig, RecoveryExhaustedError
from backend.src.recovery.persistence import MemoryPersistence, SQLAlchemyPersistence
from backend.src.recovery.strategies import (
    ExponentialBackoffStrategy, LinearBackoffStrategy, 
    FixedDelayStrategy, CustomStrategy
)
from backend.src.recovery.classification import ErrorClassifier


@dataclass
class PerformanceMetrics:
    """Performance metrics for recovery operations."""
    operation_name: str
    execution_time: float
    recovery_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    retry_attempts: int
    success: bool
    overhead_percentage: float
    timestamp: datetime
    
    def to_dict(self):
        return asdict(self)


class PerformanceBenchmark:
    """Benchmark for measuring recovery system performance."""
    
    def __init__(self):
        self.metrics = []
        self.memory_snapshots = []
        self.cpu_samples = []
        
    async def measure_overhead(self, iterations: int = 1000) -> Dict[str, float]:
        """Measure the overhead introduced by the recovery system."""
        
        # Baseline measurement without recovery
        @recoverable(max_retries=0)
        async def operation_with_recovery(data_size: int):
            return {"processed": data_size}
        
        async def operation_without_recovery(data_size: int):
            return {"processed": data_size}
        
        # Measure baseline performance
        baseline_times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            await operation_without_recovery(1000)
            baseline_times.append(time.perf_counter() - start_time)
        
        baseline_avg = statistics.mean(baseline_times)
        
        # Measure performance with recovery (no retries)
        recovery_times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            await operation_with_recovery(1000)
            recovery_times.append(time.perf_counter() - start_time)
        
        recovery_avg = statistics.mean(recovery_times)
        
        # Calculate overhead
        overhead_percentage = ((recovery_avg - baseline_avg) / baseline_avg) * 100
        
        return {
            "baseline_avg_ms": baseline_avg * 1000,
            "recovery_avg_ms": recovery_avg * 1000,
            "overhead_percentage": overhead_percentage,
            "iterations": iterations
        }
    
    async def benchmark_recovery_strategies(self, 
                                         failure_rate: float = 0.3,
                                         iterations: int = 100) -> Dict[str, Any]:
        """Benchmark different recovery strategies."""
        
        strategies = {
            "exponential": ExponentialBackoffStrategy(initial_delay=0.01, max_delay=0.5),
            "linear": LinearBackoffStrategy(delay_increment=0.01, max_delay=0.5),
            "fixed": FixedDelayStrategy(delay=0.1),
            "custom_fibonacci": CustomStrategy(
                delay_func=lambda attempt: min(0.1 * self._fibonacci(attempt), 1.0),
                name="Fibonacci"
            )
        }
        
        results = {}
        
        for strategy_name, strategy in strategies.items():
            attempt_times = []
            success_count = 0
            
            @recoverable(
                max_retries=3,
                strategy=strategy
            )
            async def benchmark_operation(operation_id: str):
                # Simulate failure based on rate
                if hash(operation_id) % 100 < int(failure_rate * 100):
                    raise ConnectionError(f"Simulated failure for {operation_id}")
                
                return {"status": "success", "operation_id": operation_id}
            
            # Run benchmark
            for i in range(iterations):
                start_time = time.perf_counter()
                try:
                    result = await benchmark_operation(f"op_{strategy_name}_{i}")
                    success_count += 1
                except RecoveryExhaustedError:
                    pass  # Expected failure
                finally:
                    attempt_times.append(time.perf_counter() - start_time)
            
            results[strategy_name] = {
                "success_rate": success_count / iterations * 100,
                "average_time_ms": statistics.mean(attempt_times) * 1000,
                "median_time_ms": statistics.median(attempt_times) * 1000,
                "p95_time_ms": statistics.quantiles(attempt_times, n=20)[18] * 1000,  # 95th percentile
                "total_time_ms": sum(attempt_times) * 1000
            }
        
        return results
    
    def _fibonacci(self, n: int) -> int:
        """Generate Fibonacci number for custom strategy."""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    async def benchmark_persistence_backends(self, 
                                           data_size: int = 1000,
                                           iterations: int = 500) -> Dict[str, Any]:
        """Benchmark different persistence backends."""
        
        backends = {
            "memory": MemoryPersistence(),
            "sqlite": self._create_sqlite_persistence()
        }
        
        results = {}
        
        for backend_name, backend in backends.items():
            save_times = []
            load_times = []
            memory_usage = []
            
            @recoverable(max_retries=1, persistence=backend)
            async def persistent_operation(data: Dict[str, Any]):
                return {"processed": len(data)}
            
            for i in range(iterations):
                test_data = {
                    "id": f"test_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": list(range(data_size))
                }
                
                # Measure save time
                save_start = time.perf_counter()
                await backend.save(test_data)
                save_times.append(time.perf_counter() - save_start)
                
                # Measure load time
                load_start = time.perf_counter()
                loaded_data = await backend.get(f"test_{i}")
                load_times.append(time.perf_counter() - load_start)
                
                # Measure memory usage
                if backend_name == "memory":
                    process = psutil.Process()
                    memory_info = process.memory_info()
                    memory_usage.append(memory_info.rss / 1024 / 1024)  # MB
            
            results[backend_name] = {
                "average_save_time_ms": statistics.mean(save_times) * 1000,
                "average_load_time_ms": statistics.mean(load_times) * 1000,
                "average_memory_mb": statistics.mean(memory_usage) if memory_usage else 0,
                "total_operations": iterations
            }
            
            # Cleanup
            if backend_name == "sqlite":
                await backend.close()
        
        return results
    
    def _create_sqlite_persistence(self):
        """Create SQLite persistence for testing."""
        import tempfile
        import os
        
        db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        db_path = db_file.name
        db_file.close()
        
        persistence = SQLAlchemyPersistence(f"sqlite+aiosqlite:///{db_path}")
        return persistence


class LoadTestRunner:
    """Runner for load testing recovery scenarios."""
    
    def __init__(self):
        self.results = []
        self.system_monitor = SystemMonitor()
        
    async def run_concurrent_load_test(self, 
                                     concurrent_users: int = 50,
                                     duration_seconds: int = 30,
                                     failure_rate: float = 0.1) -> Dict[str, Any]:
        """Run concurrent load test with recovery."""
        
        print(f"Starting concurrent load test: {concurrent_users} users for {duration_seconds}s")
        
        # Start system monitoring
        await self.system_monitor.start_monitoring()
        
        # Track metrics
        successful_operations = 0
        failed_operations = 0
        recovery_attempts = 0
        operation_times = []
        
        # Create concurrent user tasks
        user_tasks = []
        
        async def user_simulation(user_id: int):
            nonlocal successful_operations, failed_operations, recovery_attempts
            
            start_time = time.time()
            user_successful = 0
            user_failed = 0
            user_recoveries = 0
            
            @recoverable(max_retries=2, initial_delay=0.1)
            async def user_operation():
                nonlocal user_recoveries
                
                # Simulate failure based on rate
                if time.time() - start_time < duration_seconds:
                    if hash(f"{user_id}_{time.time()}") % 100 < int(failure_rate * 100):
                        user_recoveries += 1
                        raise ConnectionError(f"User {user_id} operation failed")
                    
                    await asyncio.sleep(0.05)  # Simulate work
                    user_successful += 1
                    return {"user_id": user_id, "status": "success"}
                
                return {"user_id": user_id, "status": "timeout"}
            
            # Run operations for duration
            while time.time() - start_time < duration_seconds:
                op_start = time.perf_counter()
                try:
                    result = await user_operation()
                    if result["status"] == "success":
                        operation_times.append(time.perf_counter() - op_start)
                except RecoveryExhaustedError:
                    user_failed += 1
                except asyncio.TimeoutError:
                    break
                
                await asyncio.sleep(0.1)  # Small delay between operations
            
            # Update totals
            successful_operations += user_successful
            failed_operations += user_failed
            recovery_attempts += user_recoveries
            
            return {
                "user_id": user_id,
                "successful_operations": user_successful,
                "failed_operations": user_failed,
                "recovery_attempts": user_recoveries
            }
        
        # Start all users
        for user_id in range(concurrent_users):
            user_tasks.append(user_simulation(user_id))
        
        # Wait for all users to complete
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Stop monitoring
        await self.system_monitor.stop_monitoring()
        system_metrics = self.system_monitor.get_metrics()
        
        # Calculate metrics
        total_operations = successful_operations + failed_operations
        success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
        avg_operations_per_user = total_operations / concurrent_users
        
        throughput = total_operations / duration_seconds if duration_seconds > 0 else 0
        avg_response_time = statistics.mean(operation_times) * 1000 if operation_times else 0
        
        return {
            "concurrent_users": concurrent_users,
            "duration_seconds": duration_seconds,
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "recovery_attempts": recovery_attempts,
            "success_rate": success_rate,
            "throughput_ops_per_sec": throughput,
            "avg_response_time_ms": avg_response_time,
            "avg_operations_per_user": avg_operations_per_user,
            "system_metrics": system_metrics,
            "user_results": [r for r in user_results if isinstance(r, dict)]
        }
    
    async def run_scaling_test(self, 
                            start_users: int = 10,
                            max_users: int = 200,
                            user_increment: int = 20,
                            duration_per_test: int = 10) -> Dict[str, Any]:
        """Run scaling test to determine system limits."""
        
        scaling_results = []
        
        for user_count in range(start_users, max_users + 1, user_increment):
            print(f"Testing with {user_count} concurrent users...")
            
            result = await self.run_concurrent_load_test(
                concurrent_users=user_count,
                duration_seconds=duration_per_test,
                failure_rate=0.05  # Lower failure rate for scaling test
            )
            
            scaling_results.append({
                "user_count": user_count,
                **{k: v for k, v in result.items() if k != "user_results"}
            })
            
            # Check if system is overloaded
            if result["success_rate"] < 80.0 or result["avg_response_time_ms"] > 1000:
                print(f"System appears overloaded at {user_count} users")
                break
        
        # Find optimal user count
        optimal_users = self._find_optimal_user_count(scaling_results)
        
        return {
            "scaling_results": scaling_results,
            "optimal_user_count": optimal_users,
            "max_tested_users": max(r["user_count"] for r in scaling_results),
            "test_configuration": {
                "start_users": start_users,
                "max_users": max_users,
                "user_increment": user_increment,
                "duration_per_test": duration_per_test
            }
        }
    
    def _find_optimal_user_count(self, results: List[Dict[str, Any]]) -> int:
        """Find optimal user count based on performance metrics."""
        if not results:
            return 0
        
        # Score each user count based on multiple factors
        scored_results = []
        
        for result in results:
            score = 0
            
            # Success rate (40% weight)
            score += result["success_rate"] * 0.4
            
            # Response time (30% weight) - lower is better
            response_score = max(0, 100 - result["avg_response_time_ms"] / 10)
            score += response_score * 0.3
            
            # Throughput (30% weight)
            throughput_score = min(100, result["throughput_ops_per_sec"] * 2)
            score += throughput_score * 0.3
            
            scored_results.append({
                "user_count": result["user_count"],
                "score": score,
                **result
            })
        
        # Find user count with highest score
        optimal = max(scored_results, key=lambda x: x["score"])
        return optimal["user_count"]
    
    async def run_failure_injection_test(self, 
                                       failure_patterns: List[str],
                                       duration_seconds: int = 20) -> Dict[str, Any]:
        """Test recovery behavior under different failure patterns."""
        
        pattern_results = {}
        
        for pattern in failure_patterns:
            print(f"Testing failure pattern: {pattern}")
            
            success_count = 0
            failure_count = 0
            recovery_count = 0
            response_times = []
            
            async def failure_injection_operation(operation_id: str):
                nonlocal recovery_count
                
                # Inject failure based on pattern
                should_fail = False
                
                if pattern == "random_10":
                    should_fail = hash(f"{operation_id}_{time.time()}") % 100 < 10
                elif pattern == "burst":
                    # Burst failures every 5 operations
                    operation_num = int(operation_id.split("_")[-1])
                    should_fail = (operation_num % 5) in [0, 1, 2]
                elif pattern == "cascading":
                    # Cascading failures
                    operation_num = int(operation_id.split("_")[-1])
                    should_fail = operation_num < 5  # First 5 operations fail
                elif pattern == "intermittent":
                    # Intermittent failures
                    operation_num = int(operation_id.split("_")[-1])
                    should_fail = operation_num % 3 == 0
                
                if should_fail:
                    recovery_count += 1
                    raise ConnectionError(f"Injected failure for {operation_id}")
                
                await asyncio.sleep(0.02)
                return {"operation_id": operation_id, "status": "success"}
            
            @recoverable(max_retries=3, initial_delay=0.05)
            async def resilient_operation(operation_id: str):
                return await failure_injection_operation(operation_id)
            
            # Run operations for duration
            start_time = time.time()
            operation_id = 0
            
            while time.time() - start_time < duration_seconds:
                op_start = time.perf_counter()
                
                try:
                    result = await resilient_operation(f"op_{operation_id}")
                    success_count += 1
                    response_times.append(time.perf_counter() - op_start)
                except RecoveryExhaustedError:
                    failure_count += 1
                
                operation_id += 1
                await asyncio.sleep(0.01)
            
            total_operations = success_count + failure_count
            success_rate = (success_count / total_operations * 100) if total_operations > 0 else 0
            
            pattern_results[pattern] = {
                "success_rate": success_rate,
                "total_operations": total_operations,
                "successful_operations": success_count,
                "failed_operations": failure_count,
                "recovery_attempts": recovery_count,
                "avg_response_time_ms": statistics.mean(response_times) * 1000 if response_times else 0,
                "operations_per_second": total_operations / duration_seconds
            }
        
        return {
            "failure_patterns_tested": failure_patterns,
            "pattern_results": pattern_results,
            "test_duration_seconds": duration_seconds
        }


class SystemMonitor:
    """Monitor system resources during testing."""
    
    def __init__(self):
        self.monitoring = False
        self.start_time = None
        self.cpu_samples = []
        self.memory_samples = []
        self.network_samples = []
        self.disk_samples = []
        self.monitor_thread = None
        
    async def start_monitoring(self):
        """Start system monitoring."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.start_time = time.time()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_system)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        print("System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system monitoring."""
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        print("System monitoring stopped")
    
    def _monitor_system(self):
        """Monitor system resources in background thread."""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = process.cpu_percent()
                self.cpu_samples.append({
                    "timestamp": time.time(),
                    "cpu_percent": cpu_percent
                })
                
                # Memory usage
                memory_info = process.memory_info()
                self.memory_samples.append({
                    "timestamp": time.time(),
                    "rss_mb": memory_info.rss / 1024 / 1024,
                    "vms_mb": memory_info.vms / 1024 / 1024
                })
                
                # Network I/O (if available)
                try:
                    net_io = psutil.net_io_counters()
                    self.network_samples.append({
                        "timestamp": time.time(),
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv
                    })
                except:
                    pass
                
                # Disk I/O (if available)
                try:
                    disk_io = psutil.disk_io_counters()
                    self.disk_samples.append({
                        "timestamp": time.time(),
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes
                    })
                except:
                    pass
                
                time.sleep(0.5)  # Sample every 500ms
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                break
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected system metrics."""
        if not self.start_time:
            return {}
        
        duration = time.time() - self.start_time
        
        # Calculate CPU metrics
        cpu_values = [s["cpu_percent"] for s in self.cpu_samples]
        cpu_metrics = {
            "average": statistics.mean(cpu_values) if cpu_values else 0,
            "max": max(cpu_values) if cpu_values else 0,
            "min": min(cpu_values) if cpu_values else 0,
            "samples": len(cpu_values)
        }
        
        # Calculate memory metrics
        memory_values = [s["rss_mb"] for s in self.memory_samples]
        memory_metrics = {
            "average_mb": statistics.mean(memory_values) if memory_values else 0,
            "max_mb": max(memory_values) if memory_values else 0,
            "min_mb": min(memory_values) if memory_values else 0,
            "samples": len(memory_values)
        }
        
        # Calculate network metrics
        if len(self.network_samples) >= 2:
            first_sample = self.network_samples[0]
            last_sample = self.network_samples[-1]
            network_metrics = {
                "bytes_sent_total": last_sample["bytes_sent"] - first_sample["bytes_sent"],
                "bytes_recv_total": last_sample["bytes_recv"] - first_sample["bytes_recv"],
                "bytes_sent_per_sec": (last_sample["bytes_sent"] - first_sample["bytes_sent"]) / duration,
                "bytes_recv_per_sec": (last_sample["bytes_recv"] - first_sample["bytes_recv"]) / duration
            }
        else:
            network_metrics = {}
        
        # Calculate disk metrics
        if len(self.disk_samples) >= 2:
            first_sample = self.disk_samples[0]
            last_sample = self.disk_samples[-1]
            disk_metrics = {
                "bytes_read_total": last_sample["read_bytes"] - first_sample["read_bytes"],
                "bytes_written_total": last_sample["write_bytes"] - first_sample["write_bytes"],
                "bytes_read_per_sec": (last_sample["read_bytes"] - first_sample["read_bytes"]) / duration,
                "bytes_written_per_sec": (last_sample["write_bytes"] - first_sample["write_bytes"]) / duration
            }
        else:
            disk_metrics = {}
        
        return {
            "duration_seconds": duration,
            "cpu_metrics": cpu_metrics,
            "memory_metrics": memory_metrics,
            "network_metrics": network_metrics,
            "disk_metrics": disk_metrics,
            "total_samples": len(self.cpu_samples)
        }


class MemoryProfiler:
    """Profile memory usage of recovery operations."""
    
    def __init__(self):
        self.snapshots = []
        
    async def profile_memory_usage(self, operation_func, iterations: int = 100) -> Dict[str, Any]:
        """Profile memory usage of recovery operations."""
        
        # Start memory tracing
        tracemalloc.start()
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        memory_samples = []
        
        for i in range(iterations):
            # Take snapshot before operation
            snapshot1 = tracemalloc.take_snapshot()
            
            # Execute operation
            try:
                await operation_func(f"memory_test_{i}")
            except:
                pass  # Continue even if operation fails
            
            # Take snapshot after operation
            snapshot2 = tracemalloc.take_snapshot()
            
            # Calculate memory difference
            memory_diff = snapshot2.compare_to(snapshot1, 'lineno')
            total_diff = sum(stat.size_diff for stat in memory_diff)
            
            memory_samples.append({
                "iteration": i,
                "memory_diff_bytes": total_diff,
                "memory_diff_mb": total_diff / 1024 / 1024
            })
        
        # Stop memory tracing
        tracemalloc.stop()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Calculate statistics
        memory_diffs = [s["memory_diff_mb"] for s in memory_samples]
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_growth_mb": final_memory - initial_memory,
            "average_memory_diff_per_operation_mb": statistics.mean(memory_diffs) if memory_diffs else 0,
            "max_memory_diff_per_operation_mb": max(memory_diffs) if memory_diffs else 0,
            "total_iterations": iterations,
            "memory_efficiency_score": self._calculate_memory_efficiency(memory_diffs)
        }
    
    def _calculate_memory_efficiency(self, memory_diffs: List[float]) -> float:
        """Calculate memory efficiency score (0-100)."""
        if not memory_diffs:
            return 100.0
        
        avg_memory_diff = statistics.mean(memory_diffs)
        
        # Lower memory usage is better (higher score)
        if avg_memory_diff < 0.01:  # Less than 10KB per operation
            return 100.0
        elif avg_memory_diff < 0.1:  # Less than 100KB per operation
            return 90.0
        elif avg_memory_diff < 1.0:  # Less than 1MB per operation
            return 75.0
        elif avg_memory_diff < 5.0:  # Less than 5MB per operation
            return 50.0
        else:
            return max(0, 25.0 - (avg_memory_diff - 5.0) * 5)


# Performance test runner
class PerformanceTestRunner:
    """Run comprehensive performance tests."""
    
    def __init__(self):
        self.benchmark = PerformanceBenchmark()
        self.load_tester = LoadTestRunner()
        self.memory_profiler = MemoryProfiler()
        self.results = {}
        
    async def run_all_performance_tests(self) -> Dict[str, Any]:
        """Run all performance tests."""
        print("Starting Comprehensive Performance Tests")
        print("=" * 60)
        
        test_results = {}
        
        # 1. Overhead benchmark
        print("\n1. Measuring Recovery System Overhead")
        print("-" * 40)
        overhead_results = await self.benchmark.measure_overhead(iterations=1000)
        test_results["overhead"] = overhead_results
        print(f"  Overhead: {overhead_results['overhead_percentage']:.2f}%")
        
        # 2. Strategy comparison
        print("\n2. Comparing Recovery Strategies")
        print("-" * 40)
        strategy_results = await self.benchmark.benchmark_recovery_strategies(
            failure_rate=0.3, iterations=200
        )
        test_results["strategies"] = strategy_results
        for strategy, metrics in strategy_results.items():
            print(f"  {strategy}: {metrics['success_rate']:.1f}% success, {metrics['average_time_ms']:.2f}ms avg")
        
        # 3. Persistence backend comparison
        print("\n3. Benchmarking Persistence Backends")
        print("-" * 40)
        persistence_results = await self.benchmark.benchmark_persistence_backends(
            data_size=1000, iterations=500
        )
        test_results["persistence"] = persistence_results
        for backend, metrics in persistence_results.items():
            print(f"  {backend}: {metrics['average_save_time_ms']:.2f}ms save, {metrics['average_load_time_ms']:.2f}ms load")
        
        # 4. Load testing
        print("\n4. Running Load Tests")
        print("-" * 40)
        load_results = await self.load_tester.run_concurrent_load_test(
            concurrent_users=50, duration_seconds=20, failure_rate=0.1
        )
        test_results["load_test"] = load_results
        print(f"  Throughput: {load_results['throughput_ops_per_sec']:.1f} ops/sec")
        print(f"  Success rate: {load_results['success_rate']:.1f}%")
        
        # 5. Scaling test
        print("\n5. Running Scaling Test")
        print("-" * 40)
        scaling_results = await self.load_tester.run_scaling_test(
            start_users=10, max_users=100, user_increment=10, duration_per_test=5
        )
        test_results["scaling"] = scaling_results
        print(f"  Optimal user count: {scaling_results['optimal_user_count']}")
        
        # 6. Memory profiling
        print("\n6. Profiling Memory Usage")
        print("-" * 40)
        
        @recoverable(max_retries=1)
        async def memory_test_operation(operation_id: str):
            await asyncio.sleep(0.01)
            return {"operation_id": operation_id}
        
        memory_results = await self.memory_profiler.profile_memory_usage(
            memory_test_operation, iterations=100
        )
        test_results["memory"] = memory_results
        print(f"  Memory efficiency: {memory_results['memory_efficiency_score']:.1f}/100")
        
        # Generate summary
        summary = self._generate_performance_summary(test_results)
        
        print("\n" + "=" * 60)
        print("Performance Test Summary")
        print("=" * 60)
        print(f"Overall Performance Score: {summary['overall_score']:.1f}/100")
        print(f"Recovery Overhead: {summary['overhead_grade']}")
        print(f"Load Handling: {summary['load_grade']}")
        print(f"Memory Efficiency: {summary['memory_grade']}")
        
        return {
            "test_results": test_results,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary."""
        
        # Calculate scores for different aspects
        overhead_score = max(0, 100 - test_results["overhead"]["overhead_percentage"] * 5)
        
        best_strategy = max(
            test_results["strategies"].values(),
            key=lambda x: x["success_rate"]
        )
        strategy_score = best_strategy["success_rate"]
        
        load_score = min(100, test_results["load_test"]["success_rate"] * 1.2)
        
        memory_score = test_results["memory"]["memory_efficiency_score"]
        
        # Calculate overall score
        overall_score = (
            overhead_score * 0.25 +
            strategy_score * 0.3 +
            load_score * 0.3 +
            memory_score * 0.15
        )
        
        # Determine grades
        def get_grade(score):
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
        
        return {
            "overall_score": overall_score,
            "overhead_score": overhead_score,
            "strategy_score": strategy_score,
            "load_score": load_score,
            "memory_score": memory_score,
            "overhead_grade": get_grade(overhead_score),
            "strategy_grade": get_grade(strategy_score),
            "load_grade": get_grade(load_score),
            "memory_grade": get_grade(memory_score),
            "overall_grade": get_grade(overall_score)
        }


# Global performance test runner
_performance_test_runner = PerformanceTestRunner()

async def run_comprehensive_performance_tests():
    """Run comprehensive performance tests."""
    return await _performance_test_runner.run_all_performance_tests()


if __name__ == "__main__":
    # Run all performance tests
    results = asyncio.run(run_comprehensive_performance_tests())
    print(f"\nPerformance testing complete. Results: {results}")