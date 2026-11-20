"""
Search service for semantic paper search.
"""

import time
from typing import List, Dict, Optional
from embeddings import EmbeddingGenerator, VectorStore
from ingestion import MongoDBClient


class SearchService:
    """Service for semantic search over papers."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingGenerator,
        mongo_client: MongoDBClient,
        semantic_cache: Optional['SemanticCache'] = None
    ):
        """
        Initialize search service.

        Args:
            vector_store: FAISS vector store
            embedder: Embedding generator
            mongo_client: MongoDB client
            semantic_cache: Optional semantic cache for query results
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.mongo_client = mongo_client
        self.semantic_cache = semantic_cache

    def _serialize_paper(self, paper: Dict) -> Dict:
        """
        Convert paper document to JSON-serializable format.

        Args:
            paper: Paper document from MongoDB

        Returns:
            Serialized paper with datetime converted to ISO format
        """
        from datetime import datetime
        serialized = paper.copy()

        # Convert datetime fields to ISO format strings
        for key, value in serialized.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()

        return serialized

    def search(self, query: str, k: int = 10) -> tuple[List[Dict], float, bool]:
        """
        Perform semantic search with optional caching.

        Args:
            query: Search query string
            k: Number of results to return

        Returns:
            Tuple of (results, search_time_ms, cache_hit)
        """
        start_time = time.time()
        cache_hit = False

        # Generate query embedding (needed for both cache lookup and search)
        query_embedding = self.embedder.generate_query_embedding(query)

        # Try cache first if enabled
        if self.semantic_cache:
            cached_result = self.semantic_cache.get(query, query_embedding)
            if cached_result is not None:
                results, is_exact = cached_result
                search_time = (time.time() - start_time) * 1000
                return results[:k], search_time, True  # Cache hit

        # Cache miss - perform actual search
        paper_ids, scores = self.vector_store.search(query_embedding, k=k)

        # Fetch full paper details from MongoDB
        results = []
        for paper_id, score in zip(paper_ids, scores):
            paper = self.mongo_client.get_paper_by_arxiv_id(paper_id)
            if paper:
                paper['similarity_score'] = float(score)
                # Remove MongoDB _id field
                paper.pop('_id', None)
                # Serialize datetime fields for caching
                paper = self._serialize_paper(paper)
                results.append(paper)

        # Cache the results
        if self.semantic_cache and results:
            self.semantic_cache.set(query, query_embedding, results)

        search_time = (time.time() - start_time) * 1000  # Convert to ms

        return results, search_time, cache_hit

    def get_stats(self) -> Dict:
        """Get search service statistics."""
        stats = {
            'total_papers': self.mongo_client.get_paper_count(),
            'index_size': self.vector_store.get_size(),
            'embedding_dim': self.embedder.get_embedding_dim(),
            'model_name': self.embedder.get_model_name()
        }

        # Add cache stats if available
        if self.semantic_cache:
            stats['cache'] = self.semantic_cache.get_stats()

        return stats
