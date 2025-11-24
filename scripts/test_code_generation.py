"""
Test script for Code Generator

Demonstrates the complete workflow including code generation.
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.orchestrator import get_orchestrator
from dotenv import load_dotenv

load_dotenv()


def test_code_generation():
    """Test the complete workflow with code generation."""
    
    print("=" * 80)
    print("  H-KFX CODE GENERATION TEST")
    print("=" * 80)
    print()
    
    # Test ticket with a real-world scenario
    test_ticket = {
        'key': 'TEST-101',
        'title': 'NullPointerException in UserService.authenticate()',
        'description': '''
User authentication is failing with NullPointerException.

**Error Stack Trace:**
```
java.lang.NullPointerException: Cannot invoke "String.hashCode()" because "orgId" is null
    at com.example.auth.UserService.authenticate(UserService.java:45)
    at com.example.api.AuthController.login(AuthController.java:23)
```

**Steps to Reproduce:**
1. User tries to login from mobile app
2. Request includes valid token but no X-Org-ID header
3. Server returns 500 error

**Expected Behavior:**
Should authenticate successfully or return proper error message.

**Actual Behavior:**
NullPointerException crashes the authentication service.
        ''',
        'github_url': 'https://github.com/example/auth-service'
    }
    
    print(f"📋 Test Ticket: {test_ticket['key']}")
    print(f"   Title: {test_ticket['title']}")
    print()
    
    print("🚀 Starting complete workflow with code generation...")
    print()
    
    # Get orchestrator
    orchestrator = get_orchestrator()
    
    # Run complete workflow with code generation
    result = orchestrator.generate_code_fix(
        ticket_key=test_ticket['key'],
        ticket_title=test_ticket['title'],
        ticket_description=test_ticket['description'],
        github_url=test_ticket['github_url'],
        update_jira=False  # Skip Jira for testing
    )
    
    print()
    print("=" * 80)
    print("  WORKFLOW RESULTS")
    print("=" * 80)
    print()
    
    print(f"📊 Status: {result.get('status')}")
    print()
    
    # Phase 1: AI Analysis
    if result.get('phase_1_analysis'):
        print("✅ PHASE 1: AI Analysis")
        analysis = result['phase_1_analysis']
        print(f"   • Code Related: {analysis.get('is_code_related')}")
        print(f"   • Problem: {analysis.get('problem_summary', 'N/A')[:100]}...")
        print()
    
    # Phase 2: RAG Results
    if result.get('phase_2_rag'):
        rag = result['phase_2_rag']
        print(f"✅ PHASE 2: RAG Internal Knowledge")
        print(f"   • Found: {rag.get('count', 0)} similar fixes")
        if rag.get('results'):
            top = rag['results'][0]
            print(f"   • Top Result: {top.get('source_id')} - {top.get('ticket_summary', 'N/A')[:60]}")
        print()
    
    # Phase 3: Tavily Results
    if result.get('phase_3_tavily'):
        tavily = result['phase_3_tavily']
        print(f"✅ PHASE 3: Tavily External Knowledge")
        print(f"   • Found: {tavily.get('count', 0)} external resources")
        if tavily.get('results'):
            top = tavily['results'][0]
            print(f"   • Top Result: {top.get('title', 'N/A')[:60]}")
        print()
    
    # Phase 5: Code Generation (the star of the show!)
    if result.get('phase_5_code_generation'):
        codegen = result['phase_5_code_generation']
        print(f"✅ PHASE 5: Code Generation")
        
        if codegen.get('success'):
            print(f"   • Status: SUCCESS ✅")
            print(f"   • Confidence: {codegen.get('confidence', 0) * 100:.0f}%")
            print(f"   • Files Affected: {len(codegen.get('files_affected', []))}")
            print()
            
            # Display the generated fix
            print("=" * 80)
            print("  GENERATED CODE FIX")
            print("=" * 80)
            print()
            
            from src.core.code_generator import get_code_generator
            generator = get_code_generator()
            formatted_fix = generator.format_for_display(codegen)
            print(formatted_fix)
            
        else:
            print(f"   • Status: FAILED ❌")
            print(f"   • Error: {codegen.get('error', 'Unknown')}")
        print()
    
    print("=" * 80)
    print("  TEST COMPLETE")
    print("=" * 80)
    print()
    
    print("💡 Next Steps:")
    print("   1. Review the generated code fix above")
    print("   2. Validate it matches the similar past fixes from RAG")
    print("   3. Test with real Jira integration")
    print("   4. Build GitHub PR automation to apply the fix")
    print()


if __name__ == "__main__":
    test_code_generation()
