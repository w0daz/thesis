"""
API Testing Script
Tests all endpoints and validates responses
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_endpoint(method, endpoint, data=None, params=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ {method} {endpoint}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {json.dumps(result, indent=2)[:200]}...")
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"✗ {method} {endpoint}")
        print(f"  Error: {e}")
        return None

def main():
    print_section("🧪 API ENDPOINT TESTING")
    
    # Test 1: Health Check
    print_section("TEST 1: Health Check")
    test_endpoint("GET", "/api/health")
    
    # Test 2: Current Reading
    print_section("TEST 2: Current Reading")
    test_endpoint("GET", "/api/current")
    
    # Test 3: Historical Data
    print_section("TEST 3: Historical Data (1 hour)")
    test_endpoint("GET", "/api/history", params={"hours": 1})
    
    # Test 4: Statistics
    print_section("TEST 4: Statistics")
    test_endpoint("GET", "/api/statistics")
    
    # Test 5: Baseline
    print_section("TEST 5: Baseline Calculation")
    test_endpoint("GET", "/api/baseline", params={"recalculate": True})
    
    # Test 6: Get Alerts
    print_section("TEST 6: Get Alerts")
    test_endpoint("GET", "/api/alerts", params={"limit": 10})
    
    # Test 7: Create Alert
    print_section("TEST 7: Create Test Alert")
    test_alert = {
        "timestamp": datetime.now().isoformat(),
        "power_kw": 6.5,
        "baseline_kw": 2.3,
        "deviation_percent": 182.6,
        "alert_type": "high_consumption"
    }
    test_endpoint("POST", "/api/alerts", data=test_alert)
    
    # Test 8: Get Settings
    print_section("TEST 8: Get Settings")
    test_endpoint("GET", "/api/settings")
    
    # Test 9: Update Settings
    print_section("TEST 9: Update Settings")
    new_settings = {
        "alert_threshold_percentile": 90,
        "notification_enabled": False
    }
    test_endpoint("POST", "/api/settings", data=new_settings)
    
    # Test 10: Verify Settings Updated
    print_section("TEST 10: Verify Settings Update")
    test_endpoint("GET", "/api/settings")
    
    print_section("✅ ALL TESTS COMPLETED")

if __name__ == "__main__":
    main()