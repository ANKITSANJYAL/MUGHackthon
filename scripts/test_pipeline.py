#!/usr/bin/env python3
"""
Test Pipeline for H-KFX Orchestrated Workflow

This script tests the complete pipeline:
1. AI Ticket Analysis
2. RAG Internal Knowledge Search
3. Tavily External Knowledge Search (mock for now)
4. Jira Integration (optional)

Usage:
    python scripts/test_pipeline.py
    python scripts/test_pipeline.py --skip-jira  # Skip Jira updates
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.orchestrator import get_orchestrator
from dotenv import load_dotenv

load_dotenv()


# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Auth Service NullPointerException",
        "ticket_key": "TEST-001",
        "title": "NullPointerException in user authentication",
        "description": """
User authentication is failing with NullPointerException.

Error:
```
TypeError: 'NoneType' object is not subscriptable
File "auth_service.py", line 45, in validate_token
    org_id = token_data['organization_id']
```

The issue occurs when users try to login without organization context.
This is affecting production users.

Repository: https://github.com/example/myapp.git
        """.strip()
    },
    {
        "name": "Slow Database Queries",
        "ticket_key": "TEST-002",
        "title": "Performance issue with user activity queries",
        "description": """
User activity dashboard is extremely slow (10+ seconds to load).

Query:
```sql
SELECT * FROM user_activity 
WHERE user_id = ? AND timestamp > ?
ORDER BY timestamp DESC
```

Database logs show full table scans. We need to optimize this query.
        """.strip()
    },
    {
        "name": "API Configuration Error",
        "ticket_key": "TEST-003",
        "title": "Service failing to connect on port 8080",
        "description": """
API Gateway is trying to connect to internal services on port 8080,
but our standard is 8081 according to AD-204 policy.

Error in logs:
```
ConnectionRefusedError: [Errno 111] Connection refused
Failed to connect to http://internal-api:8080
```

Need to update api_config.py with correct port.
        """.strip()
    }
]


def print_separator(title=""):
    """Print a nice separator."""
    print(f"\n{'='*80}")
    if title:
        print(f"  {title}")
        print(f"{'='*80}")
    print()


def test_pipeline(scenario: dict, update_jira: bool = False):
    """Test the pipeline with a scenario."""
    print_separator(f"TEST SCENARIO: {scenario['name']}")
    
    print(f"📋 Ticket: {scenario['ticket_key']}")
    print(f"   Title: {scenario['title']}")
    print(f"   Description: {scenario['description'][:100]}...")
    
    # Get orchestrator
    orchestrator = get_orchestrator()
    
    # Run the workflow
    print("\n🚀 Starting orchestrated workflow...")
    result = orchestrator.process_ticket(
        ticket_key=scenario['ticket_key'],
        ticket_title=scenario['title'],
        ticket_description=scenario['description'],
        update_jira=update_jira
    )
    
    # Display results
    print_separator("RESULTS")
    
    print(f"Status: {result['status']}")
    print()
    
    # Phase 1: AI Analysis
    phase_1 = result.get('phase_1_analysis', {})
    print("📋 PHASE 1: AI Analysis")
    print(f"   • Problem: {phase_1.get('problem_summary', 'N/A')[:100]}")
    print(f"   • Code Related: {phase_1.get('is_code_related', False)}")
    print(f"   • GitHub URL: {phase_1.get('github_url', 'None')}")
    print()
    
    # Phase 2: RAG Results
    phase_2 = result.get('phase_2_rag', {})
    print(f"🔍 PHASE 2: RAG Internal Knowledge")
    print(f"   • Success: {phase_2.get('success', False)}")
    print(f"   • Results Found: {phase_2.get('count', 0)}")
    
    if phase_2.get('results'):
        print(f"   • Top Result:")
        top = phase_2['results'][0]
        print(f"     - ID: {top.get('source_id')}")
        print(f"     - Summary: {top.get('summary', '')[:80]}")
        print(f"     - Module: {top.get('module')}")
        print(f"     - Score: {top.get('relevance_score', 0):.3f}")
    print()
    
    # Phase 3: Tavily Results
    phase_3 = result.get('phase_3_tavily', {})
    print(f"🌐 PHASE 3: Tavily External Knowledge")
    print(f"   • Success: {phase_3.get('success', False)}")
    print(f"   • Results Found: {phase_3.get('count', 0)}")
    print(f"   • Mock Mode: {phase_3.get('mock', False)}")
    
    if phase_3.get('results'):
        print(f"   • Top Result:")
        top = phase_3['results'][0]
        print(f"     - Title: {top.get('title', '')[:80]}")
        print(f"     - URL: {top.get('url')}")
        print(f"     - Score: {top.get('score', 0):.3f}")
    print()
    
    # Phase 4: Jira Update
    phase_4 = result.get('phase_4_jira_update', {})
    print(f"📤 PHASE 4: Jira Update")
    print(f"   • Success: {phase_4.get('success', False)}")
    print(f"   • Message: {phase_4.get('message', 'N/A')}")
    print()
    
    # Show hybrid context for LLM
    if result['status'] == 'KNOWLEDGE_RETRIEVAL_COMPLETE':
        print_separator("HYBRID CONTEXT FOR LLM")
        hybrid_context = orchestrator.get_hybrid_context_for_llm(result)
        print(hybrid_context[:800])
        print("\n[... context truncated for display ...]")
    
    return result


def test_rag_only():
    """Quick test of RAG tool only."""
    print_separator("RAG TOOL STANDALONE TEST")
    
    from rag_system.rag_tool import get_rag_tool
    
    rag = get_rag_tool()
    
    test_queries = [
        "user authentication organization context missing",
        "database query slow missing index",
        "api port configuration standard"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        result = rag.search_internal_knowledge(query, limit=3)
        
        if result['success']:
            print(f"   ✅ Found {result['count']} result(s)")
            if result['results']:
                top = result['results'][0]
                print(f"   • Top: {top['source_id']} - {top['summary'][:60]}")
        else:
            print(f"   ❌ Failed: {result.get('error')}")


def main():
    parser = argparse.ArgumentParser(description='Test H-KFX pipeline')
    parser.add_argument('--skip-jira', action='store_true', help='Skip Jira updates')
    parser.add_argument('--rag-only', action='store_true', help='Test RAG tool only')
    parser.add_argument('--scenario', type=int, help='Run specific scenario (1-3)')
    args = parser.parse_args()
    
    print_separator("H-KFX PIPELINE TEST")
    print("Testing the orchestrated workflow:")
    print("  ✓ AI Ticket Analysis")
    print("  ✓ RAG Internal Knowledge Search")
    print("  ✓ Tavily External Knowledge Search (mock)")
    if not args.skip_jira:
        print("  ✓ Jira Integration")
    else:
        print("  ⏭️ Jira Integration (skipped)")
    
    # Check environment
    print("\n📋 Environment Check:")
    print(f"   • MONGODB_URI: {'✅ Set' if os.getenv('MONGODB_URI') else '❌ Not set'}")
    print(f"   • OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print(f"   • JIRA_BASE: {'✅ Set' if os.getenv('JIRA_BASE') else '❌ Not set'}")
    print(f"   • TAVILY_API_KEY: {'✅ Set' if os.getenv('TAVILY_API_KEY') else '⚠️ Not set (using mock)'}")
    
    if args.rag_only:
        test_rag_only()
        return
    
    # Run scenarios
    update_jira = not args.skip_jira
    
    if args.scenario:
        # Run specific scenario
        scenario_index = args.scenario - 1
        if 0 <= scenario_index < len(TEST_SCENARIOS):
            test_pipeline(TEST_SCENARIOS[scenario_index], update_jira)
        else:
            print(f"❌ Invalid scenario number. Choose 1-{len(TEST_SCENARIOS)}")
    else:
        # Run all scenarios
        results = []
        for idx, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"\n\n{'#'*80}")
            print(f"# SCENARIO {idx}/{len(TEST_SCENARIOS)}")
            print(f"{'#'*80}")
            
            result = test_pipeline(scenario, update_jira)
            results.append({
                'scenario': scenario['name'],
                'status': result['status'],
                'rag_count': result.get('phase_2_rag', {}).get('count', 0),
                'tavily_count': result.get('phase_3_tavily', {}).get('count', 0)
            })
            
            # Pause between scenarios
            if idx < len(TEST_SCENARIOS):
                input("\n⏸️  Press Enter to continue to next scenario...")
        
        # Summary
        print_separator("TEST SUMMARY")
        for idx, res in enumerate(results, 1):
            print(f"{idx}. {res['scenario']}")
            print(f"   Status: {res['status']}")
            print(f"   RAG: {res['rag_count']} | Tavily: {res['tavily_count']}")
            print()
    
    print_separator("TEST COMPLETE")
    print("✅ Pipeline test finished!")
    print("\nNext steps:")
    print("  1. Review the results above")
    print("  2. Check Jira for updated tickets (if enabled)")
    print("  3. Verify MongoDB RAG queries worked")
    print("  4. Add Tavily API key for real external search")


if __name__ == '__main__':
    main()
