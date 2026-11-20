#!/usr/bin/env python3
"""
Test script for Phase 2 - Embeddings and Search.
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import MongoDBClient
from embeddings import EmbeddingGenerator, VectorStore


def test_mongodb_connection():
    """Test MongoDB connection and data availability."""
    print("\n" + "=" * 60)
    print("Test 1: MongoDB Connection and Data")
    print("=" * 60)

    try:
        client = MongoDBClient()
        count = client.get_paper_count()

        if count == 0:
            print("✗ No papers in MongoDB")
            print("  Run: python ingest_arxiv.py")
            client.close()
            return False

        print(f"✓ MongoDB connected")
        print(f"✓ Found {count} papers")

        # Get sample paper
        papers = client.get_papers(limit=1)
        if papers:
            paper = papers[0]
            print(f"✓ Sample paper: {paper['title'][:60]}...")

        client.close()
        return True

    except Exception as e:
        print(f"✗ MongoDB test failed: {e}")
        return False


def test_embedding_generation():
    """Test embedding generation."""
    print("\n" + "=" * 60)
    print("Test 2: Embedding Generation")
    print("=" * 60)

    try:
        # Initialize embedder
        embedder = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')
        print(f"✓ Loaded model: {embedder.get_model_name()}")
        print(f"✓ Embedding dimension: {embedder.get_embedding_dim()}")

        # Test single paper embedding
        test_paper = {
            'title': 'Vision-Language-Action Models for Robot Control',
            'abstract': 'We present a novel approach to robot manipulation using vision-language-action models.'
        }

        embedding = embedder.generate_paper_embedding(test_paper)
        print(f"✓ Generated paper embedding: shape {embedding.shape}")

        # Test query embedding
        query = "robot manipulation with vision language models"
        query_emb = embedder.generate_query_embedding(query)
        print(f"✓ Generated query embedding: shape {query_emb.shape}")

        return True

    except Exception as e:
        print(f"✗ Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test vector store creation and search."""
    print("\n" + "=" * 60)
    print("Test 3: Vector Store and Search")
    print("=" * 60)

    try:
        # Get papers from MongoDB
        mongo_client = MongoDBClient()
        papers = mongo_client.get_papers(limit=100)  # Test with 100 papers

        if not papers:
            print("✗ No papers to test with")
            return False

        print(f"✓ Loaded {len(papers)} papers for testing")

        # Generate embeddings
        embedder = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')
        print("  Generating embeddings...")

        embeddings = embedder.generate_batch_embeddings(papers, show_progress=False)
        print(f"✓ Generated embeddings: shape {embeddings.shape}")

        # Create vector store
        vector_store = VectorStore(embedding_dim=embedder.get_embedding_dim())
        paper_ids = [p['arxiv_id'] for p in papers]
        vector_store.add_embeddings(embeddings, paper_ids)
        print(f"✓ Created vector store with {vector_store.get_size()} papers")

        # Test search
        test_queries = [
            "robot manipulation with vision language models",
            "humanoid locomotion",
            "diffusion policy"
        ]

        for query in test_queries:
            query_emb = embedder.generate_query_embedding(query)
            result_ids, scores = vector_store.search(query_emb, k=3)

            print(f"\n  Query: '{query}'")
            for i, (paper_id, score) in enumerate(zip(result_ids, scores), 1):
                paper = mongo_client.get_paper_by_arxiv_id(paper_id)
                print(f"    {i}. [{score:.4f}] {paper['title'][:60]}...")

        mongo_client.close()
        return True

    except Exception as e:
        print(f"✗ Vector store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_index_persistence():
    """Test saving and loading index."""
    print("\n" + "=" * 60)
    print("Test 4: Index Persistence")
    print("=" * 60)

    try:
        import tempfile
        import shutil

        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        print(f"  Using temp directory: {temp_dir}")

        # Get papers
        mongo_client = MongoDBClient()
        papers = mongo_client.get_papers(limit=50)

        # Generate embeddings
        embedder = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')
        embeddings = embedder.generate_batch_embeddings(papers, show_progress=False)

        # Create and save vector store
        vector_store = VectorStore(embedding_dim=embedder.get_embedding_dim())
        paper_ids = [p['arxiv_id'] for p in papers]
        vector_store.add_embeddings(embeddings, paper_ids)

        index_path = os.path.join(temp_dir, 'test_index.bin')
        metadata_path = os.path.join(temp_dir, 'test_metadata.pkl')

        vector_store.save(index_path, metadata_path)
        print(f"✓ Saved index to {index_path}")

        # Load index
        loaded_store = VectorStore.load(index_path, metadata_path)
        print(f"✓ Loaded index with {loaded_store.get_size()} papers")

        # Test search on loaded index
        query = "robot learning"
        query_emb = embedder.generate_query_embedding(query)
        result_ids, scores = loaded_store.search(query_emb, k=3)

        print(f"\n  Test search on loaded index:")
        print(f"  Query: '{query}'")
        for i, (paper_id, score) in enumerate(zip(result_ids, scores), 1):
            paper = mongo_client.get_paper_by_arxiv_id(paper_id)
            print(f"    {i}. [{score:.4f}] {paper['title'][:60]}...")

        # Cleanup
        shutil.rmtree(temp_dir)
        mongo_client.close()

        return True

    except Exception as e:
        print(f"✗ Index persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Phase 2 Test Suite - Embeddings and Search")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("MongoDB Connection", test_mongodb_connection()))
    results.append(("Embedding Generation", test_embedding_generation()))
    results.append(("Vector Store & Search", test_vector_store()))
    results.append(("Index Persistence", test_index_persistence()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("1. Run: python build_index.py")
        print("2. Run: python run_api.py")
        print("3. Test API at: http://localhost:8000/docs")
    else:
        print("✗ Some tests failed")
        print("\nPlease fix the issues above before proceeding")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
