#!/usr/bin/env python3
"""
Comprehensive verification script for the VLA Research Engine.
Tests all components from Phase 1 and Phase 2.
"""

import os
import sys
import time


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def check_dependencies():
    """Check if all required packages are installed."""
    print_section("Checking Dependencies")

    required_packages = [
        'pymongo',
        'requests',
        'python-dotenv',
        'fastapi',
        'uvicorn',
        'sentence_transformers',
        'faiss',
        'redis',
        'pydantic'
    ]

    missing = []

    for package in required_packages:
        try:
            if package == 'python-dotenv':
                __import__('dotenv')
            elif package == 'sentence_transformers':
                __import__('sentence_transformers')
            else:
                __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            missing.append(package)

    if missing:
        print(f"\n✗ Missing packages: {', '.join(missing)}")
        print("  Run: pip install -r requirements.txt")
        return False

    print("\n✓ All dependencies installed")
    return True


def check_environment():
    """Check environment configuration."""
    print_section("Checking Environment Configuration")

    if not os.path.exists('.env'):
        print("  ✗ .env file not found")
        print("    Run: cp .env.example .env")
        print("    Then edit .env with your MongoDB URI")
        return False

    print("  ✓ .env file exists")

    from config import settings

    print(f"  MongoDB URI: {settings.mongodb_uri[:30]}...")
    print(f"  Database: {settings.mongodb_db_name}")

    return True


def check_mongodb():
    """Check MongoDB connection and data."""
    print_section("Checking MongoDB")

    try:
        from ingestion import MongoDBClient

        client = MongoDBClient()
        count = client.get_paper_count()

        print(f"  ✓ MongoDB connected")
        print(f"  ✓ Database: {client.db.name}")
        print(f"  ✓ Papers in database: {count}")

        if count == 0:
            print("\n  ⚠ No papers found in database")
            print("    Run: python ingest_arxiv.py --max-results 100")
            client.close()
            return False

        client.close()
        return True

    except Exception as e:
        print(f"  ✗ MongoDB check failed: {e}")
        return False


def check_embeddings():
    """Check if index exists."""
    print_section("Checking Embeddings and Index")

    index_path = "data/indexes/faiss_index.bin"
    metadata_path = "data/indexes/metadata.pkl"

    if not os.path.exists(index_path):
        print(f"  ✗ Index not found at {index_path}")
        print("    Run: python build_index.py")
        return False

    print(f"  ✓ Index found: {index_path}")

    if os.path.exists(metadata_path):
        print(f"  ✓ Metadata found: {metadata_path}")

    # Try loading
    try:
        from embeddings import VectorStore

        store = VectorStore.load(index_path, metadata_path)
        print(f"  ✓ Index loaded successfully")
        print(f"  ✓ Index size: {store.get_size()} papers")
        return True

    except Exception as e:
        print(f"  ✗ Failed to load index: {e}")
        return False


def test_search():
    """Test search functionality."""
    print_section("Testing Search Functionality")

    try:
        from ingestion import MongoDBClient
        from embeddings import EmbeddingGenerator, VectorStore

        # Load components
        print("  Loading components...")

        mongo_client = MongoDBClient()
        embedder = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')

        index_path = "data/indexes/faiss_index.bin"
        metadata_path = "data/indexes/metadata.pkl"
        vector_store = VectorStore.load(index_path, metadata_path)

        print("  ✓ All components loaded")

        # Test queries
        test_queries = [
            "robot manipulation with vision language models",
            "humanoid locomotion",
        ]

        for query in test_queries:
            print(f"\n  Query: '{query}'")

            start = time.time()
            query_emb = embedder.generate_query_embedding(query)
            paper_ids, scores = vector_store.search(query_emb, k=3)
            search_time = (time.time() - start) * 1000

            print(f"  Search time: {search_time:.2f}ms")

            for i, (paper_id, score) in enumerate(zip(paper_ids, scores), 1):
                paper = mongo_client.get_paper_by_arxiv_id(paper_id)
                print(f"    {i}. [{score:.4f}] {paper['title'][:60]}...")

        mongo_client.close()
        print("\n  ✓ Search test passed")
        return True

    except Exception as e:
        print(f"  ✗ Search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_api_ready():
    """Check if API can start."""
    print_section("Checking API Readiness")

    try:
        from api.main import app
        print("  ✓ API module loads successfully")

        index_path = "data/indexes/faiss_index.bin"
        if os.path.exists(index_path):
            print("  ✓ Index available for API")
            print("\n  Ready to start API:")
            print("    python run_api.py")
            print("\n  Then test with:")
            print("    python test_search.py --health")
            return True
        else:
            print("  ✗ Index not found - API will fail to start")
            return False

    except Exception as e:
        print(f"  ✗ API check failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print(" VLA Research Engine - Setup Verification")
    print("=" * 70)

    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_environment),
        ("MongoDB", check_mongodb),
        ("Embeddings & Index", check_embeddings),
        ("Search Functionality", test_search),
        ("API Readiness", check_api_ready),
    ]

    results = []

    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))

            if not result:
                print(f"\n⚠ '{name}' check failed - stopping here")
                break

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n✗ Unexpected error in '{name}': {e}")
            results.append((name, False))
            break

    # Summary
    print("\n" + "=" * 70)
    print(" Verification Summary")
    print("=" * 70)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 70)

    if all_passed:
        print(" ✓ ALL CHECKS PASSED!")
        print("=" * 70)
        print("\n Your system is ready! Next steps:")
        print("\n 1. Start the API server:")
        print("      python run_api.py")
        print("\n 2. In another terminal, test search:")
        print("      python test_search.py robot manipulation")
        print("\n 3. Or open the interactive API docs:")
        print("      http://localhost:8000/docs")
        return 0
    else:
        print(" ✗ SOME CHECKS FAILED")
        print("=" * 70)
        print("\n Please fix the issues above and run again:")
        print("   python verify_setup.py")
        return 1


if __name__ == '__main__':
    sys.exit(main())
