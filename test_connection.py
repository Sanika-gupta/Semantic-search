#!/usr/bin/env python3
"""
Quick test script to verify MongoDB connection before running full ingestion.
"""

from config import settings
from pymongo import MongoClient


def test_mongodb_connection():
    """Test MongoDB connection."""
    print("Testing MongoDB connection...")
    print(f"URI: {settings.mongodb_uri}")
    print(f"Database: {settings.mongodb_db_name}")

    try:
        client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        print("✓ MongoDB connection successful!")

        db = client[settings.mongodb_db_name]
        collections = db.list_collection_names()
        print(f"✓ Database '{settings.mongodb_db_name}' accessible")

        if collections:
            print(f"  Existing collections: {', '.join(collections)}")
        else:
            print("  No collections yet (this is normal for a new database)")

        client.close()
        return True

    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB is running (try: mongod)")
        print("2. Check your .env file has the correct MONGODB_URI")
        print("3. For MongoDB Atlas, check your IP is whitelisted")
        return False


def test_arxiv_api():
    """Test arXiv API connection."""
    print("\nTesting arXiv API connection...")

    import requests

    try:
        response = requests.get(
            "https://export.arxiv.org/api/query",
            params={
                'search_query': 'cat:cs.RO',
                'max_results': 1
            },
            timeout=10
        )
        response.raise_for_status()
        print("✓ arXiv API connection successful!")
        return True

    except Exception as e:
        print(f"✗ arXiv API connection failed: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("VLA Research Engine - Connection Test")
    print("=" * 60)

    mongodb_ok = test_mongodb_connection()
    arxiv_ok = test_arxiv_api()

    print("\n" + "=" * 60)
    if mongodb_ok and arxiv_ok:
        print("✓ All connections successful!")
        print("\nYou're ready to run: python ingest_arxiv.py")
    else:
        print("✗ Some connections failed. Please fix the issues above.")
    print("=" * 60)
