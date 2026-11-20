from typing import List, Dict, Optional
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError
from config import settings


class MongoDBClient:
    """Client for storing and retrieving papers from MongoDB."""

    def __init__(self):
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db_name]
        self.papers_collection = self.db['papers']
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for efficient querying."""
        self.papers_collection.create_index('arxiv_id', unique=True)
        self.papers_collection.create_index('published_date')
        self.papers_collection.create_index('categories')
        self.papers_collection.create_index([('title', 'text'), ('abstract', 'text')])

        print("MongoDB indexes created successfully")

    def insert_papers(self, papers: List[Dict]) -> Dict[str, int]:
        """
        Insert papers into MongoDB, skipping duplicates.

        Args:
            papers: List of paper dictionaries

        Returns:
            Dictionary with counts of inserted and skipped papers
        """
        inserted = 0
        skipped = 0

        for paper in papers:
            try:
                self.papers_collection.insert_one(paper)
                inserted += 1
            except DuplicateKeyError:
                skipped += 1
            except PyMongoError as e:
                print(f"Error inserting paper {paper.get('arxiv_id')}: {e}")
                continue

        return {
            'inserted': inserted,
            'skipped': skipped,
            'total': len(papers)
        }

    def get_paper_count(self) -> int:
        """Get total number of papers in the database."""
        return self.papers_collection.count_documents({})

    def get_papers(
        self,
        limit: Optional[int] = None,
        skip: int = 0,
        sort_by: str = 'published_date',
        ascending: bool = False
    ) -> List[Dict]:
        """
        Retrieve papers from the database.

        Args:
            limit: Maximum number of papers to return
            skip: Number of papers to skip
            sort_by: Field to sort by
            ascending: Sort order

        Returns:
            List of paper dictionaries
        """
        cursor = self.papers_collection.find({})

        sort_order = ASCENDING if ascending else -1
        cursor = cursor.sort(sort_by, sort_order)

        if skip > 0:
            cursor = cursor.skip(skip)

        if limit is not None:
            cursor = cursor.limit(limit)

        return list(cursor)

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict]:
        """Retrieve a single paper by its arXiv ID."""
        return self.papers_collection.find_one({'arxiv_id': arxiv_id})

    def get_papers_by_arxiv_ids(self, arxiv_ids: List[str]) -> Dict[str, Dict]:
        """Retrieve many papers in one round trip, keyed by arXiv ID."""
        if not arxiv_ids:
            return {}
        cursor = self.papers_collection.find({'arxiv_id': {'$in': list(arxiv_ids)}})
        return {paper['arxiv_id']: paper for paper in cursor}

    def get_papers_by_category(self, category: str, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve papers filtered by category."""
        cursor = self.papers_collection.find({'categories': category})

        if limit is not None:
            cursor = cursor.limit(limit)

        return list(cursor)

    def get_papers_by_date_range(
        self,
        start_date,
        end_date,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Retrieve papers within a date range."""
        cursor = self.papers_collection.find({
            'published_date': {
                '$gte': start_date,
                '$lte': end_date
            }
        })

        if limit is not None:
            cursor = cursor.limit(limit)

        return list(cursor)

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
