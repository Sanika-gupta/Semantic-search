# VLA/Humanoid Research Semantic Search & Trend Engine

A production-grade semantic search and trend-analysis API over VLA (Vision-Language-Action), VLM, and humanoid robotics research papers.

## Project Overview

This project enables natural language queries over robotics research papers ("robot manipulation with language grounding") and provides semantically relevant results, clustered by sub-topic, with trend tracking over time.

## Tech Stack

- **Data Source**: arXiv API (cs.RO, cs.CV, cs.LG, cs.AI categories)
- **Database**: MongoDB (metadata storage)
- **Embeddings**: sentence-transformers
- **Vector Store**: FAISS
- **Backend**: FastAPI
- **Caching**: Redis
- **Frontend**: React + Recharts
- **Load Testing**: Locust

## Project Structure

```
vla-research-engine/
├── config/              # Configuration and settings
├── ingestion/           # Data ingestion pipeline (Phase 1)
├── embeddings/          # Embedding generation and vector store (Phase 2)
├── api/                 # FastAPI backend (Phase 2)
├── tests/               # Test suites
├── ingest_arxiv.py      # Phase 1: Ingest papers from arXiv
├── build_index.py       # Phase 2: Build embeddings and FAISS index
├── run_api.py           # Phase 2: Run API server
├── test_search.py       # Phase 2: Test search functionality
└── requirements.txt
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up MongoDB

**Option A: Local MongoDB**
- Install MongoDB locally: https://www.mongodb.com/try/download/community
- Start MongoDB service: `mongod` (default port 27017)

**Option B: MongoDB Atlas (Recommended for simplicity)**
- Create free account at https://www.mongodb.com/cloud/atlas
- Create a cluster
- Get connection string and update `.env`

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your MongoDB connection string:
```
MONGODB_URI=mongodb://localhost:27017/
# Or for MongoDB Atlas:
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DB_NAME=vla_research
```

## Phase 1: arXiv Ingestion Pipeline

### Test Your Setup

Before running the full ingestion, test your connections:

```bash
python test_connection.py
```

This will verify:
- MongoDB connection
- arXiv API connectivity

### Run the Ingestion

Fetch VLA/VLM/humanoid papers from arXiv and store in MongoDB:

```bash
python ingest_arxiv.py
```

### Options

```bash
# Fetch specific number of papers
python ingest_arxiv.py --max-results 1000

# Dry run (fetch but don't insert)
python ingest_arxiv.py --dry-run

# Pagination (start from index 100)
python ingest_arxiv.py --start 100 --max-results 500
```

### What It Does

1. Queries arXiv API with filters:
   - **Categories**: cs.RO, cs.CV, cs.LG, cs.AI
   - **Keywords**: VLA, VLM, humanoid, vision language action, vision language model, embodied AI, robot learning

2. Extracts and stores:
   - Title
   - Abstract
   - Authors
   - Publication date
   - arXiv ID
   - Categories
   - PDF URL

3. MongoDB schema:
   - Indexes on `arxiv_id` (unique), `published_date`, `categories`
   - Full-text search index on `title` and `abstract`

### Expected Results

- Target: 1,000-3,000 papers
- Duplicate detection via arXiv ID
- Papers sorted by submission date (most recent first)

## Phase 2: Embeddings + Semantic Search

### Build the Index

Generate embeddings and create FAISS index:

```bash
python build_index.py
```

This will:
1. Load all papers from MongoDB
2. Generate embeddings using sentence-transformers (all-MiniLM-L6-v2)
3. Create FAISS index for similarity search
4. Save index to `data/indexes/`
5. Run test queries to verify functionality

Options:
```bash
# Use better quality model (slower, 768 dims)
python build_index.py --model all-mpnet-base-v2

# Custom batch size
python build_index.py --batch-size 64
```

### Test the System

Run the comprehensive test suite:

```bash
python tests/test_phase2.py
```

This tests:
- MongoDB connection
- Embedding generation
- Vector store creation and search
- Index persistence (save/load)

### Run the API Server

Start the FastAPI server:

```bash
python run_api.py
```

The server will start at `http://localhost:8000`

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

Options:
```bash
# Run with auto-reload for development
python run_api.py --reload

# Custom port
python run_api.py --port 8080
```

### Test Search

Using the CLI tool:

```bash
# Single query
python test_search.py robot manipulation with vision language models

# Get more results
python test_search.py -k 10 humanoid locomotion learning

# Check API health
python test_search.py --health

# Interactive mode
python test_search.py
```

Using curl:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "robot manipulation with vision language models", "k": 5}'
```

### Example Queries

Try these natural language queries:

- "robot manipulation with vision language models"
- "humanoid locomotion and balance control"
- "diffusion policy for robot learning"
- "world models for robotic planning"
- "imitation learning from human demonstrations"
- "sim-to-real transfer for robot control"

## Development Roadmap

- [x] **Phase 1**: arXiv ingestion pipeline (3-4 hrs)
- [x] **Phase 2**: Embeddings + semantic search (3-4 hrs)
- [ ] **Phase 3**: Custom rate limiter (3-4 hrs)
- [ ] **Phase 4**: Semantic-aware caching (2-3 hrs)
- [ ] **Phase 5**: Trend analysis (2-3 hrs)
- [ ] **Phase 6**: Clustering (stretch, 2-3 hrs)
- [ ] **Phase 7**: Local orchestration + load testing (2-3 hrs)

### Inspect Your Data

After ingestion, explore the data:

```bash
# Show summary statistics and recent papers
python inspect_data.py

# Show top 10 recent papers
python inspect_data.py --recent 10

# Search for papers with keyword
python inspect_data.py --search "manipulation"

# Summary statistics only
python inspect_data.py --summary
```

## Complete Workflow

### First Time Setup

See **[SETUP_GUIDE.md](SETUP_GUIDE.md)** for detailed instructions.

Quick version:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up MongoDB (MongoDB Atlas free tier recommended)
# 3. Configure .env
cp .env.example .env
# Edit .env with your MongoDB connection string

# 4. Test connections
python test_connection.py

# 5. Run Phase 1: Ingest papers
python ingest_arxiv.py --max-results 100

# 6. Run Phase 2: Build search index
python build_index.py

# 7. Verify everything
python verify_setup.py

# 8. Start API
python run_api.py

# 9. Test search (in new terminal)
python test_search.py robot manipulation
```

## Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup instructions
- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)** - Phase 2 technical details
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current status and roadmap
- **[spec.md](spec.md)** - Original project specification

## Current Status

- ✅ **Phase 1**: arXiv ingestion pipeline
- ✅ **Phase 2**: Embeddings + semantic search API
- ⬜ **Phase 3**: Custom rate limiter
- ⬜ **Phase 4**: Semantic caching
- ⬜ **Phase 5**: Trend analysis
- ⬜ **Phase 6**: Clustering (stretch)
- ⬜ **Phase 7**: Load testing

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for details.

## Performance

Current metrics (Phase 2):
- **Search latency**: ~15-30ms per query
- **Embedding generation**: ~30-60s for 1000 papers
- **Index size**: ~1.5MB per 1000 papers
- **Memory**: ~100MB (model) + ~1.5MB per 1000 papers (index)

## Tech Highlights

This project demonstrates:
- ✅ **Real ML**: Semantic embeddings, vector similarity search
- ✅ **Systems Engineering**: FastAPI backend, MongoDB indexing, FAISS vector store
- ✅ **End-to-End Pipeline**: Data ingestion → processing → search → API
- ⏳ **Rate Limiting**: Token bucket (Phase 3)
- ⏳ **Caching**: Similarity-aware semantic cache (Phase 4)
- ⏳ **Metrics**: Load testing with real numbers (Phase 7)

## License

MIT
