"""
Locust load testing for VLA Research Engine API.

Tests:
1. Search endpoint with realistic queries
2. Cache hit/miss patterns
3. Rate limiter behavior
4. Trends endpoints
5. Concurrent user load

Run:
    locust -f locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random
import json
from datetime import datetime


# Realistic query patterns based on research topics
SEARCH_QUERIES = [
    # VLA/VLM queries
    "robot manipulation with vision language models",
    "vision language action models",
    "VLA for robotic tasks",
    "VLM grounding",

    # Manipulation queries
    "robotic grasping",
    "manipulation learning",
    "dexterous manipulation",
    "object manipulation",

    # Learning methods
    "imitation learning robots",
    "reinforcement learning manipulation",
    "diffusion policy",
    "transformer for robotics",

    # Embodied AI
    "embodied AI",
    "world models robotics",
    "sim to real transfer",
    "humanoid locomotion",

    # Specific techniques
    "visual servoing",
    "6-DOF pose estimation",
    "contact-rich manipulation",
    "bimanual manipulation",
]

# Topic keywords for trends
TREND_TOPICS = ["VLA", "VLM", "manipulation", "diffusion", "transformer", "humanoid"]


class VLAResearchUser(HttpUser):
    """
    Simulates a researcher using the VLA Research Engine.

    Behavior:
    - Searches for papers (most common)
    - Checks cache stats
    - Views trends occasionally
    - Browses categories
    """

    # Wait 1-3 seconds between requests (realistic user behavior)
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a user starts."""
        self.query_history = []
        self.cache_hits = 0
        self.cache_misses = 0

    @task(10)  # Weight: 10 (most common)
    def search_papers(self):
        """Search for papers - main use case."""
        query = random.choice(SEARCH_QUERIES)

        with self.client.post(
            "/search",
            json={"query": query, "k": 5},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()

                # Track cache hits
                if data.get("cache_hit"):
                    self.cache_hits += 1
                else:
                    self.cache_misses += 1

                # Verify response structure
                if "results" in data and "search_time_ms" in data:
                    response.success()
                else:
                    response.failure("Invalid response structure")
            elif response.status_code == 429:
                # Rate limited - expected behavior
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(3)  # Weight: 3 (occasional repeat queries - tests cache)
    def search_repeat_query(self):
        """Search with a previously used query to test cache."""
        if self.query_history:
            query = random.choice(self.query_history)
        else:
            query = random.choice(SEARCH_QUERIES)
            self.query_history.append(query)

        self.client.post(
            "/search",
            json={"query": query, "k": 5},
            name="/search (repeat)"
        )

    @task(2)  # Weight: 2 (less common)
    def get_trends(self):
        """Get publication trends."""
        topic = random.choice(TREND_TOPICS)

        self.client.get(
            f"/trends?topic={topic}&interval=month",
            name="/trends"
        )

    @task(1)  # Weight: 1 (rare)
    def get_category_breakdown(self):
        """Get category breakdown."""
        self.client.get("/trends/categories")

    @task(1)  # Weight: 1 (rare)
    def get_keywords(self):
        """Get top keywords."""
        self.client.get("/trends/keywords?limit=10")

    @task(1)  # Weight: 1 (rare)
    def get_cache_stats(self):
        """Check cache statistics."""
        self.client.get("/cache/stats")

    @task(1)  # Weight: 1 (rare)
    def health_check(self):
        """Check API health."""
        self.client.get("/health")


class BurstUser(HttpUser):
    """
    Simulates burst traffic - rapid requests.

    Tests rate limiter under stress.
    """

    # Minimal wait time
    wait_time = between(0.1, 0.5)

    @task
    def rapid_search(self):
        """Rapid-fire searches to test rate limiter."""
        query = random.choice(SEARCH_QUERIES[:5])  # Use small set for cache hits

        with self.client.post(
            "/search",
            json={"query": query, "k": 3},
            catch_response=True
        ) as response:
            if response.status_code == 429:
                # Rate limited - this is expected and OK
                response.success()
            elif response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# Performance tracking
cache_hit_count = 0
cache_miss_count = 0
rate_limited_count = 0


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics."""
    global cache_hit_count, cache_miss_count, rate_limited_count

    # Track rate limiting
    if hasattr(exception, 'response') and exception.response.status_code == 429:
        rate_limited_count += 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary statistics when test stops."""
    print("\n" + "=" * 70)
    print("LOAD TEST SUMMARY")
    print("=" * 70)

    stats = environment.stats

    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.fail_ratio * 100:.2f}%")

    print(f"\nResponse Times:")
    print(f"  Median: {stats.total.median_response_time}ms")
    print(f"  Average: {stats.total.avg_response_time:.2f}ms")
    print(f"  p95: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"  p99: {stats.total.get_response_time_percentile(0.99)}ms")

    print(f"\nThroughput:")
    print(f"  Total RPS: {stats.total.total_rps:.2f} req/s")

    if rate_limited_count > 0:
        print(f"\nRate Limiting:")
        print(f"  Rate Limited Requests: {rate_limited_count}")

    print("\n" + "=" * 70)
