"""
Pydantic models for API requests and responses.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search query request."""
    query: str = Field(..., description="Natural language search query")
    k: int = Field(10, ge=1, le=100, description="Number of results to return")


class PaperResult(BaseModel):
    """Paper search result."""
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    published_date: datetime
    categories: List[str]
    pdf_url: Optional[str] = None
    similarity_score: float = Field(..., description="Cosine similarity score")


class SearchResponse(BaseModel):
    """Search response with results."""
    query: str
    results: List[PaperResult]
    total_results: int
    search_time_ms: float
    cache_hit: Optional[bool] = Field(None, description="Whether results came from cache")


class CacheStats(BaseModel):
    """Cache statistics response."""
    enabled: bool
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate_percent: float = 0.0
    exact_hits: int = 0
    similarity_hits: int = 0
    similarity_threshold: float = 0.95


class TrendDataPoint(BaseModel):
    """Single data point in a trend."""
    period: str = Field(..., description="Time period (e.g., '2023-01')")
    count: int = Field(..., description="Number of papers in this period")


class TrendsQuery(BaseModel):
    """Trends query parameters."""
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    interval: str = Field("month", description="Time interval (month, week, day)")
    topic: Optional[str] = Field(None, description="Topic keyword to filter")
    category: Optional[str] = Field(None, description="arXiv category to filter")


class TrendsResponse(BaseModel):
    """Trends analysis response."""
    data: List[TrendDataPoint]
    total_papers: int
    start_date: str
    end_date: str
    interval: str
    topic: Optional[str] = None
    category: Optional[str] = None


class CategoryBreakdown(BaseModel):
    """Category breakdown response."""
    category: str
    count: int


class KeywordTrend(BaseModel):
    """Keyword trend response."""
    keyword: str
    count: int


class GrowthStats(BaseModel):
    """Growth statistics response."""
    recent_period: str
    recent_count: int
    previous_count: int
    growth_rate: float
    growth_percent: float
    topic: Optional[str] = None
    category: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    mongodb_connected: bool
    index_loaded: bool
    total_papers: int
    index_size: int
