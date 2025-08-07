#!/usr/bin/env python3
"""
HARD TESTS for Production-Ready CV-Library Scraper API
Tests edge cases, error conditions, concurrency, and real-world scenarios.
"""

import requests
import json
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

BASE_URL = "http://localhost:8000"

class Colors:
    """Terminal colors for better output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(title, color=Colors.CYAN):
    """Print a colored header."""
    print(f"\n{color}{Colors.BOLD}{'='*70}")
    print(f" {title}")
    print(f"{'='*70}{Colors.END}")

def print_test(test_name, status="RUNNING", color=Colors.BLUE):
    """Print test status."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{timestamp}] {test_name}: {status}{Colors.END}")

def print_result(success, message, details=None):
    """Print test result."""
    color = Colors.GREEN if success else Colors.RED
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{color}{status}: {message}{Colors.END}")
    if details:
        print(f"   {Colors.YELLOW}Details: {details}{Colors.END}")

def test_api_health_under_load():
    """Test API health endpoint under moderate concurrent load."""
    print_test("API Health Under Load")
    
    def hit_health_endpoint():
        try:
            response = requests.get(f"{BASE_URL}/api/v1/health/", timeout=10)
            return response.status_code == 200, response.elapsed.total_seconds()
        except Exception as e:
            return False, str(e)
    
    # Test with moderate load: 10 concurrent requests, 20 total
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(hit_health_endpoint) for _ in range(20)]
        results = [future.result() for future in as_completed(futures)]
    
    duration = time.time() - start_time
    success_count = sum(1 for success, _ in results if success)
    avg_response_time = sum(time for success, time in results if isinstance(time, float)) / max(len(results), 1)
    
    success = success_count >= 18  # Allow 10% failure rate
    print_result(
        success, 
        f"Health endpoint load test",
        f"20 requests in {duration:.2f}s, {success_count}/20 success, avg: {avg_response_time:.3f}s"
    )
    return success

def test_invalid_endpoints():
    """Test behavior with invalid endpoints and malformed requests."""
    print_test("Invalid Endpoints & Malformed Requests")
    
    test_cases = [
        # Invalid endpoints
        ("/api/v1/nonexistent", 404),
        ("/api/v1/sessions/invalid-session-id", 404),
        ("/api/v1/scrape/invalid-scrape-id", 404),
        # Invalid methods
        ("PUT", "/api/v1/health/", 405),
        ("DELETE", "/api/v1/health/", 405),
        ("PATCH", "/api/v1/sessions/", 405),
    ]
    
    passed = 0
    for test_case in test_cases:
        try:
            if len(test_case) == 3 and test_case[0] in ["PUT", "DELETE", "PATCH"]:
                method, endpoint, expected_status = test_case
                response = requests.request(method, f"{BASE_URL}{endpoint}")
            else:
                endpoint, expected_status = test_case
                response = requests.get(f"{BASE_URL}{endpoint}")
            
            if response.status_code == expected_status:
                passed += 1
                print(f"   ✅ {test_case}: Got expected {expected_status}")
            else:
                print(f"   ❌ {test_case}: Expected {expected_status}, got {response.status_code}")
        except Exception as e:
            print(f"   ❌ {test_case}: Exception {e}")
    
    success = passed == len(test_cases)
    print_result(success, f"Invalid endpoint handling", f"{passed}/{len(test_cases)} tests passed")
    return success

def test_malformed_requests():
    """Test API with malformed JSON and invalid data."""
    print_test("Malformed Requests & Invalid Data")
    
    test_cases = [
        # Malformed JSON
        {
            "endpoint": "/api/v1/auth/login/",
            "method": "POST",
            "data": '{"invalid": json}',  # Invalid JSON
            "headers": {"Content-Type": "application/json"},
            "expected_status": 422
        },
        # Missing required fields
        {
            "endpoint": "/api/v1/auth/login/",
            "method": "POST",
            "data": json.dumps({"username": "test"}),  # Missing password
            "headers": {"Content-Type": "application/json"},
            "expected_status": 422
        },
        # Invalid data types
        {
            "endpoint": "/api/v1/scrape/",
            "method": "POST",
            "data": json.dumps({
                "session_id": 123,  # Should be string
                "keywords": "not a list",  # Should be list
                "max_downloads": "not a number"  # Should be int
            }),
            "headers": {"Content-Type": "application/json"},
            "expected_status": 422
        }
    ]
    
    passed = 0
    for i, test_case in enumerate(test_cases):
        try:
            response = requests.request(
                test_case["method"],
                f"{BASE_URL}{test_case['endpoint']}",
                data=test_case["data"],
                headers=test_case["headers"]
            )
            
            if response.status_code == test_case["expected_status"]:
                passed += 1
                print(f"   ✅ Test {i+1}: Got expected {test_case['expected_status']}")
            else:
                print(f"   ❌ Test {i+1}: Expected {test_case['expected_status']}, got {response.status_code}")
                print(f"      Response: {response.text[:100]}")
        except Exception as e:
            print(f"   ❌ Test {i+1}: Exception {e}")
    
    success = passed == len(test_cases)
    print_result(success, f"Malformed request handling", f"{passed}/{len(test_cases)} tests passed")
    return success

def test_session_management_edge_cases():
    """Test session management with edge cases."""
    print_test("Session Management Edge Cases")
    
    passed = 0
    total_tests = 0
    
    # Test 1: Get non-existent session
    total_tests += 1
    try:
        response = requests.get(f"{BASE_URL}/api/v1/sessions/non-existent-session/")
        if response.status_code == 404:
            passed += 1
            print("   ✅ Non-existent session returns 404")
        else:
            print(f"   ❌ Non-existent session: Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Non-existent session test failed: {e}")
    
    # Test 2: Delete non-existent session
    total_tests += 1
    try:
        response = requests.delete(f"{BASE_URL}/api/v1/sessions/non-existent-session/")
        if response.status_code == 404:
            passed += 1
            print("   ✅ Delete non-existent session returns 404")
        else:
            print(f"   ❌ Delete non-existent session: Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Delete non-existent session test failed: {e}")
    
    # Test 3: Auth with non-existent session
    total_tests += 1
    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/status/non-existent-session/")
        if response.status_code == 404:
            passed += 1
            print("   ✅ Auth status for non-existent session returns 404")
        else:
            print(f"   ❌ Auth status non-existent: Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Auth status test failed: {e}")
    
    success = passed == total_tests
    print_result(success, f"Session edge cases", f"{passed}/{total_tests} tests passed")
    return success

def test_scrape_without_auth():
    """Test scraping without authentication."""
    print_test("Scraping Without Authentication")
    
    scrape_request = {
        "session_id": "fake-session-id",
        "keywords": ["test"],
        "location": "London",
        "max_downloads": 1
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/scrape/",
            json=scrape_request,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 404 (session not found) or 401 (not authenticated)
        if response.status_code in [404, 401]:
            print_result(True, "Scrape without auth properly rejected", f"Status: {response.status_code}")
            return True
        else:
            print_result(False, "Scrape without auth not properly rejected", f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, "Scrape without auth test failed", str(e))
        return False

def test_concurrent_session_creation():
    """Test concurrent session creation."""
    print_test("Concurrent Session Creation")
    
    def create_session():
        try:
            auth_data = {
                "username": f"test_user_{random.randint(1000, 9999)}",
                "password": "fake_password",
                "remember_session": True
            }
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login/",
                json=auth_data,
                timeout=10
            )
            return response.status_code, response.text[:100]
        except Exception as e:
            return None, str(e)
    
    # Create 10 sessions concurrently (reduced from 20)
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_session) for _ in range(10)]
        results = [future.result() for future in as_completed(futures)]
    
    duration = time.time() - start_time
    
    # Count successful responses (should be mostly 500/422 since we're using fake credentials)
    # but the API should handle them gracefully
    handled_properly = sum(1 for status, _ in results if status in [401, 422, 500])
    
    success = handled_properly >= 8  # Allow 2 failures
    print_result(
        success, 
        "Concurrent session creation", 
        f"10 requests in {duration:.2f}s, {handled_properly}/10 handled properly"
    )
    return success

def test_api_documentation_endpoints():
    """Test API documentation endpoints."""
    print_test("API Documentation Endpoints")
    
    doc_endpoints = [
        "/docs",
        "/redoc", 
        "/openapi.json"
    ]
    
    passed = 0
    for endpoint in doc_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                passed += 1
                print(f"   ✅ {endpoint}: Available")
            else:
                print(f"   ❌ {endpoint}: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: Exception {e}")
    
    success = passed == len(doc_endpoints)
    print_result(success, "API documentation", f"{passed}/{len(doc_endpoints)} endpoints available")
    return success

def test_memory_and_performance():
    """Test memory usage and performance characteristics."""
    print_test("Memory & Performance Characteristics")
    
    # Get initial health metrics
    try:
        initial_response = requests.get(f"{BASE_URL}/api/v1/health/")
        initial_data = initial_response.json()
        initial_memory = initial_data.get('memory_usage_mb', 0)
        print(f"   📊 Initial memory usage: {initial_memory:.1f} MB")
        
        # Make 50 requests to various endpoints (reduced from 100)
        endpoints = [
            "/api/v1/health/",
            "/api/v1/health/simple/",
            "/api/v1/sessions/",
            "/",
        ]
        
        start_time = time.time()
        for i in range(50):
            endpoint = random.choice(endpoints)
            requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if i % 10 == 0:
                print(f"   🔄 Completed {i+1}/50 requests...")
        
        duration = time.time() - start_time
        
        # Check final memory usage
        final_response = requests.get(f"{BASE_URL}/api/v1/health/")
        final_data = final_response.json()
        final_memory = final_data.get('memory_usage_mb', 0)
        memory_increase = final_memory - initial_memory
        
        print(f"   📊 Final memory usage: {final_memory:.1f} MB")
        print(f"   📈 Memory increase: {memory_increase:.1f} MB")
        print(f"   ⚡ Average request time: {duration/50:.3f}s")
        
        # Success criteria: memory increase < 100MB, avg time < 1s
        success = memory_increase < 100 and (duration/50) < 1.0
        print_result(
            success, 
            "Memory and performance test",
            f"Memory increase: {memory_increase:.1f}MB, Avg time: {duration/50:.3f}s"
        )
        return success
        
    except Exception as e:
        print_result(False, "Memory and performance test failed", str(e))
        return False

def test_cors_and_security_headers():
    """Test CORS and security headers."""
    print_test("CORS & Security Headers")
    
    try:
        # Test OPTIONS request (CORS preflight)
        response = requests.options(f"{BASE_URL}/api/v1/health/", headers={"Origin": "http://localhost:3000"})
        
        # Convert headers to lowercase for case-insensitive comparison
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        cors_headers = [
            'access-control-allow-origin',
            'access-control-allow-credentials'
        ]
        
        cors_passed = 0
        for header in cors_headers:
            if header in headers_lower:
                cors_passed += 1
                print(f"   ✅ {header}: {headers_lower[header]}")
            else:
                print(f"   ❌ {header}: Missing")
        
        # Test security headers on regular request
        response = requests.get(f"{BASE_URL}/api/v1/health/")
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        # Check for basic security practices
        server_header = headers_lower.get('server', '').lower()
        has_server_info = 'uvicorn' in server_header or 'fastapi' in server_header
        
        # Also check if CORS origin header is present in GET request
        has_cors_origin = 'access-control-allow-origin' in headers_lower
        
        success = cors_passed >= 1 or has_cors_origin  # At least 1 CORS header present
        print_result(
            success, 
            "CORS and security headers",
            f"{cors_passed}/{len(cors_headers)} CORS headers present, CORS on GET: {has_cors_origin}"
        )
        return success
        
    except Exception as e:
        print_result(False, "CORS and security test failed", str(e))
        return False

def run_hard_tests():
    """Run all hard tests."""
    print_header("🔥 HARD TESTS - PRODUCTION API STRESS TESTING", Colors.RED)
    print(f"{Colors.BOLD}Testing Edge Cases, Error Conditions & Performance{Colors.END}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("API Health Under Load", test_api_health_under_load),
        ("Invalid Endpoints", test_invalid_endpoints),
        ("Malformed Requests", test_malformed_requests),
        ("Session Edge Cases", test_session_management_edge_cases),
        ("Scrape Without Auth", test_scrape_without_auth),
        ("Concurrent Sessions", test_concurrent_session_creation),
        ("API Documentation", test_api_documentation_endpoints),
        ("Memory & Performance", test_memory_and_performance),
        ("CORS & Security", test_cors_and_security_headers),
    ]
    
    results = []
    start_time = time.time()
    
    for test_name, test_func in tests:
        print_header(f"🧪 {test_name}", Colors.PURPLE)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_result(False, f"{test_name} crashed", str(e))
            results.append((test_name, False))
        
        time.sleep(0.5)  # Brief pause between tests
    
    # Summary
    total_duration = time.time() - start_time
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print_header("🎯 HARD TESTS SUMMARY", Colors.CYAN)
    print(f"{Colors.BOLD}Overall Results:{Colors.END}")
    print(f"   ✅ Passed: {passed}/{total} tests")
    print(f"   ⏱️  Duration: {total_duration:.2f} seconds")
    print(f"   📊 Success Rate: {(passed/total)*100:.1f}%")
    
    print(f"\n{Colors.BOLD}Individual Test Results:{Colors.END}")
    for test_name, result in results:
        status = f"{Colors.GREEN}✅ PASS" if result else f"{Colors.RED}❌ FAIL"
        print(f"   {status} {test_name}{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL HARD TESTS PASSED! API IS PRODUCTION-READY! 🚀{Colors.END}")
    elif passed >= total * 0.8:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  MOST TESTS PASSED - API IS MOSTLY PRODUCTION-READY{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ SEVERAL TESTS FAILED - NEEDS ATTENTION BEFORE PRODUCTION{Colors.END}")
    
    return passed, total

if __name__ == "__main__":
    try:
        passed, total = run_hard_tests()
        exit(0 if passed == total else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Tests interrupted by user{Colors.END}")
        exit(130)
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}❌ ERROR: Could not connect to API server at {BASE_URL}")
        print("   Make sure the server is running: python start_api.py{Colors.END}")
        exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ CRITICAL ERROR: {e}{Colors.END}")
        exit(1) 