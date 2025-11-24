# RAG Setup - MongoDB Atlas Vector Search

This module implements the **Retrieval-Augmented Generation (RAG)** system for JIAE using MongoDB Atlas Vector Search with OpenAI embeddings.

## Architecture Overview

### Data Structure (Per Proposal)

Each document in the `PastFixes` collection contains:

| Field | Type | Purpose |
|-------|------|---------|
| `_id` | ObjectId | MongoDB primary key |
| `source_id` | String | Original ticket ID (JIRA-XXX, PR-XXX, AD-XXX) |
| `ticket_summary` | String | Human-readable fix summary |
| `project_module` | String | Code area (user_auth, db_query_optimization, api_gateway) |
| `internal_context` | String | **The text to be embedded** - detailed fix explanation |
| `embedding` | Array[Float] | **1536-dimensional vector** from OpenAI |
| `fix_type` | String | Logic, Config, DB_Query, API_Internal |
| `gold_patch_snippet` | String | Reference code snippet for the fix |

### Three Scenarios (15 Documents Total)

1. **Scenario 1: Critical Internal Function** (5 docs)
   - Module: `user_auth`
   - Issue: Missing organization prefix in `_security_hash_id()` function
   - RAG Query: "How do I map user tokens with organization context?"

2. **Scenario 2: Database Query Optimization** (5 docs)
   - Module: `db_query_optimization`
   - Issue: Missing compound index on `(user_id, timestamp)`
   - RAG Query: "What index is needed for user activity queries?"

3. **Scenario 3: Configuration Mistake** (5 docs)
   - Module: `api_gateway`
   - Issue: Using port 8080 instead of company standard 8081 (AD-204)
   - RAG Query: "What is the internal API port standard?"

## Setup Instructions

### 1. Prerequisites

- MongoDB Atlas account (Free M0 tier works)
- OpenAI API key for embeddings
- Python 3.8+

### 2. MongoDB Atlas Setup

1. Create a free cluster at [mongodb.com/cloud/atlas](https://mongodb.com/cloud/atlas)
2. Create database user with read/write permissions
3. Whitelist your IP (or 0.0.0.0/0 for development)
4. Get connection string from "Connect" button

### 3. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env`:
```
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=JIAE_Knowledge_Base
MONGODB_COLLECTION_NAME=PastFixes
OPENAI_API_KEY=sk-...your-key...
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run Database Setup

```bash
python rag/setup_vector_rag.py
```

This will:
- ✅ Connect to MongoDB Atlas
- ✅ Create standard indexes
- ✅ Load 15 seed documents
- ✅ Generate OpenAI embeddings (1536-dim vectors)
- ✅ Insert documents with embeddings
- ⚠️  Prompt you to create Vector Search Index (next step)

### 6. Create Vector Search Index in Atlas UI

**This is CRITICAL for semantic search to work!**

1. Go to MongoDB Atlas → Your Cluster
2. Click **"Search"** tab (not "Browse Collections")
3. Click **"Create Search Index"**
4. Choose **"JSON Editor"**
5. Paste the contents of `rag_data/vector_index_definition.json`:

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

6. Name it: **`vector_index`** (exactly this name!)
7. Select database: `JIAE_Knowledge_Base`
8. Select collection: `PastFixes`
9. Click **"Create Search Index"**
10. Wait 2-3 minutes for index to build

### 7. Test RAG Queries

```bash
python rag/query_rag.py
```

This will run 3 semantic search tests matching the 3 scenarios.

## Usage in JIAE Agent

```python
from rag.query_rag import RAGQueryEngine, format_rag_context

# Initialize
rag = RAGQueryEngine()

# Semantic search based on JIRA ticket description
ticket_description = "Authentication failing for users in tenant org-123"
results = rag.semantic_search(
    query=ticket_description,
    limit=3,
    module_filter="user_auth"  # Optional pre-filter
)

# Format for LLM context
context = format_rag_context(results)
print(context)

# Pass context to LLM for code generation
# llm_prompt = f"Fix this bug:\n{ticket_description}\n\n{context}"

rag.close()
```

## File Structure

```
rag/
├── setup_vector_rag.py      # Database initialization with embeddings
├── query_rag.py              # Semantic search query engine
└── README.md                 # This file

rag_data/
├── seed_documents.json       # 15 historical fix documents
└── vector_index_definition.json  # Atlas Vector Search index config

dummy_codebase/              # Codebase with intentional bugs
├── services/
│   ├── auth_service.py      # Bug: Missing org prefix
│   └── activity_service.py  # Bug: Missing DB indexes
└── config/
    └── api_config.py        # Bug: Wrong port (8080 vs 8081)
```

## Dummy Codebase

The `dummy_codebase/` directory contains a simulated production application with 3 intentional bugs that correspond to the RAG scenarios:

1. **`auth_service.py`**: `_security_hash_id()` missing organization prefix parameter
2. **`activity_service.py`**: Slow queries due to missing compound indexes
3. **`api_config.py`**: Hardcoded port 8080 instead of 8081 (violates AD-204)

These bugs will be detected and fixed by the JIAE agent using RAG context.

## How Vector Search Works

1. **Indexing (Setup)**:
   - Load `internal_context` from each document
   - Generate 1536-dim embedding using OpenAI API
   - Store embedding array in `embedding` field
   - Create Atlas Vector Search index on `embedding` field

2. **Querying (Runtime)**:
   - JIRA ticket description comes in
   - Generate query embedding using same OpenAI model
   - MongoDB Atlas performs cosine similarity search
   - Returns top-K most similar historical fixes
   - LLM uses these as context to generate the fix

## Cost Estimation

- **MongoDB Atlas**: Free M0 tier (512MB) - sufficient for demo
- **OpenAI Embeddings**: ~$0.00002 per 1K tokens
  - 15 documents × ~200 tokens each = ~3K tokens = **$0.00006** for setup
  - Per-query: ~100 tokens = **$0.000002** per search
- **Total Demo Cost**: < $0.01

## Troubleshooting

### "No vector index found"
- Ensure you created the Vector Search Index in Atlas UI
- Index name must be exactly `vector_index`
- Wait 2-3 minutes for index to build after creation

### "OpenAI API error"
- Check `OPENAI_API_KEY` in `.env` file
- Ensure API key has credits/valid billing

### "Connection timeout"
- Check `MONGODB_URI` in `.env`
- Verify IP whitelist in Atlas Network Access
- Test connection with `mongosh` command

## Next Steps

After RAG setup:
1. ✅ Test semantic searches with `query_rag.py`
2. 🔨 Integrate with MCP orchestrator
3. 🤖 Connect to JIRA webhook listener
4. 🧪 Create test cases that trigger the 3 bug scenarios
5. 🎨 Build Streamlit approval dashboard
