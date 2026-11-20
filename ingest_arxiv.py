#!/usr/bin/env python3
"""
arXiv Ingestion Pipeline - Phase 1

Fetches VLA/VLM/humanoid-related papers from arXiv API and stores them in MongoDB.
Filters by categories: cs.RO, cs.CV, cs.LG, cs.AI
Keywords: VLA, VLM, humanoid, vision language action, etc.
"""

import argparse
from ingestion import ArxivClient, MongoDBClient


def main():
    parser = argparse.ArgumentParser(
        description='Ingest VLA/VLM/humanoid papers from arXiv into MongoDB'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        default=3000,
        help='Maximum number of papers to fetch (default: 3000)'
    )
    parser.add_argument(
        '--start',
        type=int,
        default=0,
        help='Starting index for pagination (default: 0)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch papers but do not insert into MongoDB'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("arXiv Ingestion Pipeline - Phase 1")
    print("=" * 60)

    arxiv_client = ArxivClient()

    print("\nStep 1: Fetching papers from arXiv API...")
    papers = arxiv_client.fetch_papers(
        max_results=args.max_results,
        start=args.start
    )

    if not papers:
        print("\nNo papers found. Exiting.")
        return

    print(f"\nFetched {len(papers)} papers")
    print(f"First paper: {papers[0]['title'][:80]}...")
    print(f"Last paper: {papers[-1]['title'][:80]}...")

    if args.dry_run:
        print("\nDry run mode - skipping MongoDB insertion")
        print(f"Would have inserted {len(papers)} papers")
        return

    print("\nStep 2: Inserting papers into MongoDB...")
    mongo_client = MongoDBClient()

    result = mongo_client.insert_papers(papers)

    print("\n" + "=" * 60)
    print("Ingestion Complete")
    print("=" * 60)
    print(f"Total papers fetched: {result['total']}")
    print(f"New papers inserted: {result['inserted']}")
    print(f"Duplicate papers skipped: {result['skipped']}")
    print(f"Total papers in database: {mongo_client.get_paper_count()}")

    mongo_client.close()

    print("\nSample papers in database:")
    mongo_client_sample = MongoDBClient()
    sample_papers = mongo_client_sample.get_papers(limit=3)

    for i, paper in enumerate(sample_papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   arXiv ID: {paper['arxiv_id']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}" +
              (f" et al." if len(paper['authors']) > 3 else ""))
        print(f"   Published: {paper['published_date'].strftime('%Y-%m-%d')}")
        print(f"   Categories: {', '.join(paper['categories'][:3])}")

    mongo_client_sample.close()


if __name__ == '__main__':
    main()
