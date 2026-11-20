# Phase 3: Token Bucket Rate Limiter - Quick Reference

## ✅ Status: COMPLETE

Implemented a production-ready token bucket rate limiter from scratch with Redis backend.

## Quick Start

### Prerequisites

```bash
# Install Redis (if not already installed)
# Windows: https://redis.io/download
# Mac: brew install redis
# Linux: sudo apt-get install redis-server

# Start Redis
redis-server
```

### Run Tests

```bash
# Unit tests (no Redis needed - uses mocks)
pytest tests/test_rate_limiter.py -v
# Expected: 18 passed

# Manual tests (requires Redis + running API)
python run_api.py  # Terminal 1
python test_rate_limiter_manual.py  # Terminal 2
```

### Configuration

Edit `.env`:
```bash
REDIS_URI=redis://localhost:6379/0
RATE_LIMIT_REQUESTS_PER_MINUTE=10
RATE_LIMIT_BURST_CAPACITY=20
```

## What's Implemented

### Files Created

```
rate_limiter/
├── __init__.py           # Package exports
├── token_bucket.py       # Core algorithm (250 lines)
└── middleware.py         # FastAPI middleware (200 lines)

tests/
└── test_rate_limiter.py  # 18 unit tests (450 lines)

test_rate_limiter_manual.py  # 6 manual integration tests
PHASE3_COMPLETE.md            # Detailed documentation
```

**Total**: ~900 lines of production code + tests

### Algorithm

- **Token Bucket** with time-based refill
- **Redis backend** for distributed state
- **Per-IP tracking** with proxy header support
- **Fail-open** behavior on Redis errors
- **10 req/min** sustained, **20 burst** capacity

### API Behavior

**Success (200)**:
```http
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 15
X-RateLimit-Reset: 1786284892
```

**Rate Limited (429)**:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 6

{"error": "rate_limit_exceeded", "message": "...", "retry_after": 6}
```

## Testing Coverage

### Unit Tests (18 total)

✅ Initial bucket state  
✅ Burst then throttle  
✅ Token refill over time  
✅ Concurrent access (thread safety)  
✅ Redis failure (fail-open)  
✅ Retry-After calculation  
✅ Client IP extraction  
✅ Path exclusion  
✅ Edge cases (zero tokens, overflow, etc.)

### Manual Tests (6 scenarios)

1. Basic search with rate limit headers
2. Burst 25 requests → 20 succeed, 5 throttled
3. Retry-After header validation
4. Excluded paths (health unlimited)
5. Token refill over 12 seconds
6. Client separation (different IPs)

## Quick Demo

```bash
# Terminal 1: Start services
redis-server

# Terminal 2: Start API
python run_api.py

# Terminal 3: Test burst behavior
for i in {1..25}; do
  curl -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -d '{"query":"test","k":1}' \
    -w "%{http_code}\n" -o /dev/null -s
done
# Output: 20x "200", then 5x "429"

# Check 429 response headers
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test","k":1}' -i
# Shows: X-RateLimit-*, Retry-After headers
```

## Interview Highlights

**Token bucket from scratch** - No libraries, full algorithm implementation  
**Redis-backed distributed state** - Thread-safe, atomic operations  
**Fail-open design** - Graceful degradation on Redis failures  
**Comprehensive testing** - 18 unit tests + 6 integration tests  
**Production-ready** - Proper headers, client identification, path exclusion

## Next: Phase 4

Semantic caching with Redis (2-3 hours)
- Cache by query embedding similarity (not exact match)
- Measure cache hit rate and latency improvement
- Build on Phase 3 Redis infrastructure

---

See `PHASE3_COMPLETE.md` for full technical documentation and architecture details.
