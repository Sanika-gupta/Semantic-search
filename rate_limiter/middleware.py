"""FastAPI middleware for rate limiting.

This middleware intercepts incoming requests, extracts client identifiers,
and enforces rate limits using the TokenBucket algorithm. It returns proper
HTTP 429 responses with rate limit headers when limits are exceeded.
"""

import logging
from typing import List, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .token_bucket import TokenBucket

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for token bucket rate limiting.

    This middleware:
    1. Extracts client IP from request
    2. Checks excluded paths (health checks, docs)
    3. Consumes tokens from bucket
    4. Returns 429 with headers if rate limited
    5. Adds rate limit headers to all responses

    Attributes:
        bucket: TokenBucket instance for rate limiting
        excluded_paths: List of paths to exclude from rate limiting
    """

    def __init__(
        self,
        app: ASGIApp,
        bucket: TokenBucket,
        excluded_paths: List[str] = None
    ):
        """Initialize rate limit middleware.

        Args:
            app: ASGI application
            bucket: TokenBucket instance
            excluded_paths: Paths to exclude (e.g., ["/health", "/docs"])
        """
        super().__init__(app)
        self.bucket = bucket
        self.excluded_paths = excluded_paths or [
            "/health",
            "/health/live",
            "/health/ready",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

    def _get_client_identifier(self, request: Request) -> str:
        """Extract client identifier from request.

        Priority:
        1. X-Forwarded-For header (for proxied requests)
        2. X-Real-IP header (nginx)
        3. request.client.host (direct connection)

        Args:
            request: FastAPI request object

        Returns:
            Client IP address or identifier
        """
        # Check for proxy headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can be a comma-separated list
            # First IP is the original client
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client host
        if request.client and request.client.host:
            return request.client.host

        # Last resort - use a default identifier
        logger.warning("Could not extract client IP, using default identifier")
        return "unknown"

    def _is_excluded(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting.

        Args:
            path: Request path

        Returns:
            True if path is excluded, False otherwise
        """
        return path in self.excluded_paths

    def _add_rate_limit_headers(
        self,
        response: Response,
        info: dict
    ) -> Response:
        """Add rate limit headers to response.

        Headers added:
        - X-RateLimit-Limit: Maximum requests allowed
        - X-RateLimit-Remaining: Tokens remaining
        - X-RateLimit-Reset: Unix timestamp when limit resets
        - Retry-After: Seconds to wait (only on 429)

        Args:
            response: Response object
            info: Rate limit info from TokenBucket

        Returns:
            Response with added headers
        """
        response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(info.get("reset_time", 0))

        # Add Retry-After only for denied requests
        retry_after = info.get("retry_after", 0)
        if retry_after > 0:
            response.headers["Retry-After"] = str(retry_after)

        return response

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiting middleware.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response (possibly 429 if rate limited)
        """
        # Check if path is excluded
        if self._is_excluded(request.url.path):
            return await call_next(request)

        # Extract client identifier
        client_id = self._get_client_identifier(request)

        # Attempt to consume token
        allowed, info = self.bucket.consume(client_id)

        if allowed:
            # Request allowed - proceed
            try:
                response = await call_next(request)
                # Add rate limit headers to successful response
                response = self._add_rate_limit_headers(response, info)
                return response
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                raise
        else:
            # Request denied - return 429
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path}. "
                f"Retry after {info.get('retry_after')} seconds."
            )

            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": info.get("retry_after", 60)
                }
            )

            # Add rate limit headers
            response = self._add_rate_limit_headers(response, info)
            return response


class RateLimitExemption:
    """Context manager to temporarily exempt a client from rate limiting.

    This is useful for admin operations or testing.
    """

    def __init__(self, bucket: TokenBucket, identifier: str):
        """Initialize exemption context.

        Args:
            bucket: TokenBucket instance
            identifier: Client identifier to exempt
        """
        self.bucket = bucket
        self.identifier = identifier

    def __enter__(self):
        """Reset bucket on entry."""
        self.bucket.reset(self.identifier)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset bucket on exit."""
        self.bucket.reset(self.identifier)
        return False
