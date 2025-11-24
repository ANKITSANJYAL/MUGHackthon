# 🤖 Hybrid Knowledge Fixer (H-KFX)

[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb)](https://www.mongodb.com/cloud/atlas)
[![Tavily AI](https://img.shields.io/badge/Tavily-AI%20Search-4285F4)](https://tavily.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai)](https://openai.com)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python)](https://www.python.org)

> **An AI-powered automated bug-fixing agent that combines proprietary organizational knowledge with real-time web intelligence to generate, validate, and deploy code fixes automatically.**

**🎯 Key Innovation**: We don't just generate fixes - we **validate them by running actual tests** before creating PRs!

Built for the **MUG Hackathon** | Targeting: **Overall Best Agent**, **MongoDB Category**, **Tavily AI Category**

---

## 🎯 Problem Statement

Consulting firms struggle with **high Mean Time to Resolution (MTTR)** for bugs that require:
- 📚 **Stale internal knowledge** (past fixes buried in tickets)
- 🌐 **Up-to-date external knowledge** (API deprecations, library updates)

**H-KFX** automates the 90% research and code execution effort, requiring only **Human-in-the-Loop (HITL)** sign-off for deployment.

---

## 🏗️ Architecture Overview

```
┌─────────────┐
│ Jira Ticket │ ──(webhook)──> Flask Listener
└─────────────┘                      │
                                     ▼
                          ┌───────────────────┐
                          │ MCP Orchestrator  │
                          │  (Agent Brain)    │
                          └───────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────┐
            │ MongoDB RAG  │  │ Tavily Search│  │  GitHub  │
            │ (Historical) │  │ (Real-time)  │  │  (Code)  │
            └──────────────┘  └──────────────┘  └──────────┘
                    │                │                │
                    └────────────────┴────────────────┘
                                     ▼
                          ┌──────────────────┐
                          │  LLM Coder       │
                          │  + Reflection    │
                          └──────────────────┘
                                     │
                                     ▼
                          ┌──────────────────┐
                          │ Streamlit UI     │
                          │ (HITL Approval)  │
                          └──────────────────┘
```

---

## ✨ Key Features

### 🔄 **Hybrid RAG System**
- **MongoDB Atlas Vector Search**: Semantic search over proprietary past ticket resolutions
- **Tavily Search API**: Real-time AI-optimized web search for API changes
- **Context Fusion**: Intelligently combines internal + external knowledge

### 🧠 **Intelligent Code Generation**
- GPT-4o / Claude 3.5 Sonnet for code synthesis
- **Reflection Loop**: Automatic retry with failure analysis (max 3 attempts)
- **F→P & P→P Testing**: Validates fixes and prevents regressions

### 👨‍💻 **Human-in-the-Loop**
- **Agent Trace Log**: Full transparency of every decision
- **Approval Dashboard**: Code diff, test reports, time saved metrics
- **One-click Deployment**: Automatic merge to GitHub on approval

### 🔌 **Enterprise Integrations**
- **Jira**: Webhook triggers + status updates
- **GitHub**: Branch creation, testing, PR merging
- **MCP Orchestration**: Reliable state management

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MongoDB Atlas account (Free M0 tier)
- OpenAI API key
- Jira instance with webhook access
- GitHub repository access

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ANKITSANJYAL/MUGHackthon.git
cd MUGHackthon
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials:
# - MONGODB_URI
# - OPENAI_API_KEY
# - JIRA_BASE, JIRA_EMAIL, JIRA_API_TOKEN
# - GITHUB_TOKEN (optional)
```

4. **Setup RAG Database**
```bash
python src/rag_system/setup_vector_rag.py
```
Follow the prompts to create the Vector Search Index in MongoDB Atlas.

5. **Start the webhook listener**
```bash
python src/integrations/webhook_listener.py
```

6. **Configure Jira Webhook**
- URL: `http://your-server:5000/webhook`
- Event: `Issue Created`
- JQL Filter: `project = YOUR_PROJECT`

---

## 📂 Project Structure

```
MUGHackthon/
├── src/
│   ├── core/                    # Core AI agent components
│   │   ├── ai_agent.py         # OpenAI ticket analysis
│   │   ├── analyzer.py         # Comprehensive code analyzer
│   │   └── planner.py          # Issue planning & git operations
│   │
│   ├── integrations/            # External service integrations
│   │   ├── jira_client.py      # Jira API wrapper
│   │   └── webhook_listener.py # Flask webhook server
│   │
│   └── rag_system/              # MongoDB Vector RAG
│       ├── setup_vector_rag.py # Database initialization
│       ├── query_rag.py        # Semantic search engine
│       └── query_engine.py     # RAG orchestration
│
├── tests/
│   └── data/                    # Test fixtures & historical data
│       └── historical_tickets.json
│
├── dummy_codebase/              # Sample app for testing
│   ├── services/
│   └── config/
│
├── rag_data/                    # RAG seed documents
│   ├── seed_documents.json
│   └── vector_index_definition.json
│
├── scripts/                     # Utility scripts
│   ├── test_connections.py     # Verify integrations
│   └── encode_password.py      # Credential helpers
│
├── docs/                        # Documentation
│   └── TESTING_GUIDE.md
│
├── proposal.json                # Hackathon project proposal
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
└── README.md                    # This file
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MONGODB_URI` | MongoDB Atlas connection string | ✅ |
| `MONGODB_DB_NAME` | Database name (default: `JIAE_Knowledge_Base`) | ✅ |
| `MONGODB_COLLECTION_NAME` | Collection name (default: `PastFixes`) | ✅ |
| `OPENAI_API_KEY` | OpenAI API key for embeddings & LLM | ✅ |
| `OPENAI_MODEL` | Model name (default: `gpt-4o-mini`) | ❌ |
| `JIRA_BASE` | Jira instance URL | ✅ |
| `JIRA_EMAIL` | Jira user email | ✅ |
| `JIRA_API_TOKEN` | Jira API token | ✅ |
| `GITHUB_TOKEN` | GitHub personal access token | ❌ |
| `DEFAULT_REPO_URL` | Default repository for analysis | ❌ |

---

## 🎬 Workflow Demo

### Step 1: Ticket Creation
```
Developer creates Jira ticket:
"API /users endpoint returning 500 errors after upgrading Flask to 3.0"
```

### Step 2: Webhook Trigger
```
✅ Webhook fired → Flask listener activates MCP Orchestrator
✅ Jira status: OPEN → IN PROGRESS
```

### Step 3: Hybrid RAG Retrieval
```
🔍 MongoDB Vector Search:
   → Found: "Fix for Flask 2.x → 3.0 migration (JIRA-4231)"
   → Context: "Replace deprecated Response.set_cookie with new API"

🌐 Tavily Web Search:
   → "Flask 3.0 breaking changes response cookies"
   → "Flask.Response.set_cookie() now requires 'samesite' parameter"
```

### Step 4: Code Generation + Reflection
```
🤖 Coder LLM generates patch based on hybrid context
🧪 Runs F→P test → ❌ FAIL (missing samesite param)
🔄 Reflection: Adds samesite='Lax' → ✅ PASS
🧪 Runs P→P tests → ✅ All green
```

### Step 5: HITL Approval
```
📊 Streamlit UI displays:
   • Agent trace log (MongoDB + Tavily queries)
   • Code diff with syntax highlighting
   • Test report: 12/12 passed
   • Estimated time saved: 3.5 hours

👤 Developer clicks [🟢 APPROVE & MERGE]
```

### Step 6: Deployment
```
✅ Git merge executed
✅ Jira status: IN REVIEW → DONE
✅ Comment added: "Fixed by H-KFX agent | Time saved: 3.5 hours"
```

---

## 🏆 Sponsor Alignment

### MongoDB Win 🍃
- **Proprietary Knowledge Base**: Stores high-value historical fixes that general LLMs lack
- **Vector Search**: Semantic retrieval of past solutions using Atlas Vector Search
- **Audit Trail**: Complete log of agent actions in MongoDB collections

### Tavily Win 🔍
- **Real-time Factual Layer**: Ensures fixes address the absolute latest API changes
- **AI-Optimized Search**: Better than raw Google/StackOverflow scraping
- **Citation Support**: Tracks sources for explainability

### Overall Best Agent 🥇
- **MCP Orchestrator**: Enterprise-grade reliability with state management
- **HITL System**: Production-ready automation with human oversight
- **Hybrid Intelligence**: Demonstrates cutting-edge RAG architecture

---

## 📊 Technical Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | MCP (Model Context Protocol) | State management, tool routing |
| **LLM** | GPT-4o / Claude 3.5 Sonnet | Code generation, reasoning |
| **Internal RAG** | MongoDB Atlas Vector Search | Semantic search over past fixes |
| **External RAG** | Tavily Search API | Real-time web intelligence |
| **Embeddings** | OpenAI text-embedding-3-small | 1536-dim vectors |
| **Issue Tracking** | Jira API + Webhooks | Ticket management |
| **Version Control** | GitHub API + PyGithub | Code operations |
| **Frontend** | Streamlit | Approval dashboard |
| **Backend** | Flask | Webhook listener |

---

## 💰 Cost Efficiency

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| MongoDB Atlas | M0 Free Tier | **$0** |
| Tavily API | Researcher Plan | **$0** (free credits) |
| OpenAI API | Pay-as-you-go | **~$5** (demo run) |
| **Total POC Cost** | | **Near Zero USD** |

---

## 🧪 Testing

See [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) for detailed testing instructions.

### Quick Test
```bash
# Test MongoDB connection
python scripts/test_connections.py

# Test RAG query
python src/rag_system/query_rag.py

# Start webhook listener (test mode)
FLASK_ENV=development python src/integrations/webhook_listener.py
```

---

## 🤝 Contributing

This is a hackathon project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 👥 Team

Built with ❤️ by the **MUG Hackathon Team**

- GitHub: [@ANKITSANJYAL](https://github.com/ANKITSANJYAL)
- Repository: [MUGHackthon](https://github.com/ANKITSANJYAL/MUGHackthon)

---

## 🙏 Acknowledgments

- **MongoDB** for Atlas Vector Search
- **Tavily AI** for intelligent web search
- **OpenAI** for GPT-4 and embeddings
- **LastMile AI** for MCP framework inspiration
- **MUG Community** for hosting the hackathon

---

## 📞 Support

For questions or issues:
- Open a GitHub Issue
- Check [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)
- Review `proposal.json` for architecture details

---

**⚡ Ready to slash your MTTR? Let H-KFX automate your bug fixes!**
