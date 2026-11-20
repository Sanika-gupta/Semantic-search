# Setup Required - Please Complete These Steps

This document lists what needs to be set up manually. Follow the steps below and fill in the information as you complete each one.

---

## Step 1: Fix MongoDB Connection

### Current Issue
MongoDB Atlas is showing SSL handshake error. Your current connection string in `.env`:
```
mongodb+srv://sanikagupto_db_user:<db_password>@vla.gzfpi57.mongodb.net/?appName=vla
```

### Choose One Option:

#### Option A: Fix MongoDB Atlas (Recommended - No Installation Needed)

**Steps:**
1. Go to https://cloud.mongodb.com/
2. Log in to your account
3. Click on "Network Access" in the left sidebar
4. Click "Add IP Address" button
5. Select "Allow Access from Anywhere" (or add your current IP)
6. Click "Confirm"
7. Wait 1-2 minutes for changes to propagate

**Test it:**
```bash
python test_connection.py
```

**Status:** [ ] Done / [ ] Not Done

---

#### Option B: Use Local MongoDB

**Steps:**
1. Download MongoDB Community Edition: https://www.mongodb.com/try/download/community
2. Install MongoDB
3. Start MongoDB service
4. Update `.env` file:
   ```
   MONGODB_URI=mongodb://localhost:27017/
   ```
5. Re-ingest data:
   ```bash
   python ingest_arxiv.py --max-results 100
   python build_index.py
   ```

**Status:** [ ] Done / [ ] Not Done

---

## Step 2: Set Up Redis

### Current Issue
Redis is not installed or running on your system.

### Choose One Option:

#### Option A: Redis Cloud (Recommended - No Installation Needed)

**Steps:**
1. Go to https://redis.com/try-free/
2. Create a free account
3. Click "New Database"
4. Select free tier (30MB is enough)
5. Copy the connection string (format: `redis://default:PASSWORD@HOST:PORT`)
6. Paste your Redis connection string below:

**Your Redis Connection String:**
```
REDIS_URI=redis://default:YOUR_PASSWORD_HERE@YOUR_HOST_HERE:PORT
redis-18752.c283.us-east-1-4.ec2.cloud.redislabs.com:18752
rE1UTKUwTGgWw9QDY1XVCeggZXNuHUr1
```

**Next:** Copy the line above to your `.env` file

**Status:** [ ] Done / [ ] Not Done

---

#### Option B: Install Redis Locally (Windows)

**Steps:**
1. Download Redis for Windows: https://github.com/tporadowski/redis/releases
2. Extract the zip file
3. Run `redis-server.exe`
4. Keep the terminal window open (Redis is running)
5. Your `.env` already has the correct setting:
   ```
   REDIS_URI=redis://localhost:6379/0
   ```

**Status:** [ ] Done / [ ] Not Done

---

## Step 3: Verify Everything Works

**After completing Steps 1 and 2, run these commands:**

### Test Connections
```bash
python test_connection.py
```

**Expected output:**
- ✓ MongoDB connection successful
- ✓ arXiv API connection successful

**Actual output:** _[Paste here after running]_

---

### Verify Full Setup
```bash
python verify_setup.py
```

**Expected output:**
- ✓ Dependencies installed
- ✓ Environment configured
- ✓ MongoDB connected with data
- ✓ Embeddings and index built
- ✓ Search functionality working
- ✓ API ready to start

**Actual output:** _[Paste here after running]_

---

### Test the API
```bash
# Terminal 1: Start the API
python run_api.py

# Terminal 2: Test a search
python test_search.py robot manipulation with vision language models
```

**Did it work?** [ ] Yes / [ ] No

**If No, paste the error message here:**
```
[Paste error here]
```

---

## Quick Checklist

- [ ] Step 1: MongoDB is connected (chose Option A or B)
- [ ] Step 2: Redis is set up (chose Option A or B)
- [ ] Step 3: `python test_connection.py` shows all green checkmarks
- [ ] Step 4: `python verify_setup.py` passes all checks
- [ ] Step 5: API starts without errors
- [ ] Step 6: Search test returns results

---

## Once Everything Works

**Tell me:**
1. Which options did you choose? (MongoDB: A/B, Redis: A/B)
2. Paste the output of `python test_connection.py`
3. Are you ready to proceed with Phase 4 (Semantic Caching)?

**Then I can:**
- Start building Phase 4: Semantic-Aware Caching
- Help with any issues you encountered
- Continue with the remaining phases

---

## Need Help?

If you get stuck on any step, paste the error message and I'll help troubleshoot!
