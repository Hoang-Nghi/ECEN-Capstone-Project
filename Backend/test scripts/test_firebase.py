"""
Firebase Performance Validation - Simple Version for test_scripts folder

Place this file in your test_scripts folder and run:
    python firebase_performance_simple.py [test_user_id]

Automatically finds the project root (parent directory).
"""

import sys
import os
import time
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Callable
from collections import defaultdict
import json

# Auto-detect project root (parent of test_scripts folder)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.dirname(script_dir)  # Go up one level from test_scripts

# Add project to path
sys.path.insert(0, project_path)

# Test user ID from command line or default
test_user_id = sys.argv[1] if len(sys.argv) > 1 else "nUtLw9z8fqSOQYkJPBh3WbpU4FH2"

print(f"Project Root: {project_path}")
print(f"Test User ID: {test_user_id}\n")

# Import from services folder
try:
    import importlib.util
    
    firebase_path = os.path.join(project_path, "services", "firebase.py")
    
    if not os.path.exists(firebase_path):
        firebase_path = os.path.join(project_path, "firebase.py")
    
    if not os.path.exists(firebase_path):
        print(f"ERROR: Could not find firebase.py")
        print(f"Searched in:")
        print(f"  - {os.path.join(project_path, 'services', 'firebase.py')}")
        print(f"  - {os.path.join(project_path, 'firebase.py')}")
        sys.exit(1)
    
    spec = importlib.util.spec_from_file_location("project_firebase", firebase_path)
    project_firebase = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(project_firebase)
    get_db = project_firebase.get_db
    
    from firebase_admin import firestore
    
    print(f"✓ Successfully loaded: {firebase_path}\n")
    
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}")
    print("Make sure firebase-admin is installed: pip install firebase-admin")
    sys.exit(1)


class PerformanceMetrics:
    """Container for performance test results"""
    
    def __init__(self, name: str):
        self.name = name
        self.execution_times: List[float] = []
        self.document_counts: List[int] = []
        self.errors: List[str] = []
        
    def add_result(self, execution_time: float, doc_count: int = 0):
        self.execution_times.append(execution_time)
        self.document_counts.append(doc_count)
    
    def add_error(self, error: str):
        self.errors.append(error)
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.execution_times:
            return {
                "test": self.name,
                "status": "FAILED",
                "errors": self.errors
            }
        
        return {
            "test": self.name,
            "status": "PASSED" if not self.errors else "PASSED_WITH_WARNINGS",
            "runs": len(self.execution_times),
            "avg_time_ms": round(statistics.mean(self.execution_times) * 1000, 2),
            "min_time_ms": round(min(self.execution_times) * 1000, 2),
            "max_time_ms": round(max(self.execution_times) * 1000, 2),
            "median_time_ms": round(statistics.median(self.execution_times) * 1000, 2),
            "std_dev_ms": round(statistics.stdev(self.execution_times) * 1000, 2) if len(self.execution_times) > 1 else 0,
            "avg_docs_returned": round(statistics.mean(self.document_counts), 1) if self.document_counts else 0,
            "warnings": self.errors if self.errors else None
        }


class FirebasePerformanceTester:
    """Test suite for Firebase Firestore query performance"""
    
    def __init__(self, test_user_id: str):
        self.db = get_db()
        self.test_user_id = test_user_id
        self.results: List[PerformanceMetrics] = []
        
    def _measure_query(self, query_func: Callable, runs: int = 5) -> PerformanceMetrics:
        metrics = PerformanceMetrics(query_func.__name__)
        
        for i in range(runs):
            try:
                start = time.perf_counter()
                doc_count = query_func()
                end = time.perf_counter()
                
                execution_time = end - start
                metrics.add_result(execution_time, doc_count)
                
                if i < runs - 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                metrics.add_error(f"Run {i+1}: {str(e)}")
        
        self.results.append(metrics)
        return metrics
    
    def test_simple_document_read(self):
        """Test 1: Simple document read by ID"""
        def query():
            doc = self.db.collection("users").document(self.test_user_id).get()
            return 1 if doc.exists else 0
        
        return self._measure_query(query, runs=10)
    
    def test_subcollection_query_no_filter(self):
        """Test 2: Query subcollection without filters"""
        def query():
            col = self.db.collection("users").document(self.test_user_id).collection("transactions")
            docs = list(col.limit(50).stream())
            return len(docs)
        
        return self._measure_query(query, runs=5)
    
    def test_date_range_query(self):
        """Test 3: Date range query (typical analytics query)"""
        def query():
            col = self.db.collection("users").document(self.test_user_id).collection("transactions")
            
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
            
            q = (col.where("date", ">=", start_date)
                    .where("date", "<=", end_date)
                    .order_by("date", direction=firestore.Query.DESCENDING))
            
            docs = list(q.stream())
            return len(docs)
        
        return self._measure_query(query, runs=5)
    
    def test_date_range_with_limit(self):
        """Test 4: Date range query with limit (recent transactions)"""
        def query():
            col = self.db.collection("users").document(self.test_user_id).collection("transactions")
            
            q = col.order_by("date", direction=firestore.Query.DESCENDING).limit(20)
            docs = list(q.stream())
            return len(docs)
        
        return self._measure_query(query, runs=5)
    
    def test_complex_aggregation_simulation(self):
        """Test 5: Complex query simulating category breakdown"""
        def query():
            col = self.db.collection("users").document(self.test_user_id).collection("transactions")
            
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
            
            q = (col.where("date", ">=", start_date)
                    .where("date", "<=", end_date))
            
            docs = list(q.stream())
            
            categories = defaultdict(float)
            for doc in docs:
                data = doc.to_dict()
                if data:
                    amount = float(data.get("amount", 0))
                    category = data.get("pfc_primary", "Other")
                    categories[category] += amount
            
            return len(docs)
        
        return self._measure_query(query, runs=5)
    
    def test_game_state_read(self):
        """Test 6: Read game state from subcollection"""
        def query():
            games = ["smart_saver_quiz", "spend_detective", "financial_categories"]
            total_docs = 0
            
            for game in games:
                doc = (self.db.collection("users")
                      .document(self.test_user_id)
                      .collection("games")
                      .document(game)
                      .get())
                if doc.exists:
                    total_docs += 1
            
            return total_docs
        
        return self._measure_query(query, runs=10)
    
    def test_game_history_query(self):
        """Test 7: Query game play history"""
        def query():
            col = (self.db.collection("users")
                  .document(self.test_user_id)
                  .collection("games")
                  .document("smart_saver_quiz")
                  .collection("history"))
            
            docs = list(col.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream())
            return len(docs)
        
        return self._measure_query(query, runs=5)
    
    def test_batch_write_performance(self):
        """Test 8: Batch write operations"""
        def query():
            batch = self.db.batch()
            
            test_col = (self.db.collection("users")
                       .document(self.test_user_id)
                       .collection("test_batch"))
            
            for i in range(10):
                doc_ref = test_col.document(f"test_{i}")
                batch.set(doc_ref, {
                    "index": i,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "test": True
                })
            
            batch.commit()
            
            # Clean up
            for i in range(10):
                test_col.document(f"test_{i}").delete()
            
            return 10
        
        return self._measure_query(query, runs=3)
    
    def test_index_efficiency(self):
        """Test 9: Query with composite index (date + order by)"""
        def query():
            col = self.db.collection("users").document(self.test_user_id).collection("transactions")
            
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
            
            q = (col.where("date", ">=", start_date)
                    .where("date", "<=", end_date)
                    .order_by("date", direction=firestore.Query.DESCENDING))
            
            docs = list(q.stream())
            return len(docs)
        
        return self._measure_query(query, runs=5)
    
    def test_transaction_count_estimate(self):
        """Test 10: Get document count estimate"""
        def query():
            col = self.db.collection("users").document(self.test_user_id).collection("transactions")
            docs = list(col.stream())
            return len(docs)
        
        return self._measure_query(query, runs=3)
    
    def run_all_tests(self):
        """Execute all performance tests"""
        print("=" * 80)
        print("FIREBASE PERFORMANCE VALIDATION")
        print("Student Savings Application - ECEN 403 Capstone Project")
        print("=" * 80)
        print(f"\nTest User ID: {self.test_user_id}")
        print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nRunning performance tests...\n")
        
        tests = [
            ("Simple Document Read", self.test_simple_document_read),
            ("Subcollection Query (No Filter)", self.test_subcollection_query_no_filter),
            ("Date Range Query (30 days)", self.test_date_range_query),
            ("Recent Transactions (with limit)", self.test_date_range_with_limit),
            ("Complex Aggregation Query", self.test_complex_aggregation_simulation),
            ("Game State Read", self.test_game_state_read),
            ("Game History Query", self.test_game_history_query),
            ("Batch Write Operations", self.test_batch_write_performance),
            ("Indexed Query Efficiency", self.test_index_efficiency),
            ("Transaction Count", self.test_transaction_count_estimate),
        ]
        
        for i, (name, test_func) in enumerate(tests, 1):
            print(f"[{i}/{len(tests)}] Running: {name}...", end=" ", flush=True)
            try:
                metrics = test_func()
                stats = metrics.get_stats()
                status_symbol = "✓" if stats["status"] == "PASSED" else "⚠" if stats["status"] == "PASSED_WITH_WARNINGS" else "✗"
                print(f"{status_symbol} {stats['avg_time_ms']:.2f}ms avg")
            except Exception as e:
                print(f"✗ ERROR: {str(e)}")
                metrics = PerformanceMetrics(name)
                metrics.add_error(str(e))
                self.results.append(metrics)
        
        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        
        self._print_summary()
        self._print_detailed_results()
        self._save_results_to_file()
    
    def _print_summary(self):
        all_times = []
        passed = 0
        failed = 0
        
        for metrics in self.results:
            stats = metrics.get_stats()
            if stats["status"] in ["PASSED", "PASSED_WITH_WARNINGS"]:
                passed += 1
                all_times.extend(metrics.execution_times)
            else:
                failed += 1
        
        print("\nOVERALL SUMMARY:")
        print(f"  Total Tests: {len(self.results)}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        
        if all_times:
            print(f"\nAGGREGATE PERFORMANCE:")
            print(f"  Average Query Time: {statistics.mean(all_times) * 1000:.2f}ms")
            print(f"  Median Query Time: {statistics.median(all_times) * 1000:.2f}ms")
            print(f"  Min Query Time: {min(all_times) * 1000:.2f}ms")
            print(f"  Max Query Time: {max(all_times) * 1000:.2f}ms")
            print(f"  95th Percentile: {sorted(all_times)[int(len(all_times) * 0.95)] * 1000:.2f}ms")
    
    def _print_detailed_results(self):
        print("\nDETAILED RESULTS:")
        print("-" * 80)
        
        for metrics in self.results:
            stats = metrics.get_stats()
            print(f"\nTest: {stats['test']}")
            print(f"  Status: {stats['status']}")
            
            if stats['status'] != "FAILED":
                print(f"  Runs: {stats['runs']}")
                print(f"  Average Time: {stats['avg_time_ms']}ms")
                print(f"  Median Time: {stats['median_time_ms']}ms")
                print(f"  Min/Max Time: {stats['min_time_ms']}ms / {stats['max_time_ms']}ms")
                print(f"  Std Deviation: {stats['std_dev_ms']}ms")
                print(f"  Avg Documents: {stats['avg_docs_returned']}")
                
                if stats.get('warnings'):
                    print(f"  Warnings: {', '.join(stats['warnings'])}")
            else:
                print(f"  Errors: {', '.join(stats.get('errors', []))}")
    
    def _save_results_to_file(self):
        output = {
            "test_metadata": {
                "test_user_id": self.test_user_id,
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.results)
            },
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for m in self.results if m.get_stats()["status"] in ["PASSED", "PASSED_WITH_WARNINGS"]),
                "failed": sum(1 for m in self.results if m.get_stats()["status"] == "FAILED")
            },
            "detailed_results": [m.get_stats() for m in self.results]
        }
        
        filename = f"firebase_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n{'=' * 80}")
        print(f"Results saved to: {filename}")
        print(f"{'=' * 80}\n")


def main():
    print("\nInitializing Firebase Performance Tester...")
    tester = FirebasePerformanceTester(test_user_id)
    
    print("Starting test suite...\n")
    tester.run_all_tests()
    
    print("\nValidation complete! Results are ready for inclusion in the final report.")


if __name__ == "__main__":
    main()