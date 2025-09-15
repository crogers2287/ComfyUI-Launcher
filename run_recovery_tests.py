#!/usr/bin/env python3
"""
Main test runner for ComfyUI Launcher recovery system tests.

This script provides:
1. Comprehensive test execution for all recovery scenarios
2. Performance benchmarking and analysis
3. Test report generation
4. Configuration management
5. Parallel test execution support

Usage:
    python run_recovery_tests.py --all                    # Run all tests
    python run_recovery_tests.py --unit                   # Run unit tests only
    python run_recovery_tests.py --integration           # Run integration tests
    python run_recovery_tests.py --e2e                    # Run end-to-end tests
    python run_recovery_tests.py --performance            # Run performance tests
    python run_recovery_tests.py --parallel               # Run tests in parallel
    python run_recovery_tests.py --report                # Generate test report
"""

import asyncio
import argparse
import sys
import os
import time
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import pytest
import multiprocessing

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test modules
from backend.tests.recovery.test_comprehensive_recovery import *
from backend.tests.recovery.test_integration_scenarios import *
from backend.tests.recovery.test_end_to_end_scenarios import *
from backend.tests.recovery.test_performance_benchmarks import *


class TestRunner:
    """Main test runner for recovery system tests."""
    
    def __init__(self):
        self.results = {}
        self.config = self._load_config()
        self.report_dir = Path(self.config.get("report_dir", "test_reports"))
        self.report_dir.mkdir(exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load test configuration."""
        default_config = {
            "test_timeout": 300,
            "parallel_workers": multiprocessing.cpu_count(),
            "report_dir": "test_reports",
            "performance_samples": 100,
            "load_test_duration": 30,
            "enable_memory_profiling": True,
            "log_level": "INFO"
        }
        
        config_path = Path("test_config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites."""
        print("🚀 Starting Comprehensive Recovery Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        all_results = {}
        
        # Run different test categories
        test_categories = [
            ("Unit Tests", self._run_unit_tests),
            ("Integration Tests", self._run_integration_tests),
            ("End-to-End Tests", self._run_e2e_tests),
            ("Performance Tests", self._run_performance_tests)
        ]
        
        for category_name, test_func in test_categories:
            print(f"\n📋 Running {category_name}")
            print("-" * 40)
            
            try:
                result = await test_func()
                all_results[category_name] = result
                
                status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
                print(f"{category_name}: {status}")
                
                if not result.get("success", False):
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ {category_name} failed with error: {e}")
                all_results[category_name] = {
                    "success": False,
                    "error": str(e),
                    "execution_time": 0
                }
        
        # Generate summary report
        total_time = time.time() - start_time
        summary = self._generate_summary(all_results, total_time)
        
        print("\n" + "=" * 60)
        print("📊 Test Execution Summary")
        print("=" * 60)
        self._print_summary(summary)
        
        # Save detailed report
        await self._save_report(all_results, summary)
        
        return summary
    
    async def _run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests for recovery system."""
        start_time = time.time()
        
        try:
            # Run pytest for unit tests
            result = subprocess.run([
                "python", "-m", "pytest",
                "backend/tests/recovery/test_comprehensive_recovery.py",
                "-v", "--tb=short",
                f"--timeout={self.config['test_timeout']}"
            ], capture_output=True, text=True, cwd=project_root)
            
            success = result.returncode == 0
            
            # Parse results
            test_count = self._parse_pytest_output(result.stdout)
            
            return {
                "success": success,
                "test_count": test_count,
                "execution_time": time.time() - start_time,
                "output": result.stdout,
                "error": result.stderr if not success else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        start_time = time.time()
        
        try:
            # Run integration test scenarios
            results = await run_comprehensive_integration_tests()
            
            return {
                "success": results.get("success_rate", 0) >= 80.0,
                "success_rate": results.get("success_rate", 0),
                "total_tests": results.get("total_tests", 0),
                "passed_tests": results.get("passed_tests", 0),
                "execution_time": results.get("total_execution_time", time.time() - start_time),
                "detailed_results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests."""
        start_time = time.time()
        
        try:
            # Run E2E test scenarios
            results = await run_comprehensive_e2e_tests()
            
            return {
                "success": results.get("success_rate", 0) >= 75.0,
                "success_rate": results.get("success_rate", 0),
                "total_tests": results.get("total_tests", 0),
                "passed_tests": results.get("passed_tests", 0),
                "execution_time": results.get("total_execution_time", time.time() - start_time),
                "detailed_results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmark tests."""
        start_time = time.time()
        
        try:
            # Run performance tests
            results = await run_comprehensive_performance_tests()
            
            # Determine success based on performance thresholds
            overall_score = results.get("summary", {}).get("overall_score", 0)
            success = overall_score >= 70.0  # 70% minimum score
            
            return {
                "success": success,
                "overall_score": overall_score,
                "performance_grade": results.get("summary", {}).get("overall_grade", "Unknown"),
                "execution_time": time.time() - start_time,
                "detailed_results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _parse_pytest_output(self, output: str) -> int:
        """Parse pytest output to extract test count."""
        lines = output.split('\n')
        for line in lines:
            if 'collected' in line and 'items' in line:
                try:
                    return int(line.split()[1])
                except:
                    continue
        return 0
    
    def _generate_summary(self, results: Dict[str, Any], total_time: float) -> Dict[str, Any]:
        """Generate test execution summary."""
        total_tests = 0
        passed_tests = 0
        successful_categories = 0
        
        for category, result in results.items():
            if result.get("success", False):
                successful_categories += 1
            
            if "test_count" in result:
                total_tests += result["test_count"]
                if result["success"]:
                    passed_tests += result["test_count"]
            elif "total_tests" in result:
                total_tests += result["total_tests"]
                passed_tests += result.get("passed_tests", 0)
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        category_success_rate = (successful_categories / len(results) * 100) if results else 0
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "category_success_rate": category_success_rate,
            "successful_categories": successful_categories,
            "total_categories": len(results),
            "total_execution_time": total_time,
            "average_test_time": total_time / total_tests if total_tests > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detailed_results": results
        }
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print test execution summary."""
        print(f"📈 Overall Success Rate: {summary['success_rate']:.1f}%")
        print(f"🎯 Categories Passed: {summary['successful_categories']}/{summary['total_categories']}")
        print(f"⏱️  Total Execution Time: {summary['total_execution_time']:.2f}s")
        print(f"📊 Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
        
        if summary["success_rate"] >= 90:
            print("🟢 Excellent test results!")
        elif summary["success_rate"] >= 80:
            print("🟡 Good test results!")
        elif summary["success_rate"] >= 70:
            print("🟠 Acceptable test results")
        else:
            print("🔴 Test results need improvement")
    
    async def _save_report(self, results: Dict[str, Any], summary: Dict[str, Any]):
        """Save detailed test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_dir / f"recovery_test_report_{timestamp}.json"
        summary_file = self.report_dir / f"test_summary_{timestamp}.txt"
        
        # Save detailed JSON report
        full_report = {
            "summary": summary,
            "detailed_results": results,
            "configuration": self.config,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        with open(report_file, 'w') as f:
            json.dump(full_report, f, indent=2)
        
        # Save human-readable summary
        with open(summary_file, 'w') as f:
            f.write("ComfyUI Launcher Recovery Test Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Tests: {summary['total_tests']}\n")
            f.write(f"Passed Tests: {summary['passed_tests']}\n")
            f.write(f"Failed Tests: {summary['failed_tests']}\n")
            f.write(f"Success Rate: {summary['success_rate']:.1f}%\n")
            f.write(f"Execution Time: {summary['total_execution_time']:.2f}s\n\n")
            
            f.write("Category Results:\n")
            f.write("-" * 30 + "\n")
            for category, result in results.items():
                status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
                f.write(f"{category}: {status}\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        print(f"📋 Summary saved to: {summary_file}")


class ParallelTestRunner:
    """Run tests in parallel for faster execution."""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or multiprocessing.cpu_count()
    
    async def run_tests_parallel(self, test_functions: List[callable]) -> List[Dict[str, Any]]:
        """Run multiple test functions in parallel."""
        print(f"🔄 Running {len(test_functions)} test suites in parallel")
        print(f"🔧 Using {self.max_workers} workers\n")
        
        semaphore = asyncio.Semaphore(self.max_workers)
        tasks = []
        
        async def run_with_semaphore(test_func, test_name):
            async with semaphore:
                print(f"🚀 Starting {test_name}")
                try:
                    result = await test_func()
                    print(f"✅ Completed {test_name}")
                    return {"test_name": test_name, "result": result, "success": True}
                except Exception as e:
                    print(f"❌ Failed {test_name}: {e}")
                    return {"test_name": test_name, "error": str(e), "success": False}
        
        for test_func in test_functions:
            test_name = test_func.__name__
            tasks.append(run_with_semaphore(test_func, test_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, dict)]


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="ComfyUI Launcher Recovery Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_recovery_tests.py --all
  python run_recovery_tests.py --unit --integration --performance
  python run_recovery_tests.py --parallel --report
  python run_recovery_tests.py --config custom_config.json
        """
    )
    
    parser.add_argument(
        "--all", action="store_true",
        help="Run all test suites"
    )
    
    parser.add_argument(
        "--unit", action="store_true",
        help="Run unit tests only"
    )
    
    parser.add_argument(
        "--integration", action="store_true",
        help="Run integration tests only"
    )
    
    parser.add_argument(
        "--e2e", action="store_true",
        help="Run end-to-end tests only"
    )
    
    parser.add_argument(
        "--performance", action="store_true",
        help="Run performance tests only"
    )
    
    parser.add_argument(
        "--parallel", action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--report", action="store_true",
        help="Generate detailed test report"
    )
    
    parser.add_argument(
        "--config", type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="Test timeout in seconds"
    )
    
    parser.add_argument(
        "--workers", type=int,
        help="Number of parallel workers"
    )
    
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    
    return parser


async def main():
    """Main test runner function."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # If no specific test type selected, run all tests
    if not any([args.all, args.unit, args.integration, args.e2e, args.performance]):
        args.all = True
    
    # Create test runner
    runner = TestRunner()
    
    # Override config with command line arguments
    if args.config:
        runner.config.update(json.load(open(args.config)))
    
    if args.timeout:
        runner.config["test_timeout"] = args.timeout
    
    if args.workers:
        runner.config["parallel_workers"] = args.workers
    
    # Run selected tests
    if args.all:
        results = await runner.run_all_tests()
    
    elif args.parallel:
        # Run tests in parallel
        parallel_runner = ParallelTestRunner(runner.config["parallel_workers"])
        
        test_functions = [
            runner._run_unit_tests,
            runner._run_integration_tests,
            runner._run_e2e_tests,
            runner._run_performance_tests
        ]
        
        parallel_results = await parallel_runner.run_tests_parallel(test_functions)
        
        # Process parallel results
        all_results = {}
        total_time = 0
        
        for result in parallel_results:
            if result["success"]:
                test_name = result["test_name"].replace("_run_", "").replace("_tests", "")
                all_results[test_name.title() + " Tests"] = result["result"]
                total_time += result["result"].get("execution_time", 0)
        
        summary = runner._generate_summary(all_results, total_time)
        runner._print_summary(summary)
        
        if args.report:
            await runner._save_report(all_results, summary)
    
    else:
        # Run specific test types
        results = {}
        total_time = 0
        
        if args.unit:
            print("🧪 Running Unit Tests")
            result = await runner._run_unit_tests()
            results["Unit Tests"] = result
            total_time += result.get("execution_time", 0)
        
        if args.integration:
            print("🔗 Running Integration Tests")
            result = await runner._run_integration_tests()
            results["Integration Tests"] = result
            total_time += result.get("execution_time", 0)
        
        if args.e2e:
            print("🎯 Running End-to-End Tests")
            result = await runner._run_e2e_tests()
            results["End-to-End Tests"] = result
            total_time += result.get("execution_time", 0)
        
        if args.performance:
            print("⚡ Running Performance Tests")
            result = await runner._run_performance_tests()
            results["Performance Tests"] = result
            total_time += result.get("execution_time", 0)
        
        if results:
            summary = runner._generate_summary(results, total_time)
            runner._print_summary(summary)
            
            if args.report:
                await runner._save_report(results, summary)
    
    # Exit with appropriate code
    if args.all or (args.unit or args.integration or args.e2e or args.performance):
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())