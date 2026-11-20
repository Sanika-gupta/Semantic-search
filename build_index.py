
#!/usr/bin/env python3
"""
Build embeddings and FAISS index from papers in MongoDB.
"""

import argparse
import os
from pathlib import Path
from ingestion import MongoDBClient
from embeddings import EmbeddingGenerator, VectorStore


DEFAULT_INDEX_DIR = "data/indexes"


def build_embeddings_and_index(
    model_name: str = 'all-MiniLM-L6-v2',
    index_dir: str = DEFAULT_INDEX_DIR,
    batch_size: int = 32
):
    """
    Build embeddings for all papers and create FAISS index.

    Args:
        model_name: Sentence-transformers model name
        index_dir: Directory to save index files
        batch_size: Batch size for embedding generation
    """
    print("=" * 60)
    print("Building Embeddings and FAISS Index - Phase 2")
    print("=" * 60)

    # Initialize clients
    print("\nStep 1: Loading papers from MongoDB...")
    mongo_client = MongoDBClient()
    papers = mongo_client.get_papers()

    if not papers:
        print("No papers found in MongoDB. Run: python ingest_arxiv.py")
        mongo_client.close()
        return

    print(f"Loaded {len(papers)} papers from MongoDB")

    # Initialize embedding generator
    print("\nStep 2: Initializing embedding model...")
    embedder = EmbeddingGenerator(model_name=model_name)

    # Generate embeddings
    print("\nStep 3: Generating embeddings...")
    print(f"Processing {len(papers)} papers in batches of {batch_size}")

    embeddings = embedder.generate_batch_embeddings(
        papers,
        batch_size=batch_size,
        show_progress=True
    )

    print(f"\nGenerated embeddings with shape: {embeddings.shape}")

    # Create vector store
    print("\nStep 4: Building FAISS index...")
    vector_store = VectorStore(embedding_dim=embedder.get_embedding_dim())

    paper_ids = [paper['arxiv_id'] for paper in papers]
    vector_store.add_embeddings(embeddings, paper_ids)

    # Save index
    print("\nStep 5: Saving index to disk...")
    os.makedirs(index_dir, exist_ok=True)

    index_path = os.path.join(index_dir, "faiss_index.bin")
    metadata_path = os.path.join(index_dir, "metadata.pkl")

    vector_store.save(index_path, metadata_path)

    # Save model info
    model_info_path = os.path.join(index_dir, "model_info.txt")
    with open(model_info_path, 'w') as f:
        f.write(f"Model: {model_name}\n")
        f.write(f"Embedding dimension: {embedder.get_embedding_dim()}\n")
        f.write(f"Number of papers: {len(papers)}\n")
        f.write(f"Index size: {vector_store.get_size()}\n")

    print(f"\nModel info saved to {model_info_path}")

    # Test search
    print("\n" + "=" * 60)
    print("Testing Search Functionality")
    print("=" * 60)

    test_queries = [
        "robot manipulation with vision language models",
        "humanoid locomotion learning",
        "diffusion policy for robot control"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        query_embedding = embedder.generate_query_embedding(query)
        paper_ids, scores = vector_store.search(query_embedding, k=3)

        for i, (paper_id, score) in enumerate(zip(paper_ids, scores), 1):
            paper = mongo_client.get_paper_by_arxiv_id(paper_id)
            print(f"  {i}. [{score:.4f}] {paper['title'][:80]}...")

    mongo_client.close()

    print("\n" + "=" * 60)
    print("Index Building Complete!")
    print("=" * 60)
    print(f"Index location: {index_path}")
    print(f"Ready for semantic search!")


def main():
    parser = argparse.ArgumentParser(
        description='Build embeddings and FAISS index from MongoDB papers'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='all-MiniLM-L6-v2',
        choices=['all-MiniLM-L6-v2', 'all-mpnet-base-v2'],
        help='Sentence-transformers model (default: all-MiniLM-L6-v2)'
    )
    parser.add_argument(
        '--index-dir',
        type=str,
        default=DEFAULT_INDEX_DIR,
        help=f'Directory to save index files (default: {DEFAULT_INDEX_DIR})'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for embedding generation (default: 32)'
    )

    args = parser.parse_args()

    build_embeddings_and_index(
        model_name=args.model,
        index_dir=args.index_dir,
        batch_size=args.batch_size
    )


if __name__ == '__main__':
    main()
