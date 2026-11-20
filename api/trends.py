"""
Trends analysis for research papers.

Provides time-series data on paper publications by topic/category.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from ingestion import MongoDBClient


class TrendsAnalyzer:
    """Analyzes publication trends over time."""

    def __init__(self, mongo_client: MongoDBClient):
        """
        Initialize trends analyzer.

        Args:
            mongo_client: MongoDB client instance
        """
        self.mongo_client = mongo_client

    def get_publication_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "month",
        topic: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Get publication trends over time.

        Args:
            start_date: Start date (default: 1 year ago)
            end_date: End date (default: now)
            interval: Time interval (month, week, day)
            topic: Optional topic keyword to filter
            category: Optional arXiv category to filter

        Returns:
            List of {period, count, topic} dicts
        """
        # Default date range: last year
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # Build MongoDB query
        query = {
            "published_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }

        # Add topic filter (search in title and abstract)
        if topic:
            query["$or"] = [
                {"title": {"$regex": topic, "$options": "i"}},
                {"abstract": {"$regex": topic, "$options": "i"}}
            ]

        # Add category filter
        if category:
            query["categories"] = category

        # Fetch papers
        papers = list(self.mongo_client.db.papers.find(query))

        # Group by time interval
        grouped = defaultdict(int)

        for paper in papers:
            pub_date = paper.get("published_date")
            if not pub_date:
                continue

            # Convert to period key
            period_key = self._get_period_key(pub_date, interval)
            grouped[period_key] += 1

        # Convert to sorted list
        trends = [
            {"period": period, "count": count}
            for period, count in sorted(grouped.items())
        ]

        return trends

    def get_topic_comparison(
        self,
        topics: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "month"
    ) -> Dict[str, List[Dict]]:
        """
        Compare trends across multiple topics.

        Args:
            topics: List of topic keywords
            start_date: Start date
            end_date: End date
            interval: Time interval

        Returns:
            Dict mapping topic to list of {period, count}
        """
        results = {}

        for topic in topics:
            trends = self.get_publication_trends(
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                topic=topic
            )
            results[topic] = trends

        return results

    def get_category_breakdown(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get paper counts by arXiv category.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of {category, count} dicts
        """
        # Default date range
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # MongoDB aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "published_date": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }
            },
            # Unwind categories array
            {"$unwind": "$categories"},
            # Group by category
            {
                "$group": {
                    "_id": "$categories",
                    "count": {"$sum": 1}
                }
            },
            # Sort by count descending
            {"$sort": {"count": -1}}
        ]

        results = list(self.mongo_client.db.papers.aggregate(pipeline))

        # Format results
        breakdown = [
            {"category": r["_id"], "count": r["count"]}
            for r in results
        ]

        return breakdown

    def get_top_keywords(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Extract trending keywords from paper titles.

        Args:
            start_date: Start date
            end_date: End date
            limit: Number of keywords to return

        Returns:
            List of {keyword, count} dicts
        """
        # Common ML/robotics keywords to track
        keywords = [
            "VLA", "VLM", "vision language",
            "manipulation", "grasping", "locomotion",
            "diffusion", "transformer", "world model",
            "imitation learning", "reinforcement learning",
            "humanoid", "embodied AI", "sim-to-real"
        ]

        # Default date range
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # Count occurrences
        keyword_counts = {}

        for keyword in keywords:
            count = self.mongo_client.db.papers.count_documents({
                "published_date": {
                    "$gte": start_date,
                    "$lte": end_date
                },
                "$or": [
                    {"title": {"$regex": keyword, "$options": "i"}},
                    {"abstract": {"$regex": keyword, "$options": "i"}}
                ]
            })
            keyword_counts[keyword] = count

        # Sort and limit
        sorted_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {"keyword": kw, "count": count}
            for kw, count in sorted_keywords
        ]

    def _get_period_key(self, date: datetime, interval: str) -> str:
        """
        Convert date to period key string.

        Args:
            date: Datetime object
            interval: month, week, or day

        Returns:
            Period key (e.g., "2023-01", "2023-W05", "2023-01-15")
        """
        if interval == "month":
            return date.strftime("%Y-%m")
        elif interval == "week":
            return date.strftime("%Y-W%W")
        elif interval == "day":
            return date.strftime("%Y-%m-%d")
        else:
            return date.strftime("%Y-%m")

    def get_growth_rate(
        self,
        topic: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict:
        """
        Calculate publication growth rate.

        Args:
            topic: Optional topic filter
            category: Optional category filter

        Returns:
            Dict with growth statistics
        """
        now = datetime.now()

        # Last 30 days
        recent_start = now - timedelta(days=30)
        recent_count = self._count_papers(recent_start, now, topic, category)

        # Previous 30 days
        prev_start = now - timedelta(days=60)
        prev_end = recent_start
        prev_count = self._count_papers(prev_start, prev_end, topic, category)

        # Calculate growth
        if prev_count == 0:
            growth_rate = 0.0
            growth_percent = 0.0
        else:
            growth_rate = (recent_count - prev_count) / prev_count
            growth_percent = growth_rate * 100

        return {
            "recent_period": "last_30_days",
            "recent_count": recent_count,
            "previous_count": prev_count,
            "growth_rate": growth_rate,
            "growth_percent": growth_percent,
            "topic": topic,
            "category": category
        }

    def _count_papers(
        self,
        start_date: datetime,
        end_date: datetime,
        topic: Optional[str] = None,
        category: Optional[str] = None
    ) -> int:
        """Count papers in date range with optional filters."""
        query = {
            "published_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }

        if topic:
            query["$or"] = [
                {"title": {"$regex": topic, "$options": "i"}},
                {"abstract": {"$regex": topic, "$options": "i"}}
            ]

        if category:
            query["categories"] = category

        return self.mongo_client.db.papers.count_documents(query)
