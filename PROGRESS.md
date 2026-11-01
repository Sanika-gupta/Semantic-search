# VLA Research Engine Progress

## Task 1 — done and tested

- Started: 2026-11-01
- Repository: initialized locally because this workspace did not contain a `.git` directory.
- Docker: unavailable on this machine (`docker` is not installed); rate-limiter tests use the existing in-test Redis double only.
- Changes: fixed fractional-token header rounding and moved refill/consume/state persistence into one Redis `EVAL` Lua script.
- Commands: `python -m pytest tests/test_rate_limiter.py -q`
- Result: 18 passed.

## Task 2 — next

- Start MongoDB if available, back up `data/indexes/faiss_index.bin` and `metadata.pkl`, paginate arXiv at 100 results/page with 3-second spacing, append/dedupe, then rebuild and compare MongoDB/FAISS counts.
