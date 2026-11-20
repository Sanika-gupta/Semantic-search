"""
Embedding generation using sentence-transformers.
"""

import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """Generate embeddings for papers using sentence-transformers."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize embedding generator.

        Args:
            model_name: Name of the sentence-transformers model
                       Options: 'all-MiniLM-L6-v2' (faster, 384 dims)
                               'all-mpnet-base-v2' (better quality, 768 dims)
        """
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def generate_paper_embedding(self, paper: Dict) -> np.ndarray:
        """
        Generate embedding for a single paper.

        Args:
            paper: Paper dictionary with 'title' and 'abstract'

        Returns:
            Embedding vector as numpy array
        """
        text = self._create_paper_text(paper)
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def generate_batch_embeddings(
        self,
        papers: List[Dict],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple papers in batches.

        Args:
            papers: List of paper dictionaries
            batch_size: Number of papers to process at once
            show_progress: Whether to show progress bar

        Returns:
            Array of embeddings (n_papers, embedding_dim)
        """
        texts = [self._create_paper_text(paper) for paper in papers]

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        return embeddings

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate embedding for a search query.

        Args:
            query: Search query string

        Returns:
            Query embedding vector
        """
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding

    def _create_paper_text(self, paper: Dict) -> str:
        """
        Create text representation of paper for embedding.

        Combines title and abstract with title given more weight.
        """
        title = paper.get('title', '').strip()
        abstract = paper.get('abstract', '').strip()

        # Weight title more by repeating it
        text = f"{title}. {title}. {abstract}"
        return text

    def get_embedding_dim(self) -> int:
        """Get the dimension of the embeddings."""
        return self.embedding_dim

    def get_model_name(self) -> str:
        """Get the name of the model being used."""
        return self.model_name
