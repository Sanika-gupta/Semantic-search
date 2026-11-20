"""
Automated load testing script.

Runs multiple load test scenarios and collects performance metrics.
"""

import subprocess
import time
import requests
import json
from datetime import datetime


API_BASE = "http://localhost:8000"


def check_api_health():
    """Check if API is running."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_cache_stats():
    """Get current cache statistics."""
    try:
        response = requests.get(f"{API_BASE}/cache/stats")
        return response.json()
    except:
        return {}


def reset_cache_stats():
    """Clear cache to reset statistics."""
    print("Clearing cache for clean test...")
    # Note: Would need cache clear endpoint in production
    # For now, cache stats reset on API restart


def run_load_test(users, duration, spawn_rate=10, test_name="test"):
    """
    Run a Locust load test.

    Args:
        users: Number of concurrent users
        duration: Test duration (e.g., "30s", "2m")
        spawn_rate: Users spawned per second
        test_name: Name for this test
    """
    print(f"\n{'='*70}")
    print(f"Running: {test_name}")
    print(f"Users: {users}, Duration: {duration}, Spawn Rate: {spawn_rate}/s")
    print(f"{'='*70}")

    # Get initial cache stats
    initial_cache = get_cache_stats()

    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--headless",
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", duration,
        "--host", API_BASE,
        "--html", f"load_test_{test_name}.html",
        "--only-summary"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"Error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("Test timed out")
    except FileNotFoundError:
        print("Error: Locust not installed. Run: pip install locust")
        return

    # Get final cache stats
    final_cache = get_cache_stats()

    # Calculate cache improvement
    if final_cache and initial_cache:
        print(f"\nCache Performance:")
        print(f"  Hits: {final_cache.get('hits', 0)}")
        print(f"  Misses: {final_cache.get('misses', 0)}")
        print(f"  Hit Rate: {final_cache.get('hit_rate_percent', 0):.1f}%")
        print(f"  Exact Hits: {final_cache.get('exact_hits', 0)}")
        print(f"  Similarity Hits: {final_cache.get('similarity_hits', 0)}")

    time.sleep(2)


def run_manual_performance_test():
    """
    Manual performance test without Locust.

    Measures basic performance metrics.
    """
    print("\n" + "="*70)
    print("MANUAL PERFORMANCE TEST")
    print("="*70)

    queries = [
        "robot manipulation",
        "vision language models",
        "humanoid locomotion",
        "diffusion policy",
        "imitation learning"
    ]

    print("\n1. Testing search latency (uncached)...")
    latencies = []

    for query in queries:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/search",
            json={"query": query, "k": 5}
        )
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            latencies.append(latency)
            print(f"   '{query[:30]}...': {latency:.2f}ms (cache: {data.get('cache_hit')})")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    print(f"\n   Average latency: {avg_latency:.2f}ms")

    print("\n2. Testing cache hits (repeat queries)...")
    cache_latencies = []

    for query in queries[:3]:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/search",
            json={"query": query, "k": 5}
        )
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            cache_latencies.append(latency)
            print(f"   '{query[:30]}...': {latency:.2f}ms (cache: {data.get('cache_hit')})")

    avg_cache_latency = sum(cache_latencies) / len(cache_latencies) if cache_latencies else 0
    print(f"\n   Average cached latency: {avg_cache_latency:.2f}ms")

    if avg_latency > 0 and avg_cache_latency > 0:
        improvement = ((avg_latency - avg_cache_latency) / avg_latency) * 100
        print(f"\n   Cache improvement: {improvement:.1f}%")

    print("\n3. Testing rate limiter...")
    rate_limited = 0
    successful = 0

    print("   Sending 30 rapid requests...")
    for i in range(30):
        response = requests.post(
            f"{API_BASE}/search",
            json={"query": "test", "k": 1}
        )

        if response.status_code == 429:
            rate_limited += 1
        elif response.status_code == 200:
            successful += 1

    print(f"   Successful: {successful}")
    print(f"   Rate limited: {rate_limited}")
    print(f"   Rate limiter working: {'✓' if rate_limited > 0 else '✗'}")

    print("\n4. Testing trends endpoint...")
    start = time.time()
    response = requests.get(f"{API_BASE}/trends?topic=VLA&interval=month")
    trends_latency = (time.time() - start) * 1000

    if response.status_code == 200:
        data = response.json()
        print(f"   Latency: {trends_latency:.2f}ms")
        print(f"   Periods: {len(data.get('data', []))}")
        print(f"   Total papers: {data.get('total_papers', 0)}")

    print("\n" + "="*70)
    print("MANUAL TEST COMPLETE")
    print("="*70)


def main():
    """Run all load tests."""
    print("="*70)
    print("VLA RESEARCH ENGINE - LOAD TESTING SUITE")
    print("="*70)

    # Check API is running
    print("\nChecking API health...")
    if not check_api_health():
        print("✗ Error: API is not running!")
        print("  Start the API with: python run_api.py")
        return

    print("✓ API is healthy")

    # Run manual performance test first
    run_manual_performance_test()

    # Check if Locust is available
    try:
        subprocess.run(["locust", "--version"], capture_output=True, check=True)
        has_locust = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        has_locust = False
        print("\n⚠ Locust not installed - skipping full load tests")
        print("  Install with: pip install locust")
        print("  Then run: locust -f locustfile.py --host=http://localhost:8000")
        return

    # Run load test scenarios
    print("\n" + "="*70)
    print("RUNNING LOCUST LOAD TESTS")
    print("="*70)

    # Scenario 1: Light load
    run_load_test(
        users=10,
        duration="30s",
        spawn_rate=2,
        test_name="light_load"
    )

    # Scenario 2: Medium load
    run_load_test(
        users=50,
        duration="1m",
        spawn_rate=10,
        test_name="medium_load"
    )

    # Scenario 3: Heavy load
    run_load_test(
        users=100,
        duration="1m",
        spawn_rate=20,
        test_name="heavy_load"
    )

    # Scenario 4: Burst traffic (rate limiter test)
    print("\n" + "="*70)
    print("BURST TRAFFIC TEST (Rate Limiter)")
    print("="*70)

    run_load_test(
        users=50,
        duration="30s",
        spawn_rate=50,  # Rapid spawn
        test_name="burst_traffic"
    )

    print("\n" + "="*70)
    print("ALL LOAD TESTS COMPLETE")
    print("="*70)
    print("\nGenerated reports:")
    print("  - load_test_light_load.html")
    print("  - load_test_medium_load.html")
    print("  - load_test_heavy_load.html")
    print("  - load_test_burst_traffic.html")


if __name__ == "__main__":
    main()
