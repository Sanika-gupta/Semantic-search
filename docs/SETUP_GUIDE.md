# Complete Setup Guide - VLA Research Engine

## Prerequisites

- Python 3.8 or higher
- MongoDB (local or cloud)
- Internet connection (for downloading models and arXiv data)

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pymongo` - MongoDB driver
- `sentence-transformers` - Embedding models
- `faiss-cpu` - Vector search
- `fastapi` + `uvicorn` - API server
- Other dependencies

**Note**: First install may take 5-10 minutes as it downloads PyTorch and transformers.

### 2. Set Up MongoDB

You have two options:

#### Option A: MongoDB Atlas (Recommended - Free & Easy)

1. **Create Account**:
   - Go to https://www.mongodb.com/cloud/atlas
   - Sign up for free account
   - Click "Build a Database"

2. **Create Free Cluster**:
   - Choose M0 (Free tier)
   - Select a cloud provider and region close to you
   - Name your cluster (e.g., "vla-research")
   - Click "Create Deployment"

3. **Set Up Access**:
   - Create database user:
     - Username: `vla_user` (or your choice)
     - Password: (generate secure password)
     - Save these credentials!
   
   - Add IP Address:
     - Click "Network Access"
     - Click "Add IP Address"
     - Click "Allow Access from Anywhere" (for development)
     - Or add your current IP

4. **Get Connection String**:
   - Click "Database" → "Connect"
   - Choose "Connect your application"
   - Copy the connection string
   - It looks like: `mongodb+srv://username:<password>@cluster.mongodb.net/`

5. **Update .env**:
   ```
   MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/
   MONGODB_DB_NAME=vla_research
   ```

#### Option B: Local MongoDB

1. **Download MongoDB**:
   - Windows: https://www.mongodb.com/try/download/community
   - Install as a service (recommended)
   - Or download ZIP and run manually

2. **Start MongoDB**:
   - If installed as service: Already running
   - If manual: Open terminal and run `mongod`

3. **Update .env**:
   ```
   MONGODB_URI=mongodb://localhost:27017/
   MONGODB_DB_NAME=vla_research
   ```

### 3. Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your MongoDB connection string
# Use a text editor or:
notepad .env  # Windows
```

Your `.env` should look like:
```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
# OR
MONGODB_URI=mongodb://localhost:27017/

MONGODB_DB_NAME=vla_research
ARXIV_BASE_URL=https://export.arxiv.org/api/query
MAX_RESULTS=3000
```

### 4. Test Connections

```bash
python test_connection.py
```

You should see:
```
✓ MongoDB connection successful!
✓ arXiv API connection successful!
```

**If MongoDB fails**:
- Atlas: Check username/password, IP whitelist
- Local: Make sure `mongod` is running

**If arXiv fails**:
- Check internet connection
- Check firewall settings
- Try again (arXiv API can be temperamental)

### 5. Ingest Papers (Phase 1)

Start with a small batch to test:

```bash
python ingest_arxiv.py --max-results 100
```

Expected output:
```
Fetching papers from arXiv API...
Successfully fetched 100 papers
Inserting papers into MongoDB...
Ingestion Complete
  New papers inserted: 100
  Total papers in database: 100
```

For full dataset:
```bash
python ingest_arxiv.py --max-results 3000
```

**Note**: This may take 10-15 minutes due to arXiv API rate limits (3-second delays).

### 6. Build Embeddings Index (Phase 2)

```bash
python build_index.py
```

Expected output:
```
Loading papers from MongoDB...
Loaded 100 papers

Initializing embedding model...
[Downloads model on first run - ~500MB]
Model loaded. Embedding dimension: 384

Generating embeddings...
[Progress bar]
Generated embeddings with shape: (100, 384)

Building FAISS index...
Added 100 embeddings to index

Saving index to disk...
Saved index to data/indexes/faiss_index.bin
```

**First run**: Downloads sentence-transformers model (~500MB)
**Subsequent runs**: Uses cached model

### 7. Verify Setup

```bash
python verify_setup.py
```

This checks:
- ✓ Dependencies installed
- ✓ Environment configured  
- ✓ MongoDB connected
- ✓ Papers in database
- ✓ Embeddings generated
- ✓ Index built
- ✓ Search working

If all checks pass, you're ready!

### 8. Start the API

```bash
python run_api.py
```

Output:
```
Starting server at http://0.0.0.0:8000
API docs available at http://0.0.0.0:8000/docs
```

Keep this terminal open - the server is running.

### 9. Test Search

Open a **new terminal** and run:

```bash
# Single query
python test_search.py robot manipulation with vision language models

# Health check
python test_search.py --health

# Interactive mode
python test_search.py
```

Or open browser to http://localhost:8000/docs for interactive API docs.

## Complete Workflow Example

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up .env file
cp .env.example .env
# Edit .env with MongoDB connection

# 3. Test connections
python test_connection.py

# 4. Ingest papers (Phase 1)
python ingest_arxiv.py --max-results 100

# 5. Build index (Phase 2)
python build_index.py

# 6. Verify everything
python verify_setup.py

# 7. Start API (keep running)
python run_api.py

# 8. In new terminal: test search
python test_search.py humanoid locomotion
```

## Troubleshooting

### "No module named 'X'"
```bash
pip install -r requirements.txt
```

### "MongoDB connection refused"
- **Local**: Start MongoDB: `mongod`
- **Atlas**: Check connection string, IP whitelist

### "Index not found"
```bash
python build_index.py
```

### "No papers in database"
```bash
python ingest_arxiv.py --max-results 100
```

### Model download fails
- Check internet connection
- HuggingFace models download on first `build_index.py` run
- Retry if interrupted

### arXiv API timeout
- Try smaller batch: `--max-results 100`
- Wait a few minutes and retry
- Check internet/firewall

## File Structure After Setup

```
vla-research-engine/
├── data/
│   └── indexes/
│       ├── faiss_index.bin      # Vector index
│       ├── metadata.pkl          # Paper IDs
│       └── model_info.txt        # Model metadata
├── .env                          # Your config (not in git)
└── [source files]
```

## Quick Commands Reference

```bash
# Test everything
python verify_setup.py

# Ingest more papers
python ingest_arxiv.py --max-results 500

# Rebuild index (after ingesting more)
python build_index.py

# Inspect data
python inspect_data.py
python inspect_data.py --search "manipulation"

# Start API
python run_api.py

# Test search
python test_search.py [your query]
python test_search.py --health
```

## Next Steps

Once Phase 1 & 2 are working:

- **Phase 3**: Custom rate limiter (token bucket)
- **Phase 4**: Semantic caching (similarity-based)
- **Phase 5**: Trend analysis (time-series)
- **Phase 6**: Clustering (auto-discover topics)

## Getting Help

If you encounter issues:

1. Run `python verify_setup.py` to diagnose
2. Check MongoDB is running: `python test_connection.py`
3. Check logs for specific error messages
4. Ensure all dependencies installed: `pip list | grep -E "(pymongo|faiss|sentence)"

## System Requirements

- **Disk**: ~2GB (500MB model + 500MB papers + indexes)
- **RAM**: 2GB minimum, 4GB recommended
- **CPU**: Any modern CPU (GPU not required)
- **Network**: For initial setup and ingestion

Enjoy building your VLA research engine! 🤖
