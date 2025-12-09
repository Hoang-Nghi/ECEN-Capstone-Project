# comprehensive_test.py
import requests
import time
import json

BACKEND_URL = "https://capstone-backend-1041336188288.us-central1.run.app"

class BackendTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.results = []
    
    def test(self, name, method, endpoint, **kwargs):
        """Generic test method"""
        print(f"\nTesting: {name}")
        url = f"{self.base_url}{endpoint}"
        
        try:
            start = time.time()
            response = requests.request(method, url, **kwargs)
            elapsed = time.time() - start
            
            result = {
                "name": name,
                "status": response.status_code,
                "elapsed": f"{elapsed:.3f}s",
                "success": 200 <= response.status_code < 300
            }
            
            if result["success"]:
                print(f"   SUCCESS (Status: {response.status_code}, Time: {elapsed:.3f}s)")
                try:
                    data = response.json()
                    print(f"   Response: {json.dumps(data, indent=6)}")
                except:
                    print(f"   Response: {response.text[:100]}")
            else:
                print(f"   FAILED (Status: {response.status_code})")
                print(f"   Response: {response.text[:200]}")
            
            self.results.append(result)
            return result["success"]
            
        except Exception as e:
            print(f"    ERROR: {e}")
            self.results.append({
                "name": name,
                "status": "error",
                "elapsed": "0s",
                "success": False
            })
            return False
    
    def summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        for result in self.results:
            status_icon = "GOOD" if result["success"] else "BAD"
            print(f"{status_icon} {result['name']:<40} {result['status']:<10} {result['elapsed']}")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        
        print("=" * 60)
        print(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
        print("=" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("FRONTEND -> BACKEND CONNECTION TEST")
    print(f"Testing: {BACKEND_URL}")
    print("=" * 60)
    
    tester = BackendTester(BACKEND_URL)
    
    # Test 1: Health check (should always work)
    tester.test(
        "Health Check (Public)",
        "GET",
        "/api/health"
    )
    
    # Test 2: Ping test (if you added it)
    tester.test(
        "Ping Test (Public)",
        "GET",
        "/api/test/ping"
    )
    
    # Test 3: Echo test (if you added it)
    tester.test(
        "Echo Test (Public)",
        "POST",
        "/api/test/echo",
        json={"message": "Hello from frontend!", "timestamp": time.time()},
        headers={"Content-Type": "application/json"}
    )
    
    # Test 4: Unauthorized request (should fail with 401)
    print("\Testing Security (should fail without auth)...")
    tester.test(
        "Plaid Link Token (Unauthorized)",
        "POST",
        "/api/plaid/create_link_token",
        headers={"Content-Type": "application/json"}
    )
    
    # Print summary
    tester.summary()
    
    print("\n Next Step: Add Firebase authentication to test protected endpoints")