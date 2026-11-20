"""
Semantic-aware cache for search queries.

This cache is different from traditional string-based caching because it:
1. Embeds queries into vector space
2. Finds similar cached queries by cosine similarity
3. Returns cached results if similarity > threshold

Example:
    Query 1: "robot manipulation with vision language models"
    Query 2: "robotic grasping using VLMs"

    Traditional cache: MISS (different strings)
    Semantic cache: HIT (similar embeddings, similarity > 0.95)
"""

import hashlib
import json
import numpy as np
from typing import Optional, List, Dict, Tuple
from .redis_client import RedisCache


class SemanticCache:
    """
    Semantic-aware cache using query embeddings.

    Strategy:
    - Store query embeddings alongside cached results
    - On cache lookup, find the most similar cached query
    - Return cached result if similarity > threshold

    This solves the problem where semantically identical queries
    with different wording would miss in a traditional cache.
    """

    def __init__(
        self,
        redis_cache: RedisCache,
        similarity_threshold: float = 0.95,
        max_scan: int = 1000,
        ttl: int = 3600
    ):
        """
        Initialize semantic cache.

        Args:
            redis_cache: Redis cache instance
            similarity_threshold: Minimum similarity to consider a cache hit (0-1)
            max_scan: Maximum cached queries to scan for similarity
            ttl: Time to live for cache entries (seconds)
        """
        self.cache = redis_cache
        self.similarity_threshold = similarity_threshold
        self.max_scan = max_scan
        self.ttl = ttl

        # Prefix for different data types
        self.embedding_prefix = "embedding"
        self.result_prefix = "result"

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'similarity_hits': 0,  # Hits via similarity, not exact match
            'exact_hits': 0  # Hits via exact query match
        }

    def _hash_query(self, query: str) -> str:
        """Create hash of query string for exact matching."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    def _embedding_key(self, query_hash: str) -> str:
        """Create Redis key for storing query embedding."""
        return f"{self.embedding_prefix}:{query_hash}"

    def _result_key(self, query_hash: str) -> str:
        """Create Redis key for storing search results."""
        return f"{self.result_prefix}:{query_hash}"

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            a: First embedding vector
            b: Second embedding vector

        Returns:
            Cosine similarity (0-1)
        """
        # Normalize vectors
        a_norm = a / (np.linalg.norm(a) + 1e-8)
        b_norm = b / (np.linalg.norm(b) + 1e-8)

        # Dot product of normalized vectors
        return float(np.dot(a_norm, b_norm))

    def get(
        self,
        query: str,
        query_embedding: np.ndarray
    ) -> Optional[Tuple[List[Dict], bool]]:
        """
        Get cached results for query.

        Strategy:
        1. Check for exact query match (fast path)
        2. If not found, scan recent cached queries
        3. Find most similar cached query
        4. Return if similarity > threshold

        Args:
            query: Query string
            query_embedding: Query embedding vector

        Returns:
            Tuple of (cached_results, is_exact_match) or None if miss
            is_exact_match indicates if this was exact string match or similarity match
        """
        query_hash = self._hash_query(query)

        # Fast path: Check for exact query match
        result_key = self._result_key(query_hash)
        cached_result = self.cache.get(result_key)

        if cached_result is not None:
            self.stats['hits'] += 1
            self.stats['exact_hits'] += 1
            return cached_result, True

        # Similarity search: Find similar cached queries
        similar_result = self._find_similar_cached_query(
            query_embedding,
            exclude_hash=query_hash
        )

        if similar_result is not None:
            self.stats['hits'] += 1
            self.stats['similarity_hits'] += 1
            return similar_result, False

        # Cache miss
        self.stats['misses'] += 1
        return None

    def _find_similar_cached_query(
        self,
        query_embedding: np.ndarray,
        exclude_hash: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Find the most similar cached query by embedding similarity.

        Args:
            query_embedding: Query embedding to compare
            exclude_hash: Query hash to exclude from search

        Returns:
            Cached results if similar query found, None otherwise
        """
        try:
            # Scan cached embeddings
            embedding_keys = self.cache.scan_keys(
                pattern=f"{self.embedding_prefix}:*",
                count=self.max_scan
            )

            if not embedding_keys:
                return None

            # Find most similar
            best_similarity = 0.0
            best_hash = None

            for key in embedding_keys:
                # Extract query hash from key
                query_hash = key.split(':', 1)[1]

                # Skip excluded hash
                if query_hash == exclude_hash:
                    continue

                # Get cached embedding
                cached_embedding_data = self.cache.get(key)
                if cached_embedding_data is None:
                    continue

                # Deserialize embedding
                cached_embedding = np.array(
                    cached_embedding_data['embedding'],
                    dtype=np.float32
                )

                # Calculate similarity
                similarity = self._cosine_similarity(
                    query_embedding,
                    cached_embedding
                )

                # Track best match
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_hash = query_hash

            # Check if best match exceeds threshold
            if best_similarity >= self.similarity_threshold and best_hash:
                # Retrieve cached results
                cached_result = self.cache.get(self._result_key(best_hash))
                return cached_result

            return None

        except Exception as e:
            print(f"Error in similarity search: {e}")
            return None

    def set(
        self,
        query: str,
        query_embedding: np.ndarray,
        results: List[Dict]
    ) -> bool:
        """
        Cache search results with query embedding.

        Args:
            query: Query string
            query_embedding: Query embedding vector
            results: Search results to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            query_hash = self._hash_query(query)

            # Store embedding
            embedding_data = {
                'query': query,
                'embedding': query_embedding.tolist(),
                'timestamp': self._get_timestamp()
            }
            success1 = self.cache.set(
                self._embedding_key(query_hash),
                embedding_data,
                ttl=self.ttl
            )

            # Store results
            success2 = self.cache.set(
                self._result_key(query_hash),
                results,
                ttl=self.ttl
            )

            return success1 and success2

        except Exception as e:
            print(f"Error caching results: {e}")
            return False

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()

    def clear(self) -> bool:
        """
        Clear all cached queries and results.

        Returns:
            True if successful
        """
        try:
            # Get all cache keys
            embedding_keys = self.cache.scan_keys(
                pattern=f"{self.embedding_prefix}:*",
                count=10000
            )
            result_keys = self.cache.scan_keys(
                pattern=f"{self.result_prefix}:*",
                count=10000
            )

            # Delete all
            for key in embedding_keys + result_keys:
                self.cache.delete(key)

            return True

        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hit/miss stats
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = 0.0
        if total_requests > 0:
            hit_rate = (self.stats['hits'] / total_requests) * 100

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'total_requests': total_requests,
            'hit_rate_percent': hit_rate,
            'exact_hits': self.stats['exact_hits'],
            'similarity_hits': self.stats['similarity_hits'],
            'similarity_threshold': self.similarity_threshold,
            'redis_stats': self.cache.get_stats()
        }

    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'similarity_hits': 0,
            'exact_hits': 0
        }
