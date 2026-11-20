#!/usr/bin/env python3
"""
Simple CLI for testing semantic search.
"""

import argparse
import requests
import json
from datetime import datetime


def search_papers(query: str, k: int = 5, api_url: str = "http://localhost:8000"):
    """
    Search for papers using the API.

    Args:
        query: Search query
        k: Number of results
        api_url: API base URL
    """
    try:
        response = requests.post(
            f"{api_url}/search",
            json={"query": query, "k": k},
            timeout=30
        )
        response.raise_for_status()

        data = response.json()

        print("=" * 80)
        print(f"Query: {data['query']}")
        print(f"Results: {data['total_results']}")
        print(f"Search time: {data['search_time_ms']:.2f}ms")
        print("=" * 80)

        for i, paper in enumerate(data['results'], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   arXiv ID: {paper['arxiv_id']}")
            print(f"   Similarity: {paper['similarity_score']:.4f}")
            print(f"   Authors: {', '.join(paper['authors'][:3])}" +
                  (f" et al." if len(paper['authors']) > 3 else ""))
            pub_date = datetime.fromisoformat(paper['published_date'].replace('Z', '+00:00'))
            print(f"   Published: {pub_date.strftime('%Y-%m-%d')}")
            print(f"   Categories: {', '.join(paper['categories'][:3])}")
            print(f"   Abstract: {paper['abstract'][:200]}...")
            if paper.get('pdf_url'):
                print(f"   PDF: {paper['pdf_url']}")

    except requests.exceptions.ConnectionError:
        print(f"✗ Could not connect to API at {api_url}")
        print("  Make sure the API is running: python run_api.py")
    except requests.exceptions.HTTPError as e:
        print(f"✗ API error: {e}")
        if e.response:
            print(f"  Response: {e.response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")


def check_health(api_url: str = "http://localhost:8000"):
    """Check API health."""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        response.raise_for_status()

        data = response.json()

        print("=" * 60)
        print("API Health Check")
        print("=" * 60)
        print(f"Status: {data['status']}")
        print(f"MongoDB connected: {data['mongodb_connected']}")
        print(f"Index loaded: {data['index_loaded']}")
        print(f"Total papers: {data['total_papers']}")
        print(f"Index size: {data['index_size']}")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Health check failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Test semantic search API'
    )
    parser.add_argument(
        'query',
        nargs='*',
        help='Search query (or use --health for health check)'
    )
    parser.add_argument(
        '-k',
        type=int,
        default=5,
        help='Number of results (default: 5)'
    )
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8000',
        help='API URL (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--health',
        action='store_true',
        help='Check API health'
    )

    args = parser.parse_args()

    if args.health:
        check_health(args.api_url)
    elif args.query:
        query = ' '.join(args.query)
        search_papers(query, k=args.k, api_url=args.api_url)
    else:
        # Interactive mode
        print("=" * 60)
        print("Semantic Search - Interactive Mode")
        print("=" * 60)
        print("Type your queries (or 'quit' to exit)\n")

        while True:
            try:
                query = input("Search> ").strip()

                if query.lower() in ['quit', 'exit', 'q']:
                    break

                if not query:
                    continue

                if query.lower() == 'health':
                    check_health(args.api_url)
                else:
                    search_papers(query, k=args.k, api_url=args.api_url)

                print()

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except EOFError:
                break


if __name__ == '__main__':
    main()
