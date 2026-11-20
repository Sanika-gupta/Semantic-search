# Quick Reference Card

## 🚀 Most Common Commands

```bash
# Start API server
python run_api.py

# Search from CLI
python test_search.py [your query]
python test_search.py -k 10 robot learning

# Check system health
python test_search.py --health
python verify_setup.py

# Ingest more papers
python ingest_arxiv.py --max-results 500

# Rebuild index (after ingesting)
python build_index.py

# Inspect data
python inspect_data.py
python inspect_data.py --search "VLA"
```

## 🌐 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| http://localhost:8000/docs | GET | Interactive API docs |
| http://localhost:8000/health | GET | Health check |
| http://localhost:8000/search | POST | Semantic search |

## 📝 Example Queries

### Via CLI
```bash
python test_search.py robot manipulation with vision language models
python test_search.py humanoid locomotion and balance
python test_search.py learning from demonstrations
python test_search.py diffusion policy for robot control
python test_search.py sim to real transfer
```

### Via curl
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "robot manipulation", "k": 5}'
```

### Via Python
```python
import requests

r = requests.post(
    "http://localhost:8000/search",
    json={"query": "robot learning", "k": 5}
)
print(r.json())
```

## 📊 Current System Stats

- **Papers**: 100
- **Embedding dim**: 384
- **Model**: all-MiniLM-L6-v2
- **Index size**: ~157 KB
- **Search latency**: ~150-250ms
- **Database**: MongoDB Atlas (cloud)

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| API won't start | `python verify_setup.py` |
| "Index not found" | `python build_index.py` |
| "No papers" | `python ingest_arxiv.py` |
| MongoDB error | Check .env file |
| Slow searches | Normal for first query (model load) |

## 📂 Project Structure

```
vla-research-engine/
├── api/                 # FastAPI backend
├── embeddings/          # Embedding + FAISS
├── ingestion/           # arXiv + MongoDB
├── config/              # Settings
├── data/indexes/        # Stored index
├── build_index.py       # Build search index
├── run_api.py           # Start API
├── test_search.py       # CLI search
└── verify_setup.py      # System check
```

## 🎯 Next Phases

- [ ] Phase 3: Custom rate limiter
- [ ] Phase 4: Semantic caching  
- [ ] Phase 5: Trend analysis
- [ ] Phase 6: Clustering
- [ ] Phase 7: Load testing

See **PROJECT_STATUS.md** for details.

## 📚 Documentation

- **WORKING_DEMO.md** - Demo with examples
- **SETUP_GUIDE.md** - Detailed setup
- **PHASE2_COMPLETE.md** - Technical deep-dive
- **PROJECT_STATUS.md** - Roadmap
- **README.md** - Overview

## ⚡ Key Features

✅ Semantic search (meaning, not keywords)  
✅ Fast (sub-300ms queries)  
✅ RESTful API with docs  
✅ Persistent index  
✅ Health monitoring  
✅ Similarity scores  

## 🎤 Interview Soundbites

> "I built a semantic search engine over 100+ robotics papers using sentence-transformers for embeddings and FAISS for vector similarity search, deployed as a FastAPI service with sub-300ms query latency."

> "The system demonstrates real ML engineering - not just calling an API, but implementing the full pipeline from data ingestion through embedding generation to vector search and retrieval."

> "It's production-ready with health checks, error handling, and proper API design, and I have clear metrics on performance and scalability bottlenecks."

---

**Status: ✅ Phases 1 & 2 Complete**  
**API: Running at http://localhost:8000**  
**Ready for Phase 3!**
