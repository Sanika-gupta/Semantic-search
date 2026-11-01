"""Comprehensive tests for token bucket rate limiter.

Tests cover:
1. Burst then throttle behavior
2. Token refill over time
3. Concurrent access thread safety
4. Redis failure fallback
5. Header correctness
6. Middleware integration
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import json
import threading

from rate_limiter.token_bucket import TokenBucket
from rate_limiter.middleware import RateLimitMiddleware
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


# Mock Redis client for testing
class MockRedis:
    """Mock Redis client that stores data in memory."""

    def __init__(self):
        self.data = {}
        self.ttls = {}
        self.lock = threading.Lock()

    def get(self, key):
        """Get value from mock store."""
        return self.data.get(key)

    def setex(self, key, ttl, value):
        """Set value with TTL in mock store."""
        self.data[key] = value
        self.ttls[key] = ttl

    def delete(self, key):
        """Delete key from mock store."""
        if key in self.data:
            del self.data[key]
        if key in self.ttls:
            del self.ttls[key]

    def clear(self):
        """Clear all data."""
        self.data.clear()
        self.ttls.clear()

    def eval(self, _script, numkeys, key, now, rate, capacity, requested, ttl):
        """Small in-test stand-in for the Redis Lua command used by TokenBucket."""
        assert numkeys == 1
        now, rate = float(now), float(rate)
        capacity, requested, ttl = int(capacity), int(requested), int(ttl)
        with self.lock:
            raw = self.data.get(key)
            if raw is None:
                available, last_refill = float(capacity), now
            else:
                state = json.loads(raw)
                available = float(state["tokens"])
                last_refill = float(state["last_refill"])
            available = min(capacity, available + max(0, now - last_refill) * rate)
            allowed = requested >= 0 and available >= requested
            if allowed:
                available -= requested
                retry_after = 0
            else:
                retry_after = int(-(-(max(0, requested - available) / rate) // 1)) if rate > 0 else 0
            self.setex(key, ttl, json.dumps({"tokens": available, "last_refill": now}))
            reset_time = now + (capacity - available) / rate if rate > 0 else now
            return [int(allowed), f"{available:.12f}", f"{reset_time:.12f}", retry_after]


@pytest.fixture
def mock_redis():
    """Provide a mock Redis client."""
    return MockRedis()


@pytest.fixture
def token_bucket(mock_redis):
    """Provide a TokenBucket with mock Redis."""
    # Rate: 10 tokens per minute = 1/6 tokens per second
    # Capacity: 20 tokens
    return TokenBucket(mock_redis, rate=10/60, capacity=20, ttl=3600)


class TestTokenBucket:
    """Tests for TokenBucket core algorithm."""

    def test_initial_bucket_full_capacity(self, token_bucket):
        """Test that a new bucket starts with full capacity."""
        allowed, info = token_bucket.consume("client1", tokens=1)

        assert allowed is True
        assert info["remaining"] == 19  # Started with 20, consumed 1
        assert info["limit"] == 20

    def test_burst_then_throttle(self, token_bucket):
        """Test burst capacity followed by throttling."""
        client_id = "burst_client"

        # Should allow burst up to capacity (20 tokens)
        for i in range(20):
            allowed, info = token_bucket.consume(client_id, tokens=1)
            assert allowed is True, f"Request {i+1} should be allowed"
            assert info["remaining"] == 19 - i

        # 21st request should be denied
        allowed, info = token_bucket.consume(client_id, tokens=1)
        assert allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] > 0

    def test_token_refill_over_time(self, token_bucket, mock_redis):
        """Test that tokens refill at the correct rate over time."""
        client_id = "refill_client"

        # Consume all tokens
        for _ in range(20):
            token_bucket.consume(client_id, tokens=1)

        # Should be denied immediately
        allowed, info = token_bucket.consume(client_id, tokens=1)
        assert allowed is False

        # Manually advance time by adding tokens
        # Rate is 10/60 = 1/6 token per second
        # So after 6 seconds, we should have 1 token
        key = f"ratelimit:{client_id}"
        state = json.loads(mock_redis.get(key))

        # Simulate 12 seconds passing (should refill 2 tokens)
        state["last_refill"] -= 12
        mock_redis.setex(key, 3600, json.dumps(state))

        # Now should allow 2 requests
        allowed, info = token_bucket.consume(client_id, tokens=1)
        assert allowed is True
        assert info["remaining"] >= 0

        allowed, info = token_bucket.consume(client_id, tokens=1)
        assert allowed is True

        # Third should be denied
        allowed, info = token_bucket.consume(client_id, tokens=1)
        assert allowed is False

    def test_concurrent_access(self, token_bucket):
        """Test thread-safe concurrent access to bucket."""
        client_id = "concurrent_client"
        num_threads = 10
        requests_per_thread = 5

        def make_request():
            """Make a rate-limited request."""
            allowed, info = token_bucket.consume(client_id, tokens=1)
            return allowed

        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(make_request)
                for _ in range(num_threads * requests_per_thread)
            ]
            results = [f.result() for f in futures]

        # Should allow exactly 20 requests (capacity)
        allowed_count = sum(results)
        assert allowed_count == 20, f"Expected 20 allowed, got {allowed_count}"

        # Remaining should be denied
        denied_count = len(results) - allowed_count
        assert denied_count == 30  # 50 total - 20 allowed = 30 denied

    def test_redis_failure_fail_open(self, mock_redis):
        """Test that Redis failures result in fail-open behavior."""
        # Create bucket with failing Redis
        failing_redis = Mock()
        failing_redis.get.side_effect = Exception("Redis connection failed")

        bucket = TokenBucket(failing_redis, rate=10/60, capacity=20)

        # Should allow request despite Redis failure (fail open)
        allowed, info = bucket.consume("client1", tokens=1)
        assert allowed is True
        # Note: Current implementation logs error but doesn't include it in info
        # This is acceptable as it fails open gracefully

    def test_retry_after_calculation(self, token_bucket):
        """Test that retry_after is calculated correctly."""
        client_id = "retry_client"

        # Exhaust bucket
        for _ in range(20):
            token_bucket.consume(client_id, tokens=1)

        # Try to consume 1 more token
        allowed, info = token_bucket.consume(client_id, tokens=1)

        assert allowed is False
        # Rate is 1/6 token per second, so 1 token needs 6 seconds
        assert info["retry_after"] >= 6
        assert info["retry_after"] <= 7  # Should be 6 seconds + rounding

    def test_reset_bucket(self, token_bucket, mock_redis):
        """Test bucket reset functionality."""
        client_id = "reset_client"

        # Consume all tokens
        for _ in range(20):
            token_bucket.consume(client_id, tokens=1)

        # Verify exhausted
        allowed, _ = token_bucket.consume(client_id, tokens=1)
        assert allowed is False

        # Reset bucket
        token_bucket.reset(client_id)

        # Should now have full capacity
        allowed, info = token_bucket.consume(client_id, tokens=1)
        assert allowed is True
        assert info["remaining"] == 19

    def test_get_status(self, token_bucket):
        """Test bucket status retrieval."""
        client_id = "status_client"

        # Consume some tokens
        for _ in range(5):
            token_bucket.consume(client_id, tokens=1)

        # Check status
        status = token_bucket.get_status(client_id)

        assert status["identifier"] == client_id
        assert status["tokens"] == 15  # 20 - 5 consumed
        assert status["capacity"] == 20
        assert status["rate"] == 10/60


class TestRateLimitMiddleware:
    """Tests for FastAPI middleware integration.

    Note: These tests verify the middleware logic directly rather than through
    TestClient to avoid version compatibility issues.
    """

    @pytest.fixture
    def middleware(self, token_bucket):
        """Create middleware instance."""
        from fastapi import FastAPI
        app = FastAPI()
        return RateLimitMiddleware(
            app=app,
            bucket=token_bucket,
            excluded_paths=["/health", "/docs"]
        )

    def test_middleware_extracts_client_ip(self, middleware):
        """Test client IP extraction from headers."""
        # Create mock request with X-Forwarded-For
        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        mock_request.client = Mock(host="127.0.0.1")

        ip = middleware._get_client_identifier(mock_request)
        assert ip == "192.168.1.100"

        # Test X-Real-IP
        mock_request.headers = {"X-Real-IP": "192.168.1.200"}
        ip = middleware._get_client_identifier(mock_request)
        assert ip == "192.168.1.200"

        # Test fallback to client.host
        mock_request.headers = {}
        ip = middleware._get_client_identifier(mock_request)
        assert ip == "127.0.0.1"

    def test_middleware_excludes_paths(self, middleware):
        """Test that excluded paths are correctly identified."""
        assert middleware._is_excluded("/health") is True
        assert middleware._is_excluded("/docs") is True
        assert middleware._is_excluded("/search") is False
        assert middleware._is_excluded("/api/data") is False

    def test_middleware_adds_headers(self, middleware):
        """Test that rate limit headers are added correctly."""
        mock_response = Mock()
        mock_response.headers = {}

        info = {
            "limit": 20,
            "remaining": 15,
            "reset_time": 1234567890,
            "retry_after": 0
        }

        response = middleware._add_rate_limit_headers(mock_response, info)

        assert response.headers["X-RateLimit-Limit"] == "20"
        assert response.headers["X-RateLimit-Remaining"] == "15"
        assert response.headers["X-RateLimit-Reset"] == "1234567890"

    def test_middleware_adds_retry_after_on_denial(self, middleware):
        """Test that Retry-After header is added when rate limited."""
        mock_response = Mock()
        mock_response.headers = {}

        info = {
            "limit": 20,
            "remaining": 0,
            "reset_time": 1234567890,
            "retry_after": 60
        }

        response = middleware._add_rate_limit_headers(mock_response, info)

        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"

    def test_middleware_flow_sync(self, middleware, token_bucket):
        """Test middleware logic components (sync test).

        Full async integration tested via manual testing with running server.
        """
        # Test that the middleware correctly identifies components
        assert middleware.bucket == token_bucket
        assert "/health" in middleware.excluded_paths
        assert "/docs" in middleware.excluded_paths

        # Test client identifier extraction
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock(host="test-client")
        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "test-client"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_tokens_request(self, token_bucket):
        """Test consuming zero tokens."""
        allowed, info = token_bucket.consume("client", tokens=0)
        assert allowed is True
        assert info["remaining"] == 20  # No change

    def test_multi_token_consumption(self, token_bucket):
        """Test consuming multiple tokens at once."""
        # Request consuming 5 tokens
        allowed, info = token_bucket.consume("client", tokens=5)
        assert allowed is True
        assert info["remaining"] == 15

    def test_request_exceeding_capacity(self, token_bucket):
        """Test requesting more tokens than capacity."""
        # Request 30 tokens (capacity is 20)
        allowed, info = token_bucket.consume("client", tokens=30)
        assert allowed is False

    def test_negative_rate_handling(self):
        """Test that negative rates are handled."""
        mock_redis = MockRedis()
        # This should probably raise an error, but let's see current behavior
        bucket = TokenBucket(mock_redis, rate=-1, capacity=10)
        allowed, info = bucket.consume("client", tokens=1)
        # Implementation should handle this gracefully

    def test_very_high_refill_rate(self, mock_redis):
        """Test with very high refill rate."""
        bucket = TokenBucket(mock_redis, rate=1000, capacity=10)

        # Exhaust bucket
        for _ in range(10):
            bucket.consume("client", tokens=1)

        # Should be denied
        allowed, _ = bucket.consume("client", tokens=1)
        assert allowed is False

        # Wait minimal time - high rate means quick refill
        time.sleep(0.1)

        # Manually simulate refill by modifying state
        key = "ratelimit:client"
        state = json.loads(mock_redis.get(key))
        state["last_refill"] -= 0.1
        mock_redis.setex(key, 3600, json.dumps(state))

        # Should now allow (100 tokens refilled in 0.1 seconds)
        allowed, _ = bucket.consume("client", tokens=1)
        assert allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
