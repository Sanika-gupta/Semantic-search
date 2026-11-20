"""
Test trends analysis functionality.
"""

from datetime import datetime, timedelta
from ingestion import MongoDBClient
from api.trends import TrendsAnalyzer

print("=" * 70)
print("TRENDS ANALYSIS TEST")
print("=" * 70)

# Initialize components
print("\n1. Connecting to MongoDB...")
mongo_client = MongoDBClient()
trends_analyzer = TrendsAnalyzer(mongo_client)
print("✓ Connected")

# Test 1: Publication trends over time
print("\n2. Testing publication trends (last year, monthly)...")
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

trends = trends_analyzer.get_publication_trends(
    start_date=start_date,
    end_date=end_date,
    interval="month"
)

print(f"   Found {len(trends)} periods with data")
if trends:
    print(f"   Sample periods:")
    for trend in trends[:5]:
        print(f"     - {trend['period']}: {trend['count']} papers")

# Test 2: Topic-specific trends
print("\n3. Testing topic trends (VLA papers)...")
vla_trends = trends_analyzer.get_publication_trends(
    start_date=start_date,
    end_date=end_date,
    interval="month",
    topic="VLA"
)

total_vla = sum(t['count'] for t in vla_trends)
print(f"   VLA papers in last year: {total_vla}")

# Test 3: Category breakdown
print("\n4. Testing category breakdown...")
categories = trends_analyzer.get_category_breakdown(
    start_date=start_date,
    end_date=end_date
)

print(f"   Found {len(categories)} categories:")
for cat in categories[:5]:
    print(f"     - {cat['category']}: {cat['count']} papers")

# Test 4: Top keywords
print("\n5. Testing top keywords...")
keywords = trends_analyzer.get_top_keywords(
    start_date=start_date,
    end_date=end_date,
    limit=10
)

print(f"   Top 10 keywords:")
for kw in keywords[:10]:
    print(f"     - {kw['keyword']}: {kw['count']} papers")

# Test 5: Growth rate
print("\n6. Testing growth rate...")
growth = trends_analyzer.get_growth_rate()

print(f"   Recent period: {growth['recent_count']} papers")
print(f"   Previous period: {growth['previous_count']} papers")
print(f"   Growth rate: {growth['growth_percent']:.1f}%")

# Test 6: Topic comparison
print("\n7. Testing topic comparison...")
topics = ["VLA", "diffusion", "transformer"]
comparison = trends_analyzer.get_topic_comparison(
    topics=topics,
    start_date=start_date,
    end_date=end_date,
    interval="month"
)

print(f"   Comparing {len(topics)} topics:")
for topic, data in comparison.items():
    total = sum(d['count'] for d in data)
    print(f"     - {topic}: {total} papers total")

print("\n" + "=" * 70)
print("✓ ALL TESTS PASSED")
print("=" * 70)

# Summary
print("\nSummary:")
print(f"  Total papers in DB: {mongo_client.get_paper_count()}")
print(f"  Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"  Trend periods: {len(trends)}")
print(f"  Categories: {len(categories)}")
print(f"  Top keyword: {keywords[0]['keyword']} ({keywords[0]['count']} papers)")

mongo_client.close()
