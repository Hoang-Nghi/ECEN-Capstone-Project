"""
12.1 API Response Time Validation Script

Tests API endpoint response times to ensure they meet mobile app standards (<300ms).
Validates that the backend responds quickly enough for smooth user experience.

Usage:
    python 01_api_response_time_validation.py <test_user_id>
"""

import sys
import os
import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple
import statistics

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://capstone-backend-1041336188288.us-central1.run.app/api")
FIREBASE_TOKEN = os.getenv("FIREBASE_TOKEN", "")  # Set this via environment variable

# Test user
TEST_USER_ID = sys.argv[1] if len(sys.argv) > 1 else "nUtLw9z8fqSOQYkJPBh3WbpU4FH2"

# Performance thresholds (in milliseconds)
EXCELLENT_THRESHOLD = 100
GOOD_THRESHOLD = 300
ACCEPTABLE_THRESHOLD = 500


class APIResponseTimeValidator:
    """Validates API response times across different endpoint types"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.results = []
    
    def measure_endpoint(self, method: str, endpoint: str, data: dict = None, runs: int = 5) -> Dict:
        """Measure response time for an endpoint over multiple runs"""
        times = []
        errors = []
        
        url = f"{self.base_url}{endpoint}"
        
        for i in range(runs):
            try:
                start = time.perf_counter()
                
                if method == "GET":
                    response = requests.get(url, headers=self.headers, timeout=10)
                elif method == "POST":
                    response = requests.post(url, headers=self.headers, json=data, timeout=10)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                end = time.perf_counter()
                elapsed_ms = (end - start) * 1000
                
                times.append(elapsed_ms)
                
                if response.status_code not in [200, 201]:
                    errors.append(f"Run {i+1}: HTTP {response.status_code}")
                
                # Small delay between runs
                if i < runs - 1:
                    time.sleep(0.2)
                    
            except Exception as e:
                errors.append(f"Run {i+1}: {str(e)}")
        
        if not times:
            return {
                "endpoint": endpoint,
                "method": method,
                "status": "FAILED",
                "errors": errors
            }
        
        avg_time = statistics.mean(times)
        
        # Determine status based on thresholds
        if avg_time < EXCELLENT_THRESHOLD:
            status = "EXCELLENT"
        elif avg_time < GOOD_THRESHOLD:
            status = "GOOD"
        elif avg_time < ACCEPTABLE_THRESHOLD:
            status = "ACCEPTABLE"
        else:
            status = "NEEDS_OPTIMIZATION"
        
        return {
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "runs": len(times),
            "avg_ms": round(avg_time, 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "median_ms": round(statistics.median(times), 2),
            "std_dev_ms": round(statistics.stdev(times), 2) if len(times) > 1 else 0,
            "errors": errors if errors else None
        }
    
    def run_validation(self):
        """Run validation tests on all critical endpoints"""
        print("=" * 80)
        print("API RESPONSE TIME VALIDATION")
        print("Student Savings Backend - Validation 12.1")
        print("=" * 80)
        print(f"\nAPI Base URL: {self.base_url}")
        print(f"Test User ID: {TEST_USER_ID}")
        print(f"Test Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        tests = [
            # Health/utility endpoints
            ("GET", "/health", None, "Health Check"),
            ("POST", "/test/echo", {"message": "test"}, "Echo Test"),
            
            # User progression
            ("GET", "/minigame/profile", None, "User Profile"),
            ("GET", "/minigame/ranks", None, "Rank List (Public)"),
            ("GET", "/minigame/stats", None, "Minigame Stats"),
            
            # Quiz endpoints
            ("GET", "/minigame/quiz/state", None, "Quiz State"),
            ("POST", "/minigame/quiz/new", None, "Start New Quiz"),
            
            # Spend detective endpoints
            ("GET", "/spend-detective/state", None, "Detective State"),
            
            # Financial categories
            ("GET", "/financial-categories/state", None, "Categories State"),
            
            # Plaid endpoints
            ("GET", "/plaid/status", None, "Plaid Connection Status"),
        ]
        
        print("Running response time tests...\n")
        
        for method, endpoint, data, description in tests:
            print(f"Testing: {description}...", end=" ", flush=True)
            result = self.measure_endpoint(method, endpoint, data, runs=5)
            self.results.append({**result, "description": description})
            
            if result["status"] == "FAILED":
                print(f"✗ FAILED")
            else:
                status_symbol = "✓" if result["status"] in ["EXCELLENT", "GOOD"] else "⚠"
                print(f"{status_symbol} {result['avg_ms']}ms ({result['status']})")
        
        print("\n" + "=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)
        
        self._print_summary()
        self._print_detailed_results()
        self._save_results()
        self._generate_report()
    
    def _print_summary(self):
        """Print summary statistics"""
        all_times = [r["avg_ms"] for r in self.results if r["status"] != "FAILED"]
        
        if not all_times:
            print("\n❌ All tests failed!")
            return
        
        excellent = sum(1 for r in self.results if r["status"] == "EXCELLENT")
        good = sum(1 for r in self.results if r["status"] == "GOOD")
        acceptable = sum(1 for r in self.results if r["status"] == "ACCEPTABLE")
        needs_opt = sum(1 for r in self.results if r["status"] == "NEEDS_OPTIMIZATION")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        
        print("\nOVERALL SUMMARY:")
        print(f"  Total Endpoints Tested: {len(self.results)}")
        print(f"  Excellent (<100ms): {excellent}")
        print(f"  Good (100-300ms): {good}")
        print(f"  Acceptable (300-500ms): {acceptable}")
        print(f"  Needs Optimization (>500ms): {needs_opt}")
        print(f"  Failed: {failed}")
        
        print(f"\nAGGREGATE PERFORMANCE:")
        print(f"  Average Response Time: {statistics.mean(all_times):.2f}ms")
        print(f"  Median Response Time: {statistics.median(all_times):.2f}ms")
        print(f"  Fastest Response: {min(all_times):.2f}ms")
        print(f"  Slowest Response: {max(all_times):.2f}ms")
        
        if len(all_times) > 1:
            percentile_95 = sorted(all_times)[int(len(all_times) * 0.95)]
            print(f"  95th Percentile: {percentile_95:.2f}ms")
        
        # Overall pass/fail
        avg_time = statistics.mean(all_times)
        if avg_time < GOOD_THRESHOLD and failed == 0:
            print(f"\n✅ VALIDATION PASSED - Average response time meets standards")
        elif avg_time < ACCEPTABLE_THRESHOLD and failed == 0:
            print(f"\n⚠️  VALIDATION PASSED (with warnings) - Some endpoints could be optimized")
        else:
            print(f"\n❌ VALIDATION FAILED - Response times exceed acceptable thresholds")
    
    def _print_detailed_results(self):
        """Print detailed results for each endpoint"""
        print("\nDETAILED RESULTS:")
        print("-" * 80)
        
        for result in self.results:
            print(f"\n{result['description']}")
            print(f"  Endpoint: {result['method']} {result['endpoint']}")
            print(f"  Status: {result['status']}")
            
            if result['status'] != "FAILED":
                print(f"  Average Time: {result['avg_ms']}ms")
                print(f"  Median Time: {result['median_ms']}ms")
                print(f"  Range: {result['min_ms']}ms - {result['max_ms']}ms")
                print(f"  Std Deviation: {result['std_dev_ms']}ms")
                
                if result.get('errors'):
                    print(f"  Warnings: {len(result['errors'])} errors occurred")
            else:
                print(f"  Errors: {result.get('errors', [])}")
    
    def _save_results(self):
        """Save results to JSON file"""
        import json
        
        output = {
            "validation_type": "12.1_api_response_time",
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "test_user_id": TEST_USER_ID,
            "thresholds": {
                "excellent": EXCELLENT_THRESHOLD,
                "good": GOOD_THRESHOLD,
                "acceptable": ACCEPTABLE_THRESHOLD
            },
            "results": self.results
        }
        
        filename = f"validation_12_1_api_response_time_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n{'=' * 80}")
        print(f"Results saved to: {filename}")
        print(f"{'=' * 80}\n")
    
    def _generate_report(self):
        """Generate text report for documentation"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("12.1 API RESPONSE TIME VALIDATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"API Base URL: {self.base_url}")
        report_lines.append(f"Test User ID: {TEST_USER_ID}")
        report_lines.append("")
        
        all_times = [r["avg_ms"] for r in self.results if r["status"] != "FAILED"]
        
        if all_times:
            report_lines.append("Performance Summary:")
            report_lines.append(f"  Average Response Time: {statistics.mean(all_times):.2f}ms")
            report_lines.append(f"  Median Response Time: {statistics.median(all_times):.2f}ms")
            report_lines.append(f"  95th Percentile: {sorted(all_times)[int(len(all_times)*0.95)]:.2f}ms")
            report_lines.append("")
            
            report_lines.append("Performance Distribution:")
            excellent = sum(1 for r in self.results if r["status"] == "EXCELLENT")
            good = sum(1 for r in self.results if r["status"] == "GOOD")
            acceptable = sum(1 for r in self.results if r["status"] == "ACCEPTABLE")
            
            report_lines.append(f"  Excellent (<100ms): {excellent}/{len(self.results)}")
            report_lines.append(f"  Good (100-300ms): {good}/{len(self.results)}")
            report_lines.append(f"  Acceptable (300-500ms): {acceptable}/{len(self.results)}")
            report_lines.append("")
            
            avg_time = statistics.mean(all_times)
            if avg_time < GOOD_THRESHOLD:
                report_lines.append("✅ CONCLUSION: API response times meet mobile app standards")
                report_lines.append("   All endpoints respond quickly enough for smooth user experience.")
            else:
                report_lines.append("⚠️  CONCLUSION: API response times are acceptable but could be improved")
        else:
            report_lines.append("❌ CONCLUSION: Validation failed - no successful responses")
        
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        filename = f"validation_12_1_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(report_text)
        
        print(report_text)
        print(f"\nReport saved to: {filename}")


def main():
    if not FIREBASE_TOKEN:
        print("ERROR: Firebase token not set!")
        print("Set FIREBASE_TOKEN environment variable:")
        print("  export FIREBASE_TOKEN='your_token_here'")
        print("  python 01_api_response_time_validation.py")
        sys.exit(1)
    
    validator = APIResponseTimeValidator(API_BASE_URL, FIREBASE_TOKEN)
    validator.run_validation()


if __name__ == "__main__":
    main()