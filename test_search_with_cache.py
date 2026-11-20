"""
Test search service with semantic cache - direct component test.
"""

import os
import redis
from dotenv import load_dotenv
from embeddings import EmbeddingGenerator, VectorStore
from ingestion import MongoDBClient
from cache import RedisCache, SemanticCache
from api.search_service import SearchService

load_dotenv()

print("=" * 70)
print("SEARCH SERVICE CACHE TEST")
print("=" * 70)

# Setup components
print("\n1. Loading components...")

print("   - Embedding model...")
embedder = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')

print("   - FAISS index...")
vector_store = VectorStore.load('data/indexes/faiss_index.bin', 'data/indexes/metadata.pkl')

print("   - MongoDB...")
mongo_client = MongoDBClient()

print("   - Redis...")
redis_client = redis.Redis.from_url(os.getenv('REDIS_URI'), decode_responses=True)
redis_client.ping()

print("   - Semantic cache...")
redis_cache = RedisCache(redis_client, prefix="search_cache")
semantic_cache = SemanticCache(
    redis_cache=redis_cache,
    similarity_threshold=0.95,
    ttl=3600
)

print("   - Search service...")
search_service = SearchService(
    vector_store=vector_store,
    embedder=embedder,
    mongo_client=mongo_client,
    semantic_cache=semantic_cache
)

print("✓ All components loaded\n")

# Test search with cache
query = "robot manipulation"

print("=" * 70)
print(f"QUERY: '{query}'")
print("=" * 70)

print("\n2. First search (should miss cache):")
results1, time1, cache_hit1 = search_service.search(query, k=3)
print(f"   Results: {len(results1)}")
print(f"   Time: {time1:.2f}ms")
print(f"   Cache hit: {cache_hit1}")
print(f"   Top result: {results1[0]['title'][:60]}...")

print("\n3. Second search - SAME QUERY (should hit cache):")
results2, time2, cache_hit2 = search_service.search(query, k=3)
print(f"   Results: {len(results2)}")
print(f"   Time: {time2:.2f}ms")
print(f"   Cache hit: {cache_hit2}")

print("\n4. Cache stats:")
stats = semantic_cache.get_stats()
print(f"   Hits: {stats['hits']}")
print(f"   Misses: {stats['misses']}")
print(f"   Hit rate: {stats['hit_rate_percent']:.1f}%")

print("\n" + "=" * 70)
if cache_hit2:
    print("✓ SUCCESS: Search service cache is working!")
    print(f"  Latency improvement: {time1:.2f}ms → {time2:.2f}ms")
else:
    print("✗ FAIL: Cache should have hit on second request")

mongo_client.close()
