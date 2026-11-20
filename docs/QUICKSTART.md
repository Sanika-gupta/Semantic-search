# Quick Start Guide

Get the VLA Research Engine running in minutes.

## Prerequisites

- Python 3.8+
- MongoDB (local or MongoDB Atlas free tier)

## 5-Minute Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure MongoDB

**Easy Option: MongoDB Atlas (Free)**
1. Go to https://www.mongodb.com/cloud/atlas
2. Create free account
3. Create a free cluster (M0)
4. Click "Connect" → "Connect your application"
5. Copy the connection string

**Local Option:**
- Install MongoDB: https://www.mongodb.com/try/download/community
- Start MongoDB: `mongod`
- Use default: `mongodb://localhost:27017/`

### 3. Set Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:
```
MONGODB_URI=your_connection_string_here
MONGODB_DB_NAME=vla_research
```

### 4. Test Connection

```bash
python test_connection.py
```

You should see:
```
✓ MongoDB connection successful!
✓ arXiv API connection successful!
```

### 5. Run Ingestion

```bash
# Start with a smaller batch for testing
python ingest_arxiv.py --max-results 100

# Then run full ingestion
python ingest_arxiv.py
```

Expected output:
```
Fetching papers from arXiv API...
Successfully fetched 100 papers
Inserting papers into MongoDB...
✓ Ingestion Complete
  New papers inserted: 100
  Total papers in database: 100
```

### 6. Inspect Data

```bash
python inspect_data.py
```

## Common Issues

### "Connection refused" (MongoDB)

**Local MongoDB:**
- Make sure MongoDB is running: `mongod`
- Check it's listening on port 27017

**MongoDB Atlas:**
- Add your IP to whitelist (Network Access → Add IP Address → Add Current IP)
- Check username/password in connection string
- Ensure connection string format: `mongodb+srv://username:password@cluster.mongodb.net/`

### "No module named 'pymongo'"

```bash
pip install -r requirements.txt
```

### "Request timeout" (arXiv API)

- The script already has 3-second delays between requests
- If still timing out, try smaller batches: `--max-results 500`

## Next Steps

1. ✓ Phase 1 complete - you have papers in MongoDB
2. Next: Generate embeddings (Phase 2)
3. Then: Build semantic search API (Phase 2)

## Quick Reference

```bash
# Test connections
python test_connection.py

# Ingest papers
python ingest_arxiv.py                    # Full ingestion (~3000 papers)
python ingest_arxiv.py --max-results 100  # Small batch
python ingest_arxiv.py --dry-run          # Test without inserting

# Inspect data
python inspect_data.py                    # Summary + 5 recent papers
python inspect_data.py --recent 10        # Show 10 recent papers
python inspect_data.py --search "VLA"     # Search by keyword
```

## Architecture (Phase 1)

```
arXiv API
    ↓
ArxivClient (filters by cs.RO/CV/LG + VLA/VLM keywords)
    ↓
MongoDB (papers collection)
    ↓
MongoDBClient (CRUD operations)
```

Indexed fields: `arxiv_id`, `published_date`, `categories`, `title+abstract` (full-text)
