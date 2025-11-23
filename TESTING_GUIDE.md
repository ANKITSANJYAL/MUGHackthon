# Testing Guide - RAG Setup Checklist

Follow these steps in order to test the RAG system before committing to GitHub.

## ✅ Pre-Testing Checklist

### 1. MongoDB Atlas Setup (Do this first!)

- [ ] Create MongoDB Atlas account at https://mongodb.com/cloud/atlas
- [ ] Create FREE M0 cluster (takes 3-5 minutes)
- [ ] Create database user (username + password)
- [ ] Add IP address to whitelist (0.0.0.0/0 for testing)
- [ ] Get connection string from "Connect" button
- [ ] Replace `<password>` in connection string with actual password

### 2. OpenAI API Key

- [ ] Get API key from https://platform.openai.com/api-keys
- [ ] Ensure you have credits in your account (embeddings are cheap: ~$0.0001)

### 3. Local Environment Setup

- [ ] Edit `.env` file with your credentials:
```bash
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/...
MONGODB_DB_NAME=JIAE_Knowledge_Base
MONGODB_COLLECTION_NAME=PastFixes
OPENAI_API_KEY=sk-proj-...
```

- [ ] Dependencies installed: `pip install -r requirements.txt` ✅ DONE

## 🧪 Testing Steps

### Step 1: Test MongoDB Connection

Run this command to test if MongoDB Atlas connection works:

```bash
python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGODB_URI')); client.admin.command('ping'); print('✅ MongoDB connection successful!'); client.close()"
```

**Expected output**: `✅ MongoDB connection successful!`

**If it fails**: 
- Check connection string in `.env`
- Verify password is correct (no < > brackets)
- Check IP whitelist in Atlas

---

### Step 2: Test OpenAI API

Run this command to test OpenAI embeddings:

```bash
python -c "from openai import OpenAI; import os; from dotenv import load_dotenv; load_dotenv(); client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')); response = client.embeddings.create(model='text-embedding-3-small', input='test'); print(f'✅ OpenAI working! Got {len(response.data[0].embedding)} dimensions')"
```

**Expected output**: `✅ OpenAI working! Got 1536 dimensions`

**If it fails**:
- Check OPENAI_API_KEY in `.env`
- Verify API key is active at https://platform.openai.com/api-keys
- Check if you have credits/billing set up

---

### Step 3: Run RAG Database Setup

This will:
- Connect to MongoDB Atlas
- Load 15 seed documents
- Generate embeddings for each document
- Insert documents with vectors into database

```bash
python rag/setup_vector_rag.py
```

**Expected output**:
```
================================================================================
  JIAE Vector RAG Database Setup
  MongoDB Atlas + OpenAI Embeddings
================================================================================
🔌 Connecting to MongoDB Atlas...
✅ Connected to database: JIAE_Knowledge_Base
   Collection: PastFixes

📊 Creating database indexes...
  ✓ Created unique index on source_id
  ✓ Created index on project_module
  ✓ Created index on fix_type
  ✓ Created text index on ticket_summary

⚠️  IMPORTANT: You must create the Vector Search Index manually in Atlas UI:
   1. Go to Atlas → Your Cluster → Search Indexes
   2. Click 'Create Search Index' → 'JSON Editor'
   3. Use the vector_index_definition.json file
   4. Name it: 'vector_index'

📥 Loading and embedding documents from: ../rag_data/seed_documents.json
  Found 15 documents to process
  Generating embeddings with text-embedding-3-small...

  [1/15] Embedding JIRA-301...
      ✓ Inserted with 1536-dim vector
  [2/15] Embedding JIRA-302...
      ✓ Inserted with 1536-dim vector
  ...
  [15/15] Embedding RUNBOOK-101...
      ✓ Inserted with 1536-dim vector

✅ Successfully inserted 15 documents with embeddings
...
✅ Vector RAG Database Setup Complete!
```

**Cost**: ~$0.0001 (1/100th of a cent)

**If it fails**: Check the error message and fix the issue before continuing

---

### Step 4: Verify Data in MongoDB Atlas

1. Go to MongoDB Atlas → Database → Browse Collections
2. You should see:
   - Database: `JIAE_Knowledge_Base`
   - Collection: `PastFixes`
   - 15 documents
3. Click on a document to see it has an `embedding` array with 1536 numbers

---

### Step 5: Create Vector Search Index (CRITICAL!)

**This must be done manually in Atlas UI for semantic search to work!**

1. In Atlas, go to your cluster
2. Click **"Search"** tab (NOT "Browse Collections")
3. Click **"Create Search Index"**
4. Choose **"JSON Editor"**
5. Select:
   - Database: `JIAE_Knowledge_Base`
   - Collection: `PastFixes`
6. Paste this JSON:

```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "type": "knnVector",
        "dimensions": 1536,
        "similarity": "cosine"
      },
      "project_module": {
        "type": "string"
      },
      "fix_type": {
        "type": "string"
      }
    }
  }
}
```

7. Name it: **`vector_index`** (exactly this!)
8. Click **"Create Search Index"**
9. **Wait 2-3 minutes** for it to build (status will show "Active")

---

### Step 6: Test RAG Queries

Once the vector index is ACTIVE, test semantic search:

```bash
python rag/query_rag.py
```

**Expected output**: Three semantic search results showing relevant fixes for:
1. Authentication issues
2. Database performance issues  
3. API configuration issues

Each result should show:
- Source ID
- Similarity score
- Internal context
- Gold patch snippet

---

## 🎉 Success Criteria

You're ready to commit when:

- [ ] MongoDB Atlas cluster is running
- [ ] 15 documents inserted with embeddings
- [ ] Vector Search Index is ACTIVE
- [ ] `query_rag.py` returns relevant results for all 3 test queries
- [ ] No errors in any of the test commands

---

## 🐛 Common Issues

### "ServerSelectionTimeoutError"
- MongoDB URI is wrong or IP not whitelisted
- Fix: Check `.env` and Atlas Network Access

### "AuthenticationFailed"  
- Wrong password in connection string
- Fix: Regenerate password in Atlas Database Access

### "RateLimitError" from OpenAI
- No credits or invalid API key
- Fix: Add payment method at https://platform.openai.com/account/billing

### "Index not found" in query_rag.py
- Vector index not created or still building
- Fix: Wait for index to show "Active" status in Atlas

---

## 📝 After Successful Testing

Once all tests pass:

1. Take screenshots of:
   - MongoDB Atlas showing 15 documents
   - Vector index showing "Active" status
   - Terminal output of successful `query_rag.py` run

2. Commit to GitHub:
```bash
git add .
git status  # Review changes
git commit -m "feat: Set up MongoDB Atlas RAG with vector embeddings

- Added 15 seed documents across 3 scenarios (auth, db, config)
- Implemented OpenAI embeddings (1536-dim)
- Created query engine with semantic search
- Verified working with dummy codebase bugs"
git push origin rag-setup
```

3. Create PR to main branch

---

## 💰 Cost Summary

- MongoDB Atlas: **$0** (Free M0 tier)
- OpenAI Embeddings:
  - Setup: **~$0.0001** (15 docs × ~200 tokens)
  - Per query: **~$0.000002**
  - Total demo: **< $0.01**

**Total hackathon cost: FREE to $0.01**
