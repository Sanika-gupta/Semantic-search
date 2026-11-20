"""
FAISS-based vector store for similarity search.
"""

import os
import pickle
import numpy as np
import faiss
from typing import List, Tuple, Optional


class VectorStore:
    """FAISS vector store for efficient similarity search."""

    def __init__(self, embedding_dim: int):
        """
        Initialize vector store.

        Args:
            embedding_dim: Dimension of the embedding vectors
        """
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product (cosine similarity)
        self.paper_ids = []  # Maps FAISS index position to arxiv_id

    def add_embeddings(self, embeddings: np.ndarray, paper_ids: List[str]):
        """
        Add embeddings to the index.

        Args:
            embeddings: Array of embeddings (n_papers, embedding_dim)
            paper_ids: List of arXiv IDs corresponding to embeddings
        """
        # Normalize embeddings for cosine similarity
        embeddings = self._normalize(embeddings)

        self.index.add(embeddings)
        self.paper_ids.extend(paper_ids)

        print(f"Added {len(paper_ids)} embeddings to index. Total: {self.index.ntotal}")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10
    ) -> Tuple[List[str], List[float]]:
        """
        Search for similar papers.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return

        Returns:
            Tuple of (paper_ids, similarity_scores)
        """
        # Normalize query
        query_embedding = self._normalize(query_embedding.reshape(1, -1))

        # Search
        scores, indices = self.index.search(query_embedding, k)

        # Convert to lists and get paper IDs
        scores = scores[0].tolist()
        indices = indices[0].tolist()

        paper_ids = [self.paper_ids[idx] for idx in indices if idx < len(self.paper_ids)]
        scores = scores[:len(paper_ids)]

        return paper_ids, scores

    def save(self, index_path: str, metadata_path: str):
        """
        Save index and metadata to disk.

        Args:
            index_path: Path to save FAISS index
            metadata_path: Path to save metadata (paper_ids)
        """
        os.makedirs(os.path.dirname(index_path) or '.', exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, index_path)

        # Save metadata
        metadata = {
            'paper_ids': self.paper_ids,
            'embedding_dim': self.embedding_dim
        }
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)

        print(f"Saved index to {index_path}")
        print(f"Saved metadata to {metadata_path}")

    @classmethod
    def load(cls, index_path: str, metadata_path: str) -> 'VectorStore':
        """
        Load index and metadata from disk.

        Args:
            index_path: Path to FAISS index
            metadata_path: Path to metadata file

        Returns:
            Loaded VectorStore instance
        """
        # Load metadata
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)

        # Create instance
        store = cls(embedding_dim=metadata['embedding_dim'])

        # Load FAISS index
        store.index = faiss.read_index(index_path)
        store.paper_ids = metadata['paper_ids']

        print(f"Loaded index from {index_path}")
        print(f"Index contains {store.index.ntotal} embeddings")

        return store

    def _normalize(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalize embeddings to unit length for cosine similarity."""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        return embeddings / norms

    def get_size(self) -> int:
        """Get number of embeddings in the index."""
        return self.index.ntotal
