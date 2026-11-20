"""Manual test script for rate limiter functionality.

This script tests the 
rate limiter with a running Redis instance and API server.

Prerequisites:
1. Redis running: redis-server
2. API running: python run_api.py
3. Environment configured with REDIS_URI

Usage:
    python test_rate_limiter_manual.py
"""

import requests
import time
import sys
from typing import List, Dict

API_URL = "http://localhost:8000"


def test_basic_search():
    """Test basic search functionality."""
    print("\n=== Test 1: Basic Search ===")
    response = requests.post(
        f"{API_URL}/search",
        json={"query": "robot manipulation", "k": 5}
    )

    print(f"Status: {response.status_code}")
    print(f"Headers:")
    for header in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
        print(f"  {header}: {response.headers.get(header, 'N/A')}")

    if response.status_code == 200:
        data = response.json()
        print(f"Results: {data['total_results']}")
        print("✓ Basic search working")
    else:
        print(f"✗ Failed: {response.text}")

    return response.status_code == 200


def test_burst_then_throttle():
    """Test burst capacity followed by rate limiting."""
    print("\n=== Test 2: Burst Then Throttle ===")

    results = []
    for i in range(25):  # More than capacity (20)
        response = requests.post(
            f"{API_URL}/search",
            json={"query": f"test query {i}", "k": 1}
        )
        results.append({
            "request": i + 1,
            "status": response.status_code,
            "remaining": response.headers.get("X-RateLimit-Remaining", "N/A")
        })

        time.sleep(0.1)  # Small delay

    # Count successes and throttles
    success_count = sum(1 for r in results if r["status"] == 200)
    throttle_count = sum(1 for r in results if r["status"] == 429)

    print(f"Successful requests: {success_count}")
    print(f"Throttled requests (429): {throttle_count}")
    print(f"Expected: 20 success, 5 throttled")

    if success_count == 20 and throttle_count == 5:
        print("✓ Burst and throttle working correctly")
        return True
    else:
        print("✗ Unexpected behavior")
        for r in results[-5:]:
            print(f"  Request {r['request']}: {r['status']} (remaining: {r['remaining']})")
        return False


def test_retry_after_header():
    """Test Retry-After header on 429 response."""
    print("\n=== Test 3: Retry-After Header ===")

    # Exhaust limit
    for _ in range(20):
        requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})

    # Next should be throttled
    response = requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        print(f"Status: 429 (rate limited)")
        print(f"Retry-After: {retry_after} seconds")

        data = response.json()
        print(f"Error message: {data.get('message')}")
        print(f"Retry after (body): {data.get('retry_after')}")

        if retry_after:
            print("✓ Retry-After header present")
            return True
        else:
            print("✗ Retry-After header missing")
            return False
    else:
        print(f"✗ Expected 429, got {response.status_code}")
        return False


def test_excluded_paths():
    """Test that health endpoints are excluded from rate limiting."""
    print("\n=== Test 4: Excluded Paths ===")

    # Health endpoint should not be rate limited even after many requests
    success = True
    for i in range(30):  # More than capacity
        response = requests.get(f"{API_URL}/health")
        if response.status_code != 200:
            print(f"✗ Health endpoint throttled at request {i + 1}")
            success = False
            break

    if success:
        print(f"Made 30 requests to /health, all succeeded")
        print("✓ Excluded paths working correctly")

    return success


def test_refill_over_time():
    """Test that tokens refill over time."""
    print("\n=== Test 5: Token Refill Over Time ===")

    # Exhaust limit
    for _ in range(20):
        requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})

    # Should be throttled
    response = requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})
    if response.status_code != 429:
        print("✗ Expected to be throttled after exhausting limit")
        return False

    print("Throttled as expected. Waiting 12 seconds for refill...")
    print("(Rate: 10 req/min = 1/6 token per second, should refill 2 tokens)")

    time.sleep(12)

    # Should now allow 2 requests
    response1 = requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})
    response2 = requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})
    response3 = requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})

    if response1.status_code == 200 and response2.status_code == 200 and response3.status_code == 429:
        print("✓ Token refill working correctly")
        print("  - 2 requests allowed after refill")
        print("  - 3rd request throttled")
        return True
    else:
        print(f"✗ Unexpected refill behavior:")
        print(f"  Request 1: {response1.status_code}")
        print(f"  Request 2: {response2.status_code}")
        print(f"  Request 3: {response3.status_code}")
        return False


def test_different_clients():
    """Test that different IPs have separate buckets."""
    print("\n=== Test 6: Separate Client Buckets ===")

    # Client 1 exhausts limit
    for _ in range(20):
        requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})

    # Client 1 should be throttled
    response1 = requests.post(f"{API_URL}/search", json={"query": "test", "k": 1})

    # Client 2 (simulated via X-Forwarded-For) should have full capacity
    response2 = requests.post(
        f"{API_URL}/search",
        json={"query": "test", "k": 1},
        headers={"X-Forwarded-For": "192.168.1.100"}
    )

    if response1.status_code == 429 and response2.status_code == 200:
        print("✓ Client separation working correctly")
        print("  - Client 1 (localhost) throttled")
        print("  - Client 2 (192.168.1.100) allowed")
        return True
    else:
        print(f"✗ Unexpected behavior:")
        print(f"  Client 1: {response1.status_code}")
        print(f"  Client 2: {response2.status_code}")
        return False


def main():
    """Run all manual tests."""
    print("=" * 60)
    print("Rate Limiter Manual Test Suite")
    print("=" * 60)

    # Check API is running
    try:
        response = requests.get(f"{API_URL}/health/live", timeout=2)
        if response.status_code != 200:
            print(f"\n✗ API not healthy: {response.status_code}")
            print("Please start the API: python run_api.py")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Cannot connect to API at {API_URL}")
        print(f"Error: {e}")
        print("Please start the API: python run_api.py")
        sys.exit(1)

    print(f"\n✓ API running at {API_URL}")

    # Run tests
    tests = [
        ("Basic Search", test_basic_search),
        ("Burst Then Throttle", test_burst_then_throttle),
        ("Retry-After Header", test_retry_after_header),
        ("Excluded Paths", test_excluded_paths),
        ("Token Refill", test_refill_over_time),
        ("Client Separation", test_different_clients),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
