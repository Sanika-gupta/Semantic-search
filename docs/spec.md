# VLA/Humanoid Research Semantic Search & Trend Engine

## Core Value Proposition

A production-shaped semantic search and trend-analysis API over VLA (Vision-Language-Action), VLM, and humanoid robotics research papers — letting you query in natural language ("robot manipulation with language grounding") and get semantically relevant papers, clustered by sub-topic, with trend tracking over time (e.g., "VLA papers per month since 2023").

**Why this is defensible, not generic:**

- Real ML: embeddings \+ vector similarity search \+ clustering, evaluated with actual precision/recall numbers on a held-out query set — not just "I called an API."  
- Real systems engineering: caching a *semantic* search (non-trivial — queries aren't exact-match, so naive caching doesn't work) \+ rate limiting built from scratch \+ load-tested throughput/latency numbers.  
- Authentic narrative: ties directly to your ROS/robotics background, so "why I built this" isn't manufactured.

---

## Architectural Overview

                        ┌─────────────────────┐

                        │   arXiv API /        │

                        │   Papers With Code    │   (Data Source)

                        └──────────┬───────────┘

                                   │

                          \[Ingestion Pipeline\]

                                   │

                     ┌─────────────▼─────────────┐

                     │  Preprocessing \+ Chunking   │

                     │  (title, abstract, metadata)│

                     └─────────────┬─────────────┘

                                   │

                     ┌─────────────▼─────────────┐

                     │   Embedding Generation       │

                     │  (sentence-transformers)     │

                     └─────────────┬─────────────┘

                                   │

                     ┌─────────────▼─────────────┐

                     │   Vector Store (FAISS/       │

                     │   Chroma) \+ Metadata DB       │

                     │   (MongoDB/Postgres)          │

                     └─────────────┬─────────────┘

                                   │

        ┌──────────────────────────▼──────────────────────────┐

        │                    FastAPI Backend                    │

        │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐  │

        │  │ /search     │ │ /trends     │ │ /cluster          │  │

        │  └────────────┘ └────────────┘ └──────────────────┘  │

        │           │              │                │           │

        │  ┌────────▼──────────────▼────────────────▼────────┐ │

        │  │   Rate Limiter (token bucket, custom-built)       │ │

        │  └────────────────────────┬───────────────────────┘ │

        │  ┌────────────────────────▼───────────────────────┐ │

        │  │   Redis Cache (query-embedding-hash based)        │ │

        │  └────────────────────────────────────────────────┘ │

        └────────────────────────────┬──────────────────────┘

                                     │

                          ┌──────────▼──────────┐

                          │   React Frontend      │

                          │  (search UI \+ trend    │

                          │   charts via Recharts) │

                          └────────────────────────┘

        \[FastAPI backend, Redis, and MongoDB run as local

         processes/services, orchestrated via a simple

         Procfile or shell script — no containers\]

        \[Locust/wrk load-tests the API layer directly\]

---

## Tech Stack

| Layer | Choice | Why |
| :---- | :---- | :---- |
| **Data source** | arXiv API (cs.RO, cs.CV, cs.LG categories) | Free, well-documented, real ongoing research data |
| **Embeddings** | `sentence-transformers` (e.g., `all-MiniLM-L6-v2` or `all-mpnet-base-v2`) | Runs locally, no API cost, good semantic quality |
| **Vector store** | FAISS (local, no server) or ChromaDB (if you want persistence \+ metadata filtering) | FAISS \= faster to implement; Chroma \= more production-like |
| **Metadata DB** | MongoDB (you already know it) or PostgreSQL | Store paper metadata, authors, dates, categories |
| **Backend API** | FastAPI (Python) | Async support, auto docs, plays well with ML stack |
| **Caching** | Redis | Cache repeated/similar queries |
| **Rate limiting** | Custom token-bucket implementation (no library) | This is your technical "spike" — the thing you explain deeply in interviews |
| **Frontend** | React \+ Recharts | Search UI \+ trend visualization (you know this stack already) |
| **Process orchestration** | Shell script / `Procfile` \+ `honcho` (or just multiple terminal tabs) | Run API, Redis, Mongo, frontend as local processes — no container overhead |
| **Load testing** | Locust or `wrk` | Generate real throughput/latency numbers |
| **Clustering (stretch)** | `scikit-learn` (KMeans or HDBSCAN on embeddings) | Groups papers into sub-topics (e.g., "manipulation," "locomotion," "world models") |

---

## Core Features (in priority order)

### 1\. Ingestion Pipeline (3-4 hrs)

- Pull papers from arXiv API filtered by VLA/VLM/humanoid-relevant keywords and categories (cs.RO, cs.CV, cs.LG, cs.AI)  
- Store title, abstract, authors, date, arXiv ID, category in MongoDB  
- Target: 1,000-3,000 papers is plenty — don't over-scope the dataset size

### 2\. Embedding \+ Semantic Search (3-4 hrs)

- Generate embeddings for title+abstract using sentence-transformers  
- Store in FAISS index  
- `/search?q=...` endpoint: embed query, do cosine similarity search, return top-k papers  
- **Eval metric to report:** build a small hand-labeled test set (\~20-30 queries with expected relevant papers) and report precision@5 or NDCG — this is your "real ML eval number"

### 3\. Custom Rate Limiter (3-4 hrs) — your technical spike

- Implement token bucket algorithm from scratch (per-IP or per-API-key buckets)  
- No library — this is the part you go deep on in interviews  
- Return proper `429 Too Many Requests` with `Retry-After` headers

### 4\. Semantic-Aware Caching (2-3 hrs)

- Naive caching (exact query string match) misses semantically identical queries  
- Better approach: cache by rounding/hashing the query embedding to a bucket, or cache top-k results keyed by a similarity threshold to previously seen queries  
- **This is a real, explainable design decision** — "why does normal caching not work for semantic search, and what did I do instead"

### 5\. Trend Analysis (2-3 hrs)

- `/trends` endpoint: paper count over time, broken down by sub-topic/keyword (e.g., "VLA," "diffusion policy," "world models") — simple time-series aggregation on your metadata DB  
- Frontend chart via Recharts

### 6\. Clustering (stretch, 2-3 hrs if time allows)

- Run KMeans/HDBSCAN on embeddings to auto-discover sub-topic clusters  
- Label clusters using top TF-IDF terms per cluster or an LLM call to name them

### 7\. Local Orchestration \+ Load Testing (2-3 hrs)

- Install Redis and MongoDB locally (or use free-tier hosted versions — Redis Cloud, MongoDB Atlas — so you don't have to manage servers yourself)  
- A simple shell script or `Procfile` (run with `honcho start`) to bring up API \+ frontend together  
- Locust script simulating concurrent search requests against the running API  
- **Numbers to report:** requests/sec sustained, p95/p99 latency, cache hit rate, latency with vs. without cache

---

## Realistic Time Budget

| Phase | Hours |
| :---- | :---- |
| Ingestion pipeline | 3-4 |
| Embeddings \+ search | 3-4 |
| Rate limiter | 3-4 |
| Caching layer | 2-3 |
| Trends endpoint \+ frontend chart | 2-3 |
| Local orchestration \+ load testing | 2-3 |
| **Total (excluding stretch)** | **\~16-21 hrs** |
| Clustering (stretch) | \+2-3 |

Spread over 2-3 weeks at \~1-1.5 hrs/day on non-OA-heavy days, this is realistic without eating into DSA/GRE time.

---

## Resume Bullets This Will Actually Produce (examples — fill in real numbers once built)

- "Built a semantic search engine over 2,000+ VLA/robotics research papers using sentence-transformer embeddings and FAISS, achieving X precision@5 on a hand-labeled query set"  
- "Designed a custom token-bucket rate limiter and similarity-aware caching layer, reducing p95 query latency by X% under load"  
- "Load-tested the API to sustain X req/s with Y ms p99 latency using Locust, orchestrating Redis, MongoDB, and the API as coordinated local services"  
- "Implemented trend analysis over research metadata, surfacing publication velocity across VLA sub-topics (manipulation, locomotion, world models)"

---

## Interview Talking Points (rehearse these)

1. **"Why did normal caching not work for semantic search, and what did you do instead?"** — the similarity-bucket caching design.  
2. **"Walk me through your rate limiter"** — token bucket internals, why you chose it over sliding window/fixed window.  
3. **"How did you evaluate search quality?"** — your precision@5/NDCG setup and what the number actually means.  
4. **"What would you do differently at 10x scale?"** — sharding the vector index, moving to a managed vector DB (Pinecone/Weaviate), async ingestion.

---

## What to Skip (protect your 30-day window)

- Don't fine-tune any models — pretrained sentence-transformers is enough, fine-tuning eats days for marginal gain.  
- Don't build user auth/accounts — not needed for the story.  
- Don't try to scrape full PDFs — abstracts \+ metadata are enough signal for search and are far faster to ingest.  
- Skip the frontend polish — a functional, unstyled React page is fine. This is a backend/ML systems project, not a design portfolio piece.  
- Skip Docker/containers — local processes plus hosted free-tier Redis/MongoDB (Redis Cloud, MongoDB Atlas) is simpler to set up and one less thing to debug. You can always containerize later if you want the "infra" talking point, but it's not required to tell this story well.

