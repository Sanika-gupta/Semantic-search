"""Token bucket rate limiting algorithm implementation.

This module implements a token bucket algorithm from scratch without using any
rate limiting libraries. The token bucket allows burst traffic up to a capacity
while enforcing an average rate over time.

Algorithm:
- Bucket starts with 'capacity' tokens
- Tokens refill at 'rate' tokens per second
- Each request consumes 'tokens' (default 1)
- If bucket has enough tokens: request allowed, tokens decremented
- If bucket lacks tokens: request denied, retry_after calculated
- Uses Redis for distributed state storage with atomic operations
"""

import time
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


# A read/refill/consume/write operation must be one Redis command; separate
# GET/SET calls allow concurrent requests to spend the same token.
CONSUME_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local raw = redis.call('GET', key)
local available = capacity
local last_refill = now
if raw then
  local state = cjson.decode(raw)
  available = tonumber(state.tokens)
  last_refill = tonumber(state.last_refill)
end

available = math.min(capacity, available + math.max(0, now - last_refill) * rate)
local allowed = 0
local retry_after = 0
if requested >= 0 and available >= requested then
  allowed = 1
  available = available - requested
else
  if rate > 0 then
    retry_after = math.ceil(math.max(0, requested - available) / rate)
  end
end

redis.call('SETEX', key, ttl, cjson.encode({tokens = available, last_refill = now}))
local reset_time = now
if rate > 0 then
  reset_time = now + (capacity - available) / rate
end
return {allowed, string.format('%.12f', available), string.format('%.12f', reset_time), retry_after}
"""


class TokenBucket:
    """Token bucket rate limiter with Redis backend.

    Attributes:
        redis_client: Redis client for atomic operations
        rate: Token refill rate (tokens per second)
        capacity: Maximum burst capacity (tokens)
        ttl: Redis key TTL for inactive clients (seconds)
    """

    def __init__(
        self,
        redis_client,
        rate: float,
        capacity: int,
        ttl: int = 3600
    ):
        """Initialize token bucket.

        Args:
            redis_client: Redis client instance
            rate: Refill rate in tokens per second (e.g., 10/60 = 0.167 for 10 req/min)
            capacity: Maximum bucket size (burst capacity)
            ttl: Key expiration time for inactive clients
        """
        self.redis = redis_client
        self.rate = rate
        self.capacity = capacity
        self.ttl = ttl

    def _get_key(self, identifier: str) -> str:
        """Generate Redis key for client identifier.

        Args:
            identifier: Client identifier (e.g., IP address)

        Returns:
            Redis key string
        """
        return f"ratelimit:{identifier}"

    def consume(
        self,
        identifier: str,
        tokens: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Attempt to consume tokens from the bucket.

        This is the main method for rate limiting. It's thread-safe through
        Redis atomic operations.

        Args:
            identifier: Client identifier (e.g., IP address)
            tokens: Number of tokens to consume (default 1)

        Returns:
            Tuple of (allowed, info):
                allowed: True if request allowed, False if rate limited
                info: Dict containing:
                    - remaining: Tokens remaining after consumption
                    - reset_time: Unix timestamp when bucket will refill
                    - retry_after: Seconds to wait before retrying (if denied)
                    - limit: Total capacity
                    - rate: Refill rate
        """
        key = self._get_key(identifier)
        now = time.time()

        try:
            allowed, remaining, reset_time, retry_after = self.redis.eval(
                CONSUME_LUA,
                1,
                key,
                now,
                self.rate,
                self.capacity,
                tokens,
                self.ttl,
            )
            remaining_tokens = float(remaining)
            # Redis/Lua returns a fractional value.  The header is an integer
            # count, and a tiny elapsed-time refill must not turn 19.999999
            # into a reported value of 18.
            remaining_count = int(remaining_tokens + 1e-9)
            info = {
                "remaining": remaining_count if int(allowed) else 0,
                "reset_time": int(float(reset_time)),
                "retry_after": int(retry_after),
                "limit": self.capacity,
                "rate": self.rate,
            }
            return bool(int(allowed)), info

        except Exception as e:
            logger.error(f"Error in token bucket consume: {e}")
            # Fail open: allow the request on error
            info = {
                "remaining": self.capacity,
                "reset_time": int(now + 60),
                "retry_after": 0,
                "limit": self.capacity,
                "rate": self.rate,
                "error": str(e)
            }
            return True, info

    def reset(self, identifier: str) -> None:
        """Reset bucket for a specific identifier (admin/testing use).

        Args:
            identifier: Client identifier to reset
        """
        key = self._get_key(identifier)
        try:
            self.redis.delete(key)
            logger.info(f"Reset bucket for {identifier}")
        except Exception as e:
            logger.error(f"Error resetting bucket: {e}")

    def get_status(self, identifier: str) -> Dict[str, Any]:
        """Get current rate limit status for an identifier.

        Args:
            identifier: Client identifier

        Returns:
            Dict with current status information
        """
        key = self._get_key(identifier)
        now = time.time()

        try:
            data = self.redis.get(key)
            if data is None:
                return {
                    "identifier": identifier,
                    "tokens": self.capacity,
                    "capacity": self.capacity,
                    "rate": self.rate,
                    "last_refill": now,
                    "age_seconds": 0,
                }
            import json
            state = json.loads(data)
            last_refill = float(state["last_refill"])
            refilled_tokens = min(
                self.capacity,
                float(state["tokens"]) + max(0, now - last_refill) * self.rate,
            )

            return {
                "identifier": identifier,
                "tokens": int(refilled_tokens + 1e-9),
                "capacity": self.capacity,
                "rate": self.rate,
                "last_refill": last_refill,
                "age_seconds": now - last_refill
            }
        except Exception as e:
            logger.error(f"Error getting bucket status: {e}")
            return {
                "identifier": identifier,
                "error": str(e)
            }
