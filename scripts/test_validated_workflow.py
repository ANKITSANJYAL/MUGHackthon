"""
Test script for Complete Validated Workflow

Demonstrates:
1. Ticket analysis
2. Knowledge retrieval (RAG + Tavily)
3. Code generation
4. Code validation (clone repo, apply patch, run tests)
5. Feedback loop if validation fails
6. Final validated fix ready for PR
"""

import sys
import os
import argparse

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.orchestrator import get_orchestrator
from dotenv import load_dotenv

load_dotenv()


def test_validated_workflow(github_url: str, skip_validation: bool = False):
    """
    Test the complete validated workflow.
    
    Args:
        github_url: GitHub repository URL to test with
        skip_validation: If True, only generate code without validation
    """
    
    print("=" * 80)
    print("  H-KFX COMPLETE VALIDATED WORKFLOW TEST")
    print("=" * 80)
    print()
    
    # Test ticket
    test_ticket = {
        'key': 'TEST-VALIDATE-001',
        'title': 'Fix NullPointerException in authentication',
        'description': '''
User authentication service crashes with NullPointerException when X-Org-ID header is missing.

**Error:**
```
NullPointerException: Cannot invoke "String.hashCode()" because "orgId" is null
    at UserService.authenticate(UserService.java:45)
```

**Expected:** Should return proper error message when header is missing.
**Actual:** Server crashes with 500 error.

**Impact:** High - Prevents all authentication attempts from mobile app.
        ''',
        'github_url': github_url
    }
    
    print(f"📋 Test Ticket: {test_ticket['key']}")
    print(f"   Title: {test_ticket['title']}")
    print(f"   Repository: {github_url}")
    print()
    
    if skip_validation:
        print("⚠️  VALIDATION SKIPPED - Only generating code")
        print()
    
    # Get orchestrator
    orchestrator = get_orchestrator()
    
    if skip_validation:
        # Run without validation (original workflow)
        print("🚀 Running code generation without validation...")
        print()
        
        result = orchestrator.generate_code_fix(
            ticket_key=test_ticket['key'],
            ticket_title=test_ticket['title'],
            ticket_description=test_ticket['description'],
            github_url=test_ticket['github_url'],
            update_jira=False
        )
    else:
        # Run FULL validated workflow
        print("🚀 Running COMPLETE VALIDATED workflow...")
        print("   This will:")
        print("   1. Analyze the ticket")
        print("   2. Search for similar fixes (RAG)")
        print("   3. Search external knowledge (Tavily)")
        print("   4. Generate code fix")
        print("   5. Clone repo and apply patch")
        print("   6. Run tests to validate fix")
        print("   7. Refine if tests fail (up to 3 attempts)")
        print()
        
        result = orchestrator.generate_and_validate_fix(
            ticket_key=test_ticket['key'],
            ticket_title=test_ticket['title'],
            ticket_description=test_ticket['description'],
            github_url=test_ticket['github_url'],
            update_jira=False,
            max_refinement_attempts=3
        )
    
    # Display results
    print()
    print("=" * 80)
    print("  WORKFLOW RESULTS")
    print("=" * 80)
    print()
    
    print(f"📊 Status: {result.get('status')}")
    print()
    
    # Phase summaries
    if result.get('phase_1_analysis'):
        print("✅ Phase 1: AI Analysis - Complete")
    
    if result.get('phase_2_rag'):
        rag = result['phase_2_rag']
        print(f"✅ Phase 2: RAG Search - Found {rag.get('count', 0)} similar fixes")
    
    if result.get('phase_3_tavily'):
        tavily = result['phase_3_tavily']
        print(f"✅ Phase 3: Tavily Search - Found {tavily.get('count', 0)} resources")
    
    if result.get('phase_5_code_generation'):
        codegen = result['phase_5_code_generation']
        if codegen.get('success'):
            print(f"✅ Phase 5: Code Generation - {len(codegen.get('files_affected', []))} files affected")
        else:
            print(f"❌ Phase 5: Code Generation - Failed")
    
    if result.get('phase_6_validation'):
        validation = result['phase_6_validation']
        if validation.get('tests_passed'):
            print(f"✅ Phase 6: Validation - Tests PASSED ✨")
            print(f"   • Branch: {validation.get('validation_branch')}")
            print(f"   • Repo: {validation.get('repo_path')}")
        else:
            print(f"❌ Phase 6: Validation - Tests FAILED")
            print(f"   • Errors: {len(validation.get('errors', []))}")
    
    # Validation attempts summary
    if result.get('validation_attempts'):
        print()
        print(f"🔄 Validation Attempts: {len(result['validation_attempts'])}")
        for attempt in result['validation_attempts']:
            attempt_num = attempt['attempt']
            validation = attempt['validation']
            passed = validation.get('tests_passed', False)
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"   Attempt {attempt_num}: {status}")
    
    print()
    
    # Final code fix
    if result.get('final_code_fix'):
        print("=" * 80)
        print("  FINAL VALIDATED CODE FIX")
        print("=" * 80)
        print()
        
        from src.core.code_generator import get_code_generator
        generator = get_code_generator()
        formatted_fix = generator.format_for_display(result['final_code_fix'])
        print(formatted_fix)
    
    elif result.get('phase_5_code_generation') and result['phase_5_code_generation'].get('success'):
        print("=" * 80)
        print("  GENERATED CODE FIX (Not Validated)")
        print("=" * 80)
        print()
        
        from src.core.code_generator import get_code_generator
        generator = get_code_generator()
        formatted_fix = generator.format_for_display(result['phase_5_code_generation'])
        print(formatted_fix)
    
    print()
    print("=" * 80)
    print("  TEST COMPLETE")
    print("=" * 80)
    print()
    
    if result.get('status') == 'VALIDATED_FIX_READY':
        print("✅ SUCCESS! Fix is validated and ready for:")
        print("   • GitHub PR creation")
        print("   • Human approval (HITL)")
        print("   • Automated deployment")
    elif result.get('status') == 'CODE_FIX_GENERATED':
        print("⚠️  Code generated but not validated")
        print("   • Provide GitHub URL to enable validation")
    elif result.get('status') == 'VALIDATION_FAILED_MAX_ATTEMPTS':
        print("❌ Validation failed after multiple attempts")
        print("   • May require human intervention")
        print("   • Review validation errors above")
    else:
        print(f"Status: {result.get('status')}")
    
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test H-KFX validated workflow')
    parser.add_argument(
        '--github-url',
        type=str,
        default='https://github.com/example/auth-service',
        help='GitHub repository URL to clone and test'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation (only generate code)'
    )
    
    args = parser.parse_args()
    
    test_validated_workflow(
        github_url=args.github_url,
        skip_validation=args.skip_validation
    )
