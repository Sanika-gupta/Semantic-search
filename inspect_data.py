#!/usr/bin/env python3
"""
Utility script to inspect ingested papers in MongoDB.
"""

import argparse
from datetime import datetime
from collections import Counter
from ingestion import MongoDBClient


def print_summary(client: MongoDBClient):
    """Print summary statistics."""
    total = client.get_paper_count()
    print(f"\nTotal papers: {total}")

    if total == 0:
        print("No papers in database yet. Run: python ingest_arxiv.py")
        return

    papers = client.get_papers(limit=total)

    categories = []
    years = []
    for paper in papers:
        categories.extend(paper.get('categories', []))
        pub_date = paper.get('published_date')
        if pub_date:
            years.append(pub_date.year)

    print("\nTop categories:")
    for cat, count in Counter(categories).most_common(10):
        print(f"  {cat}: {count}")

    print("\nPapers by year:")
    for year, count in sorted(Counter(years).items(), reverse=True):
        print(f"  {year}: {count}")


def print_recent_papers(client: MongoDBClient, limit: int = 5):
    """Print most recent papers."""
    papers = client.get_papers(limit=limit)

    print(f"\n{limit} Most Recent Papers:")
    print("=" * 80)

    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   arXiv ID: {paper['arxiv_id']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}" +
              (f" et al. ({len(paper['authors'])} total)" if len(paper['authors']) > 3 else ""))
        print(f"   Published: {paper['published_date'].strftime('%Y-%m-%d')}")
        print(f"   Categories: {', '.join(paper['categories'])}")
        print(f"   Abstract: {paper['abstract'][:200]}...")


def search_papers(client: MongoDBClient, keyword: str, limit: int = 5):
    """Search papers by keyword in title."""
    papers = client.get_papers()

    keyword_lower = keyword.lower()
    matches = [
        p for p in papers
        if keyword_lower in p['title'].lower() or keyword_lower in p['abstract'].lower()
    ]

    print(f"\nFound {len(matches)} papers matching '{keyword}'")

    if matches:
        print(f"\nShowing top {min(limit, len(matches))} results:")
        print("=" * 80)

        for i, paper in enumerate(matches[:limit], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   arXiv ID: {paper['arxiv_id']}")
            print(f"   Published: {paper['published_date'].strftime('%Y-%m-%d')}")


def main():
    parser = argparse.ArgumentParser(description='Inspect ingested papers in MongoDB')
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary statistics'
    )
    parser.add_argument(
        '--recent',
        type=int,
        metavar='N',
        help='Show N most recent papers (default: 5)'
    )
    parser.add_argument(
        '--search',
        type=str,
        metavar='KEYWORD',
        help='Search for papers by keyword'
    )

    args = parser.parse_args()

    if not any([args.summary, args.recent, args.search]):
        args.summary = True
        args.recent = 5

    client = MongoDBClient()

    try:
        if args.summary:
            print_summary(client)

        if args.recent:
            print_recent_papers(client, limit=args.recent)
        elif args.recent is None and not args.search:
            print_recent_papers(client, limit=5)

        if args.search:
            search_papers(client, args.search)

    finally:
        client.close()


if __name__ == '__main__':
    main()
