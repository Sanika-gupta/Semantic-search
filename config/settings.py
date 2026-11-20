from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_db_name: str = "vla_research"

    # arXiv API
    arxiv_base_url: str = "https://export.arxiv.org/api/query"
    max_results: int = 3000

    # Redis
    redis_uri: str = "redis://localhost:6379/0"

    # Rate Limiting
    rate_limit_requests_per_minute: int = 10
    rate_limit_burst_capacity: int = 20

    # Caching (for Phase 4)
    cache_enabled: bool = True
    cache_similarity_threshold: float = 0.95
    cache_ttl_seconds: int = 3600
    cache_max_scan: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
