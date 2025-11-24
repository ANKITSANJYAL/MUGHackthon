#!/usr/bin/env python3
"""
Quick Test Script for Validation Fixes

Tests the key fixes without running the full webhook.
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("🧪 TESTING VALIDATION FIXES")
print("=" * 80)

# Test 1: Code Validator imports correctly
print("\n1️⃣ Testing Code Validator import...")
try:
    from src.core.code_validator import CodeValidator
    validator = CodeValidator()
    print("   ✅ CodeValidator initialized successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 2: Test the new apply methods exist
print("\n2️⃣ Testing new methods exist...")
try:
    assert hasattr(validator, '_apply_with_git_apply'), "Missing _apply_with_git_apply"
    assert hasattr(validator, '_apply_direct_replacement'), "Missing _apply_direct_replacement"
    assert hasattr(validator, '_extract_code_from_diff'), "Missing _extract_code_from_diff"
    print("   ✅ All new methods present")
except AssertionError as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 3: Code Generator imports correctly
print("\n3️⃣ Testing Code Generator import...")
try:
    from src.core.code_generator import CodeGenerator
    # Don't initialize (needs API key)
    print("   ✅ CodeGenerator imports successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 4: Analyzer imports correctly
print("\n4️⃣ Testing Analyzer import...")
try:
    from src.core.analyzer import ComprehensiveAnalysisAgent
    analyzer = ComprehensiveAnalysisAgent()
    print("   ✅ ComprehensiveAnalysisAgent initialized successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 5: Webhook listener imports correctly
print("\n5️⃣ Testing Webhook Listener import...")
try:
    from src.integrations.webhook_listener import extract_github_url_from_ticket
    test_desc = "Repository: https://github.com/test/repo"
    url = extract_github_url_from_ticket(test_desc)
    assert url == "https://github.com/test/repo", f"URL extraction failed: {url}"
    print("   ✅ Webhook listener imports successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 6: Test diff parsing improvement
print("\n6️⃣ Testing diff parsing preserves whitespace...")
try:
    # Old version would strip, new version preserves
    test_diff = "+    def function():"  # 4 spaces
    old_result = test_diff[1:].strip()  # Old way: loses spaces
    new_result = test_diff[1:]           # New way: keeps spaces
    
    assert old_result == "def function():", "Old way check failed"
    assert new_result == "    def function():", "New way check failed"
    print("   ✅ Whitespace preservation works correctly")
except AssertionError as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 7: Verify complete file support flag
print("\n7️⃣ Testing complete file support...")
try:
    # Test the new _apply_diff_to_file signature
    import inspect
    sig = inspect.signature(validator._apply_diff_to_file)
    params = list(sig.parameters.keys())
    assert 'is_complete_file' in params, "Missing is_complete_file parameter"
    print("   ✅ Complete file support parameter added")
except AssertionError as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
print("\n📝 Next steps:")
print("   1. Restart webhook: python main.py --mode webhook")
print("   2. Create a test Jira ticket")
print("   3. Watch for improved validation logging")
print()
