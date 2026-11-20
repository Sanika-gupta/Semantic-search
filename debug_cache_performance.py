"""
Debug cache performance to understand why it's slow.
"""

import time
import redis
import os
from dotenv import load_dotenv
from cache import RedisCache, SemanticCache
import numpy as np

load_dotenv()

print("="*70)
print("CACHE PERFORMANCE DEBUG")
print("="*70)

# Connect to Redis
redis_client = redis.Redis.from_url(os.getenv('REDIS_URI'), decode_responses=True)
redis_cache = RedisCache(redis_client, prefix="perf_test")

# Test 1: Raw Redis performance
print("\n1. Testing raw Redis performance...")
test_data = {"test": "data", "number": 123, "list": [1, 2, 3]}

latencies = []
for i in range(10):
    start = time.time()
    redis_cache.set(f"test_key_{i}", test_data, ttl=60)
    latency = (time.time() - start) * 1000
    latencies.append(latency)

print(f"   Redis SET latency: {np.mean(latencies):.2f}ms (avg)")

latencies = []
for i in range(10):
    start = time.time()
    result = redis_cache.get(f"test_key_0")
    latency = (time.time() - start) * 1000
    latencies.append(latency)

print(f"   Redis GET latency: {np.mean(latencies):.2f}ms (avg)")

# Test 2: Cache with embedding
print("\n2. Testing semantic cache operations...")
semantic_cache = SemanticCache(redis_cache, similarity_threshold=0.95, ttl=3600)

fake_embedding = np.random.rand(384).astype(np.float32)
fake_results = [{"title": f"Paper {i}", "score": 0.9} for i in range(5)]

# SET operation
start = time.time()
semantic_cache.set("test query", fake_embedding, fake_results)
set_latency = (time.time() - start) * 1000
print(f"   Cache SET: {set_latency:.2f}ms")

# GET operation (should hit)
start = time.time()
result = semantic_cache.get("test query", fake_embedding)
get_latency = (time.time() - start) * 1000
print(f"   Cache GET (hit): {get_latency:.2f}ms")

# Test 3: Compare search with/without cache more carefully
print("\n3. Controlled search test...")
from embeddings import EmbeddingGenerator, VectorStore
from ingestion import MongoDBClient
from api.search_service import SearchService

embedder = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')
vector_store = VectorStore.load('data/indexes/faiss_index.bin', 'data/indexes/metadata.pkl')
mongo_client = MongoDBClient()

# Create fresh cache
fresh_cache = SemanticCache(
    RedisCache(redis_client, prefix="fresh_test"),
    similarity_threshold=0.95,
    ttl=3600
)

search_service = SearchService(
    vector_store=vector_store,
    embedder=embedder,
    mongo_client=mongo_client,
    semantic_cache=fresh_cache
)

query = "robot manipulation"

# First call - cache miss
print(f"\n   Query: '{query}'")
start = time.time()
results1, time1, hit1 = search_service.search(query, k=5)
total_latency1 = (time.time() - start) * 1000
print(f"   First call (miss): {total_latency1:.2f}ms (reported: {time1:.2f}ms, cache: {hit1})")

# Second call - should hit cache
start = time.time()
results2, time2, hit2 = search_service.search(query, k=5)
total_latency2 = (time.time() - start) * 1000
print(f"   Second call (hit): {total_latency2:.2f}ms (reported: {time2:.2f}ms, cache: {hit2})")

if hit2:
    improvement = ((total_latency1 - total_latency2) / total_latency1) * 100
    print(f"   Improvement: {improvement:.1f}%")
else:
    print(f"   ✗ Cache did not hit!")

# Test 4: Break down where time is spent
print("\n4. Breaking down search service time...")

# Time just the embedding
start = time.time()
embedding = embedder.generate_query_embedding(query)
embed_time = (time.time() - start) * 1000
print(f"   Embedding generation: {embed_time:.2f}ms")

# Time just FAISS search
start = time.time()
paper_ids, scores = vector_store.search(embedding, k=5)
faiss_time = (time.time() - start) * 1000
print(f"   FAISS search: {faiss_time:.2f}ms")

# Time just MongoDB fetch
start = time.time()
for paper_id in paper_ids[:5]:
    paper = mongo_client.get_paper_by_arxiv_id(paper_id)
mongo_time = (time.time() - start) * 1000
print(f"   MongoDB fetch (5 papers): {mongo_time:.2f}ms")

total_expected = embed_time + faiss_time + mongo_time
print(f"   Total expected (no cache): {total_expected:.2f}ms")

# Time cache GET
start = time.time()
cached = fresh_cache.get(query, embedding)
cache_get_time = (time.time() - start) * 1000
print(f"   Cache GET: {cache_get_time:.2f}ms")

print("\n5. Analysis:")
print(f"   If cache GET ({cache_get_time:.2f}ms) < full search ({total_expected:.2f}ms):")
print(f"   Cache is FASTER by {total_expected - cache_get_time:.2f}ms")
print(f"   Speedup: {((total_expected - cache_get_time) / total_expected * 100):.1f}%")

mongo_client.close()
