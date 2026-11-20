"""
Test API cache with simple requests.
"""

import requests
import time

API_BASE = "http://localhost:8000"

print("Testing API cache...")
print("=" * 70)

# Test 1: First request
print("\n1. First request (should miss cache):")
response1 = requests.post(
    f"{API_BASE}/search",
    json={"query": "robot manipulation", "k": 3}
)
result1 = response1.json()
print(f"   Cache hit: {result1.get('cache_hit')}")
print(f"   Time: {result1.get('search_time_ms'):.2f}ms")
print(f"   Results: {result1.get('total_results')}")

time.sleep(1)

# Test 2: Same request (should hit cache)
print("\n2. Second request - SAME QUERY (should hit cache):")
response2 = requests.post(
    f"{API_BASE}/search",
    json={"query": "robot manipulation", "k": 3}
)
result2 = response2.json()
print(f"   Cache hit: {result2.get('cache_hit')}")
print(f"   Time: {result2.get('search_time_ms'):.2f}ms")
print(f"   Results: {result2.get('total_results')}")

# Test 3: Cache stats
print("\n3. Cache statistics:")
stats_response = requests.get(f"{API_BASE}/cache/stats")
stats = stats_response.json()
print(f"   Enabled: {stats.get('enabled')}")
print(f"   Hits: {stats.get('hits')}")
print(f"   Misses: {stats.get('misses')}")
print(f"   Hit rate: {stats.get('hit_rate_percent'):.1f}%")

print("\n" + "=" * 70)

if result2.get('cache_hit'):
    print("✓ SUCCESS: Cache is working!")
else:
    print("✗ FAIL: Cache not hitting")
