"""
Redis client wrapper for caching.
"""

import json
import redis
from typing import Optional, Any
from datetime import datetime


class RedisCache:
    """Redis-backed cache with JSON serialization."""

    def __init__(self, redis_client: redis.Redis, prefix: str = "cache"):
        """
        Initialize Redis cache.

        Args:
            redis_client: Redis client instance
            prefix: Key prefix for namespacing
        """
        self.redis = redis_client
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/error
        """
        try:
            value = self.redis.get(self._make_key(key))
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value, default=self._json_serializer)
            self.redis.setex(
                self._make_key(key),
                ttl,
                serialized
            )
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    @staticmethod
    def _json_serializer(obj):
        """Custom JSON serializer for objects not serializable by default."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            self.redis.delete(self._make_key(key))
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            return bool(self.redis.exists(self._make_key(key)))
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    def scan_keys(self, pattern: str = "*", count: int = 100) -> list[str]:
        """
        Scan cache keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "query:*")
            count: Number of keys to return per scan

        Returns:
            List of matching keys (without prefix)
        """
        try:
            full_pattern = f"{self.prefix}:{pattern}"
            cursor = 0
            keys = []
            prefix_len = len(self.prefix) + 1  # +1 for the colon

            while True:
                cursor, batch = self.redis.scan(
                    cursor,
                    match=full_pattern,
                    count=count
                )
                # Remove prefix from keys
                keys.extend([key[prefix_len:] for key in batch])

                if cursor == 0 or len(keys) >= count:
                    break

            return keys
        except Exception as e:
            print(f"Cache scan error: {e}")
            return []

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        try:
            info = self.redis.info('stats')
            return {
                'total_keys': self.redis.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100
