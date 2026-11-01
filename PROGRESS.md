# VLA Research Engine Progress

## Task 1 — done and tested

- Started: 2026-11-01
- Repository: initialized locally because this workspace did not contain a `.git` directory.
- Docker: unavailable on this machine (`docker` is not installed); rate-limiter tests use the existing in-test Redis double only.
- Changes: fixed fractional-token header rounding and moved refill/consume/state persistence into one Redis `EVAL` Lua script.
- Commands: `python -m pytest tests/test_rate_limiter.py -q`
- Result: 18 passed.

## Task 2 — blocked

- Backup created: `backups/20261101-133009/` contains the pre-rebuild FAISS index and metadata.
- Existing index evidence: `data/indexes/model_info.txt` reports 100 papers and FAISS vectors.
- Docker is not installed, so the required local MongoDB container cannot be started.
- The active Python environment is missing `pydantic_settings`; `python -m pip install -r requirements.txt` failed both sandboxed and elevated because no package index is reachable (`pymongo==4.6.1` could not be downloaded).
- Therefore MongoDB cannot be queried, arXiv cannot be ingested, the 2,000-paper rebuild cannot be run, and tasks 3–7 must not be started because they depend on Task 2’s live corpus and dependencies.
- Resume after Docker and Python package-index access are available:
  1. `docker run -d --name vla-mongo -p 27017:27017 mongo:7`
  2. `python -m pip install -r requirements.txt rank_bm25`
  3. update `ingest_arxiv.py`/`ingestion/arxiv_client.py` for 100-paper pagination with 3-second delays, then run ingestion and `python build_index.py`.
  4. query MongoDB and FAISS counts; continue at Task 3.
