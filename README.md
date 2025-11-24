# H-KFX: Hybrid Knowledge Fixer

> AI-powered autonomous bug-fixing agent that analyzes Jira tickets, generates validated code fixes, and creates pull requests automatically.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-19.x-61dafb.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB Atlas account
- Jira account (Cloud)
- OpenAI API key
- GitHub account
- ngrok account

### Installation

```bash
# Clone the repository
git clone https://github.com/ANKITSANJYAL/MUGHackthon.git
cd MUGHackthon

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# MongoDB Atlas
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=JIAE_Knowledge_Base
MONGODB_COLLECTION_NAME=PastFixes

# OpenAI API
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o
CODE_GENERATION_MODEL=gpt-4o
ANALYSIS_MODEL=gpt-4o-mini

# Tavily AI (for external knowledge search)
TAVILY_API_KEY=tvly-dev-your-key-here

# Jira Configuration
JIRA_BASE=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

# GitHub (for PR creation)
GITHUB_TOKEN=ghp_your-github-token-here

# Server Configuration
PORT=5001
FRONTEND_URL=http://localhost:3000
```

### 2. Get API Keys

| Service | How to Get |
|---------|------------|
| **MongoDB Atlas** | [Create free cluster](https://www.mongodb.com/cloud/atlas/register) → Get connection string |
| **OpenAI** | [Get API key](https://platform.openai.com/api-keys) |
| **Tavily AI** | [Sign up](https://tavily.com/) → Get API key |
| **Jira API Token** | Jira → Settings → [Create API token](https://id.atlassian.com/manage-profile/security/api-tokens) |
| **GitHub Token** | Settings → [Developer settings → Tokens](https://github.com/settings/tokens) → Generate (classic) with \`repo\` scope |

### 3. Setup Jira Webhook

1. **Jira Settings** → System → WebHooks → Create a WebHook
2. **URL:** \`https://your-ngrok-url.ngrok.io/webhook\`
3. **Events:** Issue → Created
4. **JQL Filter:** \`project = YOUR_PROJECT_KEY\`

---

## 🏃 Running the Application

### Terminal 1: Start ngrok

```bash
# Get your ngrok auth token from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_NGROK_TOKEN

# Start ngrok tunnel
ngrok http 5001
```

Copy the **Forwarding URL** (e.g., \`https://abc123.ngrok.io\`) and update your Jira webhook.

### Terminal 2: Start Backend

```bash
python main.py --mode webhook
```

**Expected output:**
```
INFO:integrations.webhook_listener:✅ Approval API registered
INFO:integrations.github_manager:✅ GitHub Manager initialized
INFO:integrations.webhook_listener:✅ Progress tracking API registered
 * Running on http://127.0.0.1:5001
```

### Terminal 3: Start Frontend

```bash
cd frontend
npm run dev
```

**Expected output:**
```
  VITE v6.4.1  ready in 500 ms

  ➜  Local:   http://localhost:3000/
```

---

## 📝 Usage

### Create a Jira Ticket

Create a ticket in your Jira project with:

```
Summary: API Gateway Port Configuration Error

Description:
The InternalAPIConfig class is using port 8080, but per AD-204, 
all internal services must use port 8081.

Repository: https://github.com/your-org/your-repo
Branch: main
File: config/api_config.py
```

### What Happens Next

1. **Webhook triggers** → Backend receives ticket
2. **AI Analysis** → Analyzes problem (GPT-4o)
3. **RAG Search** → Finds similar past fixes
4. **Tavily Search** → Gets external best practices
5. **Code Generation** → Creates fix with context
6. **Validation** → Runs tests in isolated environment
7. **Jira Update** → Posts approval link
8. **Review & Approve** → Click link → Review → Approve
9. **PR Creation** → Automatically creates and merges PR
10. **Ticket Closure** → Jira status → Done

**Total Time:** ~60-90 seconds from ticket to validated fix

---

## 🎯 Features

- ✅ **Real-time Progress Tracking** - See orchestrator pipeline progress live
- ✅ **RAG-Powered Context** - Learns from past fixes
- ✅ **External Knowledge** - Integrates Tavily AI for best practices
- ✅ **Test-Driven Validation** - Runs actual tests before approval
- ✅ **Smart Test Selection** - Derives and runs only relevant tests
- ✅ **Refinement Loop** - Self-corrects if validation fails (max 3 attempts)
- ✅ **Approval Workflow** - Review code changes before merge
- ✅ **Auto PR Creation** - Creates and merges GitHub PRs
- ✅ **Jira Integration** - Updates status and posts comments

---

## 🔧 Troubleshooting

### Backend Won't Start

```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt

# Check .env file
grep "MONGODB_URI" .env
```

### Frontend Won't Start

```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Webhook Not Triggering

1. Check ngrok is running: \`http://localhost:4040\` (ngrok dashboard)
2. Verify Jira webhook URL matches ngrok URL
3. Check backend logs: \`tail -f webhook_debug.log\`

### Merge Fails

```bash
# Test GitHub token
python test_github_token.py

# Check token has 'repo' scope
# Regenerate if needed: https://github.com/settings/tokens
```

---

## 📊 API Endpoints

### Backend (Port 5001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| \`/webhook\` | POST | Jira webhook receiver |
| \`/api/progress/stream\` | GET | SSE progress stream |
| \`/api/progress/status/<ticket_key>\` | GET | Get ticket status |
| \`/api/approval/<session_id>\` | GET | Get approval session |
| \`/api/approval/<session_id>/approve\` | POST | Approve and merge |
| \`/api/approval/<session_id>/reject\` | POST | Reject fix |

### Frontend (Port 3000)

| Route | Description |
|-------|-------------|
| \`/\` | Pipeline visualization |
| \`/approve/:sessionId\` | Code review & approval |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

Built with ❤️ for MUG Hackathon 2024

---

## 🙏 Acknowledgments

- OpenAI GPT-4o for code generation
- Tavily AI for external knowledge search
- MongoDB Atlas for vector storage
- Jira for project management integration
- GitHub for version control automation

---

<div align="center">
  <strong>⭐ Star this repo if you find it useful! ⭐</strong>
</div>
