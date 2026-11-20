"""
FastAPI application for semantic search API.
"""

import os
import redis
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from embeddings import EmbeddingGenerator, VectorStore
from ingestion import MongoDBClient
from cache import SemanticCache, RedisCache
from .models import (
    SearchQuery, SearchResponse, HealthResponse, PaperResult, CacheStats,
    TrendsQuery, TrendsResponse, TrendDataPoint, CategoryBreakdown,
    KeywordTrend, GrowthStats
)
from .search_service import SearchService
from .trends import TrendsAnalyzer
from rate_limiter import TokenBucket, RateLimitMiddleware
from config.settings import settings
from datetime import datetime


# Global state
app_state = {
    'search_service': None,
    'mongo_client': None,
    'redis_client': None,
    'token_bucket': None,
    'semantic_cache': None,
    'trends_analyzer': None
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load resources on startup, cleanup on shutdown."""
    print("Starting up...")

    # Load model and index
    index_dir = os.getenv('INDEX_DIR', 'data/indexes')
    model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

    index_path = os.path.join(index_dir, 'faiss_index.bin')
    metadata_path = os.path.join(index_dir, 'metadata.pkl')

    if not os.path.exists(index_path):
        raise RuntimeError(
            f"Index not found at {index_path}. "
            "Run: python build_index.py"
        )

    print("Loading embedding model...")
    embedder = EmbeddingGenerator(model_name=model_name)

    print("Loading FAISS index...")
    vector_store = VectorStore.load(index_path, metadata_path)

    print("Connecting to MongoDB...")
    mongo_client = MongoDBClient()

    # Initialize Redis for rate limiting
    print("Connecting to Redis...")
    try:
        redis_client = redis.Redis.from_url(
            settings.redis_uri,
            decode_responses=True,
            socket_connect_timeout=5
        )
        # Test connection
        redis_client.ping()
        print(f"Redis connected at {settings.redis_uri}")
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")
        print("Rate limiting will be disabled")
        redis_client = None

    # Create token bucket for rate limiting
    token_bucket = None
    semantic_cache = None

    if redis_client:
        # Convert requests per minute to tokens per second
        rate_per_second = settings.rate_limit_requests_per_minute / 60.0
        token_bucket = TokenBucket(
            redis_client=redis_client,
            rate=rate_per_second,
            capacity=settings.rate_limit_burst_capacity,
            ttl=3600  # 1 hour TTL for inactive clients
        )
        print(f"Rate limiting enabled: {settings.rate_limit_requests_per_minute} req/min, "
              f"burst: {settings.rate_limit_burst_capacity}")

        # Create semantic cache if enabled
        if settings.cache_enabled:
            redis_cache = RedisCache(redis_client, prefix="search_cache")
            semantic_cache = SemanticCache(
                redis_cache=redis_cache,
                similarity_threshold=settings.cache_similarity_threshold,
                max_scan=settings.cache_max_scan,
                ttl=settings.cache_ttl_seconds
            )
            print(f"Semantic cache enabled: threshold={settings.cache_similarity_threshold}, "
                  f"ttl={settings.cache_ttl_seconds}s")

    # Create search service
    search_service = SearchService(
        vector_store=vector_store,
        embedder=embedder,
        mongo_client=mongo_client,
        semantic_cache=semantic_cache
    )

    # Create trends analyzer
    trends_analyzer = TrendsAnalyzer(mongo_client=mongo_client)

    app_state['search_service'] = search_service
    app_state['mongo_client'] = mongo_client
    app_state['redis_client'] = redis_client
    app_state['token_bucket'] = token_bucket
    app_state['semantic_cache'] = semantic_cache
    app_state['trends_analyzer'] = trends_analyzer

    print("Startup complete!")

    yield

    # Cleanup
    print("Shutting down...")
    if app_state['mongo_client']:
        app_state['mongo_client'].close()
    if app_state['redis_client']:
        try:
            app_state['redis_client'].close()
        except Exception as e:
            print(f"Error closing Redis: {e}")


app = FastAPI(
    title="VLA Research Engine API",
    description="Semantic search over VLA/VLM/humanoid robotics research papers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware (added after CORS, before routes)
# Will be configured after startup when token_bucket is available
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Conditionally apply rate limiting if Redis is available."""
    token_bucket = app_state.get('token_bucket')

    if not token_bucket:
        # Rate limiting disabled (Redis not available)
        return await call_next(request)

    # Apply rate limiting using the middleware logic
    from rate_limiter.middleware import RateLimitMiddleware
    middleware = RateLimitMiddleware(
        app=app,
        bucket=token_bucket,
        excluded_paths=["/health", "/health/live", "/health/ready", "/docs", "/redoc", "/openapi.json", "/"]
    )
    return await middleware.dispatch(request, call_next)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "VLA Research Engine API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health/live", tags=["Health"])
async def liveness():
    """Liveness probe - is the app running?"""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """Readiness probe - can the app handle requests?"""
    search_service = app_state.get('search_service')
    mongo_client = app_state.get('mongo_client')

    if not search_service or not mongo_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Check MongoDB connection
        mongo_client.client.server_info()

        # Check Redis (optional - not critical)
        redis_status = "ok"
        redis_client = app_state.get('redis_client')
        if redis_client:
            try:
                redis_client.ping()
            except Exception:
                redis_status = "unavailable"

        # Check search service
        stats = search_service.get_stats()

        return {
            "status": "ready",
            "mongodb": "ok",
            "redis": redis_status,
            "index": "ok",
            "total_papers": stats['total_papers']
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint (legacy, use /health/ready)."""
    search_service = app_state.get('search_service')
    mongo_client = app_state.get('mongo_client')

    if not search_service or not mongo_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        stats = search_service.get_stats()

        return HealthResponse(
            status="healthy",
            mongodb_connected=True,
            index_loaded=True,
            total_papers=stats['total_papers'],
            index_size=stats['index_size']
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/cache/stats", response_model=CacheStats, tags=["Cache"])
async def cache_stats():
    """
    Get cache statistics.

    Returns hit/miss rates and other cache performance metrics.
    """
    semantic_cache = app_state.get('semantic_cache')

    if not semantic_cache:
        return CacheStats(enabled=False)

    stats = semantic_cache.get_stats()
    return CacheStats(
        enabled=True,
        **stats
    )


@app.get("/trends", response_model=TrendsResponse, tags=["Trends"])
async def get_trends(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "month",
    topic: Optional[str] = None,
    category: Optional[str] = None
):
    """
    Get publication trends over time.

    Returns time-series data showing paper publications by period.
    Optionally filter by topic keyword or arXiv category.
    """
    trends_analyzer = app_state.get('trends_analyzer')

    if not trends_analyzer:
        raise HTTPException(status_code=503, detail="Trends service not available")

    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Get trends
        data = trends_analyzer.get_publication_trends(
            start_date=start_dt,
            end_date=end_dt,
            interval=interval,
            topic=topic,
            category=category
        )

        # Convert to response model
        trend_data = [TrendDataPoint(**point) for point in data]
        total_papers = sum(point.count for point in trend_data)

        # Format dates for response
        if not start_dt:
            end_dt = end_dt or datetime.now()
            start_dt = end_dt.replace(year=end_dt.year - 1)

        return TrendsResponse(
            data=trend_data,
            total_papers=total_papers,
            start_date=start_dt.strftime("%Y-%m-%d"),
            end_date=(end_dt or datetime.now()).strftime("%Y-%m-%d"),
            interval=interval,
            topic=topic,
            category=category
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trends analysis failed: {str(e)}")


@app.get("/trends/categories", response_model=List[CategoryBreakdown], tags=["Trends"])
async def get_category_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get paper counts by arXiv category.

    Returns breakdown of papers across different arXiv categories.
    """
    trends_analyzer = app_state.get('trends_analyzer')

    if not trends_analyzer:
        raise HTTPException(status_code=503, detail="Trends service not available")

    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        breakdown = trends_analyzer.get_category_breakdown(
            start_date=start_dt,
            end_date=end_dt
        )

        return [CategoryBreakdown(**item) for item in breakdown]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Category breakdown failed: {str(e)}")


@app.get("/trends/keywords", response_model=List[KeywordTrend], tags=["Trends"])
async def get_top_keywords(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10
):
    """
    Get trending keywords from paper titles and abstracts.

    Returns most common keywords/topics in recent papers.
    """
    trends_analyzer = app_state.get('trends_analyzer')

    if not trends_analyzer:
        raise HTTPException(status_code=503, detail="Trends service not available")

    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        keywords = trends_analyzer.get_top_keywords(
            start_date=start_dt,
            end_date=end_dt,
            limit=limit
        )

        return [KeywordTrend(**kw) for kw in keywords]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keyword analysis failed: {str(e)}")


@app.get("/trends/growth", response_model=GrowthStats, tags=["Trends"])
async def get_growth_stats(
    topic: Optional[str] = None,
    category: Optional[str] = None
):
    """
    Get publication growth rate.

    Compares last 30 days vs previous 30 days to show growth trend.
    """
    trends_analyzer = app_state.get('trends_analyzer')

    if not trends_analyzer:
        raise HTTPException(status_code=503, detail="Trends service not available")

    try:
        stats = trends_analyzer.get_growth_rate(topic=topic, category=category)
        return GrowthStats(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Growth analysis failed: {str(e)}")


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(query: SearchQuery):
    """
    Semantic search endpoint.

    Performs semantic search over research papers using natural language queries.
    Results may be served from semantic cache if a similar query was recently made.
    """
    search_service = app_state.get('search_service')

    if not search_service:
        raise HTTPException(status_code=503, detail="Search service not available")

    try:
        results, search_time, cache_hit = search_service.search(query.query, k=query.k)

        paper_results = [
            PaperResult(**result) for result in results
        ]

        return SearchResponse(
            query=query.query,
            results=paper_results,
            total_results=len(paper_results),
            search_time_ms=search_time,
            cache_hit=cache_hit if app_state.get('semantic_cache') else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
