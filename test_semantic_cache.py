"""
Test script for semantic cache functionality.

This demonstrates the difference between traditional caching and semantic caching:
- Traditional cache: exact string match only
- Semantic cache: similarity-based matching

Example:
  Query 1: "robot manipulation with vision language models"
  Query 2: "robotic grasping using VLMs"

  Traditional cache: MISS (different strings)
  Semantic cache: HIT (similar embeddings)
"""

import requests
import time
from typing import List, Dict


API_BASE = "http://localhost:8000"


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def print_section(text: str):
    """Print formatted section."""
    print(f"\n{text}")
    print("-" * 70)


def search(query: str, k: int = 5) -> Dict:
    """Perform search and return response."""
    response = requests.post(
        f"{API_BASE}/search",
        json={"query": query, "k": k}
    )
    response.raise_for_status()
    return response.json()


def get_cache_stats() -> Dict:
    """Get cache statistics."""
    response = requests.get(f"{API_BASE}/cache/stats")
    response.raise_for_status()
    return response.json()


def print_search_result(query: str, result: Dict):
    """Print search result summary."""
    cache_hit = result.get('cache_hit', False)
    cache_status = "✓ CACHE HIT" if cache_hit else "✗ CACHE MISS"

    print(f"Query: \"{query}\"")
    print(f"Status: {cache_status}")
    print(f"Time: {result['search_time_ms']:.2f}ms")
    print(f"Results: {result['total_results']}")

    if result['results']:
        print(f"Top result: {result['results'][0]['title'][:80]}...")


def test_exact_match():
    """Test 1: Exact query match (should hit cache on second request)."""
    print_header("TEST 1: Exact Query Match")

    query = "robot manipulation with vision language models"

    print_section("First request (should miss cache)")
    result1 = search(query)
    print_search_result(query, result1)

    time.sleep(0.5)

    print_section("Second request - SAME QUERY (should hit cache)")
    result2 = search(query)
    print_search_result(query, result2)

    # Verify cache hit
    if result2.get('cache_hit'):
        print("\n✓ PASS: Exact match cache working!")
    else:
        print("\n✗ FAIL: Should have hit cache")


def test_semantic_similarity():
    """Test 2: Similar but different queries (semantic cache test)."""
    print_header("TEST 2: Semantic Similarity Cache")

    queries = [
        "robot manipulation with vision language models",
        "robotic grasping using VLMs",  # Similar meaning, different words
        "vision language action models for manipulation"  # Very similar
    ]

    for i, query in enumerate(queries, 1):
        print_section(f"Request {i}: \"{query}\"")
        result = search(query)
        print_search_result(query, result)
        time.sleep(0.5)

    print("\nNote: Queries 2 and 3 may hit cache if semantically similar enough")
    print(f"(threshold = 0.95 by default)")


def test_different_topics():
    """Test 3: Completely different topics (should not share cache)."""
    print_header("TEST 3: Different Topics (No Cache Sharing)")

    queries = [
        "humanoid locomotion and balance control",
        "diffusion policy for robot learning",
        "world models for robotic planning"
    ]

    for i, query in enumerate(queries, 1):
        print_section(f"Request {i}: \"{query}\"")
        result = search(query)
        print_search_result(query, result)
        time.sleep(0.5)

    print("\nNote: Different topics should not share cache entries")


def test_cache_stats():
    """Display final cache statistics."""
    print_header("CACHE STATISTICS")

    stats = get_cache_stats()

    if not stats.get('enabled'):
        print("Cache is DISABLED")
        return

    print(f"Cache Enabled: {stats['enabled']}")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Cache Hits: {stats['hits']}")
    print(f"  - Exact Matches: {stats['exact_hits']}")
    print(f"  - Similarity Matches: {stats['similarity_hits']}")
    print(f"Cache Misses: {stats['misses']}")
    print(f"Hit Rate: {stats['hit_rate_percent']:.1f}%")
    print(f"Similarity Threshold: {stats['similarity_threshold']}")

    if stats['similarity_hits'] > 0:
        print("\n✓ SUCCESS: Semantic cache is working!")
        print("  Similar queries are sharing cache entries!")
    else:
        print("\nNote: No similarity hits yet. Try more similar queries.")


def main():
    """Run all tests."""
    print_header("SEMANTIC CACHE TEST SUITE")
    print("This demonstrates semantic-aware caching vs traditional caching")

    # Check if API is running
    try:
        response = requests.get(f"{API_BASE}/health")
        response.raise_for_status()
        print("✓ API is running")
    except Exception as e:
        print(f"✗ Error: API not running at {API_BASE}")
        print(f"  Start the API with: python run_api.py")
        return

    # Run tests
    try:
        test_exact_match()
        test_semantic_similarity()
        test_different_topics()
        test_cache_stats()

        print_header("TESTS COMPLETE")
        print("\nKey Takeaways:")
        print("1. Exact queries hit cache immediately")
        print("2. Similar queries can share cache (if similarity > threshold)")
        print("3. Different topics don't interfere with each other")
        print("4. Cache reduces latency for repeated/similar queries")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error during testing: {e}")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")


if __name__ == "__main__":
    main()
