"""
Direct test of semantic cache functionality.
"""

import redis
import numpy as np
from cache import RedisCache, SemanticCache
from dotenv import load_dotenv
import os

load_dotenv()

print("=" * 70)
print("DIRECT CACHE TEST")
print("=" * 70)

# Connect to Redis
print("\n1. Connecting to Redis...")
redis_uri = os.getenv('REDIS_URI')
print(f"URI: {redis_uri[:50]}...")

redis_client = redis.Redis.from_url(redis_uri, decode_responses=True)
redis_client.ping()
print("✓ Redis connected")

# Create cache instances
print("\n2. Creating cache instances...")
redis_cache = RedisCache(redis_client, prefix="test_cache")
semantic_cache = SemanticCache(
    redis_cache=redis_cache,
    similarity_threshold=0.95,
    ttl=3600
)
print("✓ Cache instances created")

# Test 1: Basic Redis operations
print("\n3. Testing basic Redis operations...")
test_key = "test_key_123"
test_value = {"message": "hello", "count": 42}

success = redis_cache.set(test_key, test_value, ttl=60)
print(f"Set operation: {success}")

retrieved = redis_cache.get(test_key)
print(f"Get operation: {retrieved}")

if retrieved == test_value:
    print("✓ Basic Redis get/set working")
else:
    print("✗ Redis get/set FAILED")

# Test 2: Semantic cache set
print("\n4. Testing semantic cache set...")
query = "robot manipulation"
fake_embedding = np.random.rand(384).astype(np.float32)
fake_results = [
    {"title": "Paper 1", "score": 0.9},
    {"title": "Paper 2", "score": 0.8}
]

success = semantic_cache.set(query, fake_embedding, fake_results)
print(f"Semantic cache set: {success}")

# Test 3: Semantic cache get (exact match)
print("\n5. Testing semantic cache get (exact match)...")
cached = semantic_cache.get(query, fake_embedding)
if cached:
    results, is_exact = cached
    print(f"✓ Cache hit! Exact match: {is_exact}")
    print(f"  Retrieved {len(results)} results")
else:
    print("✗ Cache miss (should have hit)")

# Test 4: Same query again
print("\n6. Testing second retrieval of same query...")
cached2 = semantic_cache.get(query, fake_embedding)
if cached2:
    results, is_exact = cached2
    print(f"✓ Cache hit! Exact match: {is_exact}")
else:
    print("✗ Cache miss (should have hit)")

# Test 5: Check stats
print("\n7. Cache statistics:")
stats = semantic_cache.get_stats()
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")

# Test 6: List Redis keys
print("\n8. Checking Redis keys...")
all_keys = redis_cache.scan_keys("*", count=100)
print(f"Found {len(all_keys)} keys with prefix 'test_cache':")
for key in all_keys[:5]:
    print(f"  - {key}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
