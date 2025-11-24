import { ProposalData, NodePosition, Edge } from './types';

export const PROPOSAL: ProposalData = {
  project_name: "Hybrid Knowledge Fixer (H-KFX)",
  category_focus: ["Overall Best Agent", "MongoDB Category", "Tavily AI Category"],
  problem_statement: "Consulting firms suffer from high Mean Time to Resolution (MTTR) for bugs requiring both stale internal knowledge (past fixes) and up-to-date external knowledge (API changes). This agent automates the 90% research and code execution effort, requiring Human-in-the-Loop (HITL) sign-off for deployment.",
  architecture_overview: "A Model Context Protocol (MCP) Orchestrator manages the end-to-end bug fix workflow, integrating Jira, GitHub, a proprietary MongoDB RAG tool, and the Tavily Search MCP tool.",
  technical_stack: {
    orchestration_framework: {
      name: "LastMile AI mcp-agent",
      purpose: "Primary Orchestrator, Reflection Loop Manager, State Handler, and Tool Client."
    },
    llm_model: {
      name: "GPT-4o / Claude 3.5 Sonnet",
      purpose: "Code Generation, Synthesis of Hybrid RAG Context, Reasoning for Reflection."
    },
    internal_knowledge_tool: {
      name: "MongoDB Atlas Vector Search RAG",
      purpose: "Stores proprietary past ticket resolutions (organizational memory) as vector embeddings for semantic search.",
      libraries: ["pymongo", "custom MCP wrapper"]
    },
    external_knowledge_tool: {
      name: "Tavily Search MCP Server",
      purpose: "Provides real-time, AI-optimized web search results for API deprecations and library updates.",
      libraries: ["tavily-python"]
    },
    integration_tools: {
      jira: {
        libraries: ["jira", "Flask"],
        purpose: "Webhook listener for ticket creation and API client for status updates/comments."
      },
      github: {
        libraries: ["PyGithub", "subprocess"],
        purpose: "Clones repo, creates branches, runs tests, and merges code."
      },
      frontend_ui: {
        name: "Streamlit",
        purpose: "Displays Agent Trace Log and serves the Human-in-the-Loop Approval Dashboard."
      }
    }
  },
  workflow_steps: [
    {
      step_id: 1,
      name: "Trigger & Preparation",
      actor: "Client / MCP Orchestrator",
      details: "Client creates Jira ticket. Jira Webhook triggers Flask listener which activates MCP Orchestrator. Orchestrator starts workflow."
    },
    {
      step_id: 2,
      name: "Hybrid Knowledge Retrieval",
      actor: "MCP Orchestrator",
      details: "Parallel queries: MongoDB RAG (Vector Search) for history + Tavily Search for live API docs."
    },
    {
      step_id: 3,
      name: "Code Generation & Loop",
      actor: "Coder/Evaluator Tool",
      details: "LLM generates patch. GitHub tool runs tests. If fail, traceback feeds back to LLM (Reflection)."
    },
    {
      step_id: 4,
      name: "HITL Hand-off",
      actor: "Developer",
      details: "Orchestrator updates Jira to 'IN REVIEW'. Developer reviews diff in Streamlit UI."
    },
    {
      step_id: 5,
      name: "Deployment",
      actor: "Orchestrator",
      details: "Developer approves. Orchestrator merges code, updates Jira to DONE, logs metrics."
    }
  ],
  demonstration_ui_plan: {
    design_tool: "Streamlit (or Gradio)",
    key_panels: [
      { name: "Agent Trace Log", content: "Real-time feed of tool calls and reasoning." },
      { name: "Code Diff & Test Report", content: "Side-by-side patch view." },
      { name: "Approval Zone", content: "Approve button and time saved metrics." }
    ]
  },
  sponsor_alignment_pitch: {
    mongodb_win: "Proprietary Knowledge Base (Competitive Advantage)",
    tavily_win: "Real-time Factual Layer (Reliability)",
    overall_win: "Enterprise reliability & Scalable HITL"
  },
  estimated_cost: {
    mongodb_atlas: "$0 (M0 Free Tier)",
    tavily_api: "$0 (Researcher Plan)",
    llm_api: "<$5",
    total_estimated_poc_cost: "Near Zero USD"
  }
};

// Architecture Diagram Definition
export const NODES: NodePosition[] = [
  { 
    id: 'client', 
    label: 'Dev / Client', 
    x: 10, y: 15, 
    type: 'trigger', 
    icon: '👤', 
    description: 'Initiates request via Jira Ticket',
    tech: { purpose: 'Human User', name: 'User' } 
  },
  { 
    id: 'jira', 
    label: 'Jira / Flask', 
    x: 30, y: 15, 
    type: 'trigger', 
    icon: '🎫', 
    description: 'Webhook listener and Ticket Management',
    tech: PROPOSAL.technical_stack.integration_tools.jira 
  },
  { 
    id: 'orchestrator', 
    label: 'MCP Orchestrator', 
    x: 50, y: 40, 
    type: 'core', 
    icon: '🧠', 
    description: 'Central Brain: Manages tools, state, and reflection.',
    tech: PROPOSAL.technical_stack.orchestration_framework 
  },
  { 
    id: 'mongodb', 
    label: 'MongoDB Atlas', 
    x: 20, y: 50, 
    type: 'knowledge', 
    icon: '🍃', 
    description: 'Vector Search for Historical Fixes',
    tech: PROPOSAL.technical_stack.internal_knowledge_tool 
  },
  { 
    id: 'tavily', 
    label: 'Tavily Search', 
    x: 80, y: 50, 
    type: 'knowledge', 
    icon: '🔍', 
    description: 'Real-time Web Search for API Changes',
    tech: PROPOSAL.technical_stack.external_knowledge_tool 
  },
  { 
    id: 'llm', 
    label: 'LLM (GPT-4o)', 
    x: 50, y: 70, 
    type: 'core', 
    icon: '🤖', 
    description: 'Reasoning Engine & Code Synthesis',
    tech: PROPOSAL.technical_stack.llm_model 
  },
  { 
    id: 'github', 
    label: 'GitHub Tool', 
    x: 30, y: 85, 
    type: 'execution', 
    icon: '🐙', 
    description: 'Repo Management & CI/CD',
    tech: PROPOSAL.technical_stack.integration_tools.github 
  },
  { 
    id: 'ui', 
    label: 'Streamlit UI', 
    x: 70, y: 85, 
    type: 'ui', 
    icon: '🖥️', 
    description: 'HITL Approval Dashboard',
    tech: PROPOSAL.technical_stack.integration_tools.frontend_ui 
  }
];

export const EDGES: Edge[] = [
  { from: 'client', to: 'jira', label: 'Create Ticket', activeInStep: [1] },
  { from: 'jira', to: 'orchestrator', label: 'Webhook', activeInStep: [1] },
  { from: 'orchestrator', to: 'mongodb', label: 'Query RAG', activeInStep: [2] },
  { from: 'orchestrator', to: 'tavily', label: 'Search Web', activeInStep: [2] },
  { from: 'mongodb', to: 'orchestrator', label: 'Vectors', activeInStep: [2] },
  { from: 'tavily', to: 'orchestrator', label: 'Context', activeInStep: [2] },
  { from: 'orchestrator', to: 'llm', label: 'Prompt', activeInStep: [3] },
  { from: 'llm', to: 'orchestrator', label: 'Code/Plan', activeInStep: [3] },
  { from: 'orchestrator', to: 'github', label: 'Test Fix', activeInStep: [3, 5] },
  { from: 'github', to: 'orchestrator', label: 'Result', activeInStep: [3] },
  { from: 'orchestrator', to: 'ui', label: 'Request Approval', activeInStep: [4] },
  { from: 'ui', to: 'orchestrator', label: 'Approved', activeInStep: [5] },
];
