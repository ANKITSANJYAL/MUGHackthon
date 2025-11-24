"""
Code Generation Agent

Generates actual code fixes based on ticket analysis and hybrid knowledge context.
Uses GPT-4o to produce code changes with detailed explanations.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import openai

logger = logging.getLogger(__name__)


class CodeGenerator:
    """
    Generates code fixes using LLM based on ticket context and retrieved knowledge.
    
    Takes the hybrid context (RAG + Tavily + AI analysis) and produces:
    - Actual code changes (as diffs or complete files)
    - Explanation of the fix
    - Files affected
    - Testing recommendations
    """
    
    def __init__(self):
        """Initialize Code Generator with OpenAI client."""
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        # Use specialized code generation model (better for coding tasks)
        self.model = os.getenv('CODE_GENERATION_MODEL', os.getenv('OPENAI_MODEL', 'gpt-4o'))
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        logger.info(f"✅ Code Generator initialized with model: {self.model}")
    
    def generate_fix(
        self,
        ticket_data: Dict[str, Any],
        ai_analysis: Dict[str, Any],
        rag_results: Dict[str, Any],
        tavily_results: Dict[str, Any],
        github_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate code fix based on all available context.
        
        Args:
            ticket_data: Original ticket information (key, summary, description)
            ai_analysis: AI's analysis of the problem
            rag_results: Similar past fixes from internal knowledge
            tavily_results: External resources from Tavily
            github_url: Optional GitHub repository URL
        
        Returns:
            Dict with:
                - success: bool
                - code_changes: List of file changes with diffs
                - explanation: Human-readable explanation
                - files_affected: List of file paths
                - testing_notes: How to test the fix
                - confidence: Confidence score (0-1)
                - error: Error message if failed
        """
        try:
            logger.info(f"🔧 Code Generator: Starting fix generation for {ticket_data.get('key', 'Unknown')}")
            
            # Build the comprehensive prompt
            prompt = self._build_generation_prompt(
                ticket_data=ticket_data,
                ai_analysis=ai_analysis,
                rag_results=rag_results,
                tavily_results=tavily_results,
                github_url=github_url
            )
            
            # Call LLM to generate code
            logger.info(f"🤖 Calling {self.model} for code generation...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more deterministic code
                max_tokens=4000
            )
            
            generated_content = response.choices[0].message.content
            logger.info(f"✅ Code generation complete ({len(generated_content)} chars)")
            
            # Parse the generated response
            parsed_fix = self._parse_generated_fix(generated_content)
            
            # Validate the fix for common mistakes
            validation_warnings = self._validate_generated_fix(parsed_fix, ticket_data)
            if validation_warnings:
                logger.warning("⚠️ Generated fix has potential issues:")
                for warning in validation_warnings:
                    logger.warning(f"   • {warning}")
            
            return {
                'success': True,
                'code_changes': parsed_fix['code_changes'],
                'explanation': parsed_fix['explanation'],
                'files_affected': parsed_fix['files_affected'],
                'testing_notes': parsed_fix['testing_notes'],
                'confidence': parsed_fix.get('confidence', 0.8),
                'raw_output': generated_content,
                'model_used': self.model,
                'validation_warnings': validation_warnings
            }
            
        except Exception as e:
            error_msg = f"Code generation failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'code_changes': [],
                'explanation': error_msg,
                'files_affected': [],
                'testing_notes': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the code generator."""
        return """You are an expert software engineer specialized in debugging and fixing code issues.

Your task is to generate precise, production-ready code fixes based on:
1. The original ticket/bug report
2. AI analysis of the problem
3. Similar past fixes from the codebase (RAG results)
4. External resources and documentation (Tavily results)

IMPORTANT INSTRUCTIONS:
- Generate actual, working code - not pseudocode or placeholders
- Follow the patterns shown in similar past fixes
- Include proper error handling and edge cases
- Write clean, idiomatic code matching the existing style
- Provide COMPLETE FILE CONTENT with changes applied (not just diffs)
- For small files (<200 lines), provide the ENTIRE file with all functions
- For large files, provide enough context (20+ lines before/after changes)
- Preserve exact indentation and whitespace
- Explain WHY each change fixes the problem
- Consider backwards compatibility
- Include testing recommendations

🚨 CRITICAL - PRESERVE ALL EXISTING FUNCTIONS AND CLASSES:
- If a file has multiple functions, include ALL of them
- If a file has classes AND standalone functions, include BOTH
- Only modify the specific function(s) or variable(s) that need fixing
- DO NOT remove or omit any existing functions (class methods OR standalone functions)
- If you omit functions, test imports will break with ImportError
- Example: config/api_config.py has InternalAPIConfig class AND call_internal_service() function
  → You MUST include BOTH in your output
- When in doubt, include more rather than less
- Tests may import ANY function from the file, not just the one you're fixing

🚨 CRITICAL - BACKWARD COMPATIBILITY:
- If adding a new parameter, it MUST have a default value
- Tests may call the function WITHOUT the new parameter
- Use default parameter values: func(old_param, new_param="")
- Example: If adding org_id parameter:
  ❌ WRONG: def func(token, org_id):        # Makes org_id required!
  ✅ RIGHT: def func(token, org_id=""):     # Makes org_id optional!
- This ensures both old and new calling patterns work
- Tests that call func(token) will still work
- Tests that call func(token, org_id) will also work

🚨 CRITICAL - CLASS VARIABLE DEPENDENCIES:
- When changing a class variable that's used by OTHER class variables, you MUST update ALL dependent variables
- Python evaluates class variables at class definition time (not at instantiation)
- Example: If changing API_GATEWAY_PORT in a config class:
  ❌ WRONG: Only change API_GATEWAY_PORT value, leave URLs with old port
  ✅ RIGHT: Update API_GATEWAY_PORT AND regenerate all URLs that use it
- String interpolation happens ONCE at class definition time
- If AUTH_SERVICE_URL = f"http://...:{API_GATEWAY_PORT}/auth" is defined BEFORE you change the port, it will have the OLD value
- You MUST preserve ALL class methods (like get_service_url()) that exist in the original
- You MUST preserve ALL class attributes (URL constants, config values) that exist in the original
- Check the test file to see what methods/attributes tests expect to exist

🚨 CRITICAL - PRESERVE ALL CLASS ATTRIBUTES:
- If a class has attributes like AUTH_SERVICE_URL, USER_SERVICE_URL, ACTIVITY_SERVICE_URL, keep ALL of them
- Do NOT remove or rename attributes unless explicitly required by the ticket
- Tests may reference ANY attribute - removing one causes AttributeError
- If the original has 5 service URLs, your fix MUST have all 5 (with updated port values)
- Example from api_config.py:
  ❌ WRONG: Change port to 8081 but only keep AUTH_SERVICE_URL and remove USER_SERVICE_URL
  ✅ RIGHT: Change port to 8081 and update ALL service URLs (AUTH, USER, ACTIVITY)
- If get_service_url() method has a service_map with 'auth', 'users', 'activity' - keep ALL THREE
- Do NOT arbitrarily remove services from service_map unless the ticket explicitly says to
- The ONLY thing you're fixing is the port number (8080 → 8081), NOT the list of services!

🚨 CRITICAL - PRESERVE ALL EXISTING CLASS METHODS:
- If a class has methods like get_service_url(), get_config(), etc., keep them ALL
- Tests may be importing and calling these methods
- Removing a method will cause: AttributeError: type object 'ClassName' has no attribute 'method_name'
- Even if you think a method isn't needed, KEEP IT if it exists in the original
- Only change what's broken, keep everything else intact

OUTPUT FORMAT:
Structure your response as follows:

## EXPLANATION
[Brief explanation of the root cause and the fix strategy]

## FILES AFFECTED
- path/to/file1.py
- path/to/file2.js

## CODE CHANGES

### File: utils/logger.py
[Provide the COMPLETE working file content as plain code without markdown]

**Change Explanation**: Describe what changed and why it fixes the issue.

### File: [path/to/file2]
[... repeat for each file ...]

## TESTING NOTES
[How to test this fix, including specific test commands]

## CONFIDENCE
[High/Medium/Low - based on completeness of information]

CRITICAL INSTRUCTIONS:
1. Provide COMPLETE working code with ALL functions preserved
2. Do NOT remove any existing functions unless explicitly required
3. If modifying a function, show the ENTIRE file with the change applied
4. Preserve ALL imports, ALL other functions, ALL class definitions
5. Only change what's necessary to fix the specific bug
6. The validator will REPLACE the entire file, so include EVERYTHING

Example: If fixing function_a() in a file with function_a() and function_b():
- Show function_a() WITH your fix
- Show function_b() EXACTLY as it was (unchanged)
- Include ALL imports
- Include ALL other code

NOT ACCEPTABLE:
- "... rest of functions unchanged" ❌
- Showing only the changed function ❌  
- Omitting other functions ❌

The test suite imports multiple functions - if you omit them, imports will break!"""
    
    def _build_generation_prompt(
        self,
        ticket_data: Dict[str, Any],
        ai_analysis: Dict[str, Any],
        rag_results: Dict[str, Any],
        tavily_results: Dict[str, Any],
        github_url: Optional[str]
    ) -> str:
        """Build the comprehensive prompt for code generation."""
        
        prompt_parts = [
            "# CODE FIX GENERATION REQUEST\n",
            "## TICKET INFORMATION",
            f"**Ticket ID**: {ticket_data.get('key', 'N/A')}",
            f"**Summary**: {ticket_data.get('summary', 'N/A')}",
            f"**Description**:\n{ticket_data.get('description', 'N/A')}",
        ]
        
        # Add error/stack trace if available
        if 'error_message' in ticket_data:
            prompt_parts.append(f"\n**Error Message**:\n```\n{ticket_data['error_message']}\n```")
        
        # Add test output if available (from previous validation attempts)
        if 'test_output' in ticket_data:
            prompt_parts.append(f"\n**Test Output**:\n```\n{ticket_data['test_output'][-1000:]}\n```")
        
        # Add validation feedback if available
        if 'validation_feedback' in ticket_data:
            prompt_parts.append(f"\n**Previous Validation Feedback**:\n{ticket_data['validation_feedback']}")
        
        # Add GitHub URL if available
        if github_url:
            prompt_parts.append(f"\n**Repository**: {github_url}")
            
            # Try to fetch the actual file content AND tests
            file_path = self._extract_file_path_from_description(ticket_data.get('description', ''))
            if file_path:
                # Fetch the source file
                file_content = self._fetch_file_from_github(github_url, file_path)
                if file_content:
                    prompt_parts.append(f"\n## CURRENT FILE CONTENT: {file_path}")
                    prompt_parts.append("```python")
                    prompt_parts.append(file_content)
                    prompt_parts.append("```")
                    prompt_parts.append("\n**🚨 CRITICAL - COPY THE ENTIRE FILE CONTENT EXACTLY:**")
                    prompt_parts.append("The file content above shows EVERYTHING in the file. Your output must include ALL of it!")
                    prompt_parts.append("")
                    prompt_parts.append("**What you MUST include in your output:**")
                    prompt_parts.append("- ALL imports at the top")
                    prompt_parts.append("- ALL classes with ALL their methods")
                    prompt_parts.append("- ALL standalone functions (functions outside classes)")
                    prompt_parts.append("- ALL comments and docstrings")
                    prompt_parts.append("- Everything else (module-level code, etc.)")
                    prompt_parts.append("")
                    prompt_parts.append("**What to change:**")
                    prompt_parts.append("- ONLY the specific bug mentioned in the ticket")
                    prompt_parts.append("- If bug is port 8080→8081, change ONLY port-related values")
                    prompt_parts.append("- Copy everything else EXACTLY as shown above")
                    prompt_parts.append("")
                    prompt_parts.append("**Example for config/api_config.py:**")
                    prompt_parts.append("- File has: InternalAPIConfig class + call_internal_service() function")
                    prompt_parts.append("- Bug: Port is 8080, should be 8081")
                    prompt_parts.append("- Your output MUST include:")
                    prompt_parts.append("  ✅ Complete InternalAPIConfig class with get_service_url() method")
                    prompt_parts.append("  ✅ Complete call_internal_service() standalone function")
                    prompt_parts.append("  ✅ All imports, docstrings, comments")
                    prompt_parts.append("- If you omit call_internal_service(), tests will fail with ImportError!")
                
                # CRITICAL: Fetch the TEST file to understand expectations
                test_file_path = self._derive_test_file_path(file_path)
                test_content = self._fetch_file_from_github(github_url, test_file_path)
                if test_content:
                    prompt_parts.append(f"\n## TEST FILE CONTENT: {test_file_path}")
                    prompt_parts.append("```python")
                    prompt_parts.append(test_content)
                    prompt_parts.append("```")
                    prompt_parts.append("\n**CRITICAL**: Study these tests to understand what the fix should do!")
                    prompt_parts.append("")
                    prompt_parts.append("**Understanding the Tests:**")
                    prompt_parts.append("1. Some tests may be **testing the bug exists** (e.g., expecting TypeError)")
                    prompt_parts.append("2. Your fix should make the function ACCEPT the missing parameter")
                    prompt_parts.append("3. Tests that expect errors should PASS after your fix (behavior changes)")
                    prompt_parts.append("4. Tests of normal functionality should continue to PASS")
                    prompt_parts.append("")
                    prompt_parts.append("**Key Questions:**")
                    prompt_parts.append("- What parameters do tests try to pass? (These should be supported!)")
                    prompt_parts.append("- What return values do tests expect?")
                    prompt_parts.append("- Are there tests with pytest.raises(TypeError)? (Fix should prevent these errors)")
                    prompt_parts.append("- Do tests call functions with optional parameters? (Use default values!)")
                    prompt_parts.append("")
                    prompt_parts.append("**🚨 CRITICAL - PARAMETER DEFAULTS:**")
                    prompt_parts.append("If tests call a function with org_id or any new parameter:")
                    prompt_parts.append("")
                    prompt_parts.append("❌ WRONG (Makes it required):")
                    prompt_parts.append("```python")
                    prompt_parts.append("def _security_hash_id(user_token: str, org_id: str) -> str:")
                    prompt_parts.append("    # Tests calling with 1 param will FAIL!")
                    prompt_parts.append("```")
                    prompt_parts.append("")
                    prompt_parts.append("✅ RIGHT (Makes it optional):")
                    prompt_parts.append("```python")
                    prompt_parts.append("def _security_hash_id(user_token: str, org_id: str = \"\") -> str:")
                    prompt_parts.append("    # Tests with 1 or 2 params will BOTH work!")
                    prompt_parts.append("```")
                    prompt_parts.append("")
                    prompt_parts.append("The default value (\"\") ensures backward compatibility!")
                    prompt_parts.append("Apply this to ALL functions that need the new parameter.")
        
        # Add AI Analysis
        prompt_parts.append("\n## AI ANALYSIS")
        prompt_parts.append(ai_analysis.get('problem_analysis', 'No analysis available'))
        
        # Add critical reminder about preserving existing code
        prompt_parts.append("\n## ⚠️ CRITICAL REMINDER #1: PRESERVE ALL FUNCTIONS AND METHODS")
        prompt_parts.append("**IMPORTANT**: If you're modifying services/auth_service.py, config/api_config.py, or any file:")
        prompt_parts.append("1. The file likely has MULTIPLE functions/methods")
        prompt_parts.append("2. Tests import MULTIPLE functions/methods from this file")
        prompt_parts.append("3. You MUST include ALL existing functions/methods in your output")
        prompt_parts.append("4. Only modify the SPECIFIC function/variable that has the bug")
        prompt_parts.append("5. Keep all other functions/methods EXACTLY as they are")
        prompt_parts.append("")
        prompt_parts.append("**For Config Classes (like api_config.py):**")
        prompt_parts.append("- If the class has get_service_url() or any other method, KEEP IT")
        prompt_parts.append("- If changing a port/host variable, UPDATE ALL dependent URLs")
        prompt_parts.append("- Example: Changing API_GATEWAY_PORT requires updating AUTH_SERVICE_URL, USER_SERVICE_URL, etc.")
        prompt_parts.append("- These URLs use string interpolation at class definition time")
        prompt_parts.append("")
        prompt_parts.append("If you remove functions/methods, imports will break with ImportError or AttributeError!")
        
        # Add critical reminder about parameter defaults
        prompt_parts.append("\n## ⚠️ CRITICAL REMINDER #2: USE DEFAULT PARAMETER VALUES")
        prompt_parts.append("**MANDATORY**: When adding new parameters (like org_id):")
        prompt_parts.append("")
        prompt_parts.append("Example Problem: Missing org_id parameter")
        prompt_parts.append("")
        prompt_parts.append("❌ WRONG FIX (breaks existing code):")
        prompt_parts.append("```python")
        prompt_parts.append("def _security_hash_id(user_token: str, org_id: str) -> str:")
        prompt_parts.append("    # Problem: org_id is REQUIRED")
        prompt_parts.append("    # Tests calling func(token) will FAIL with TypeError!")
        prompt_parts.append("```")
        prompt_parts.append("")
        prompt_parts.append("✅ CORRECT FIX (backward compatible):")
        prompt_parts.append("```python")
        prompt_parts.append("def _security_hash_id(user_token: str, org_id: str = \"\") -> str:")
        prompt_parts.append("    # Solution: org_id is OPTIONAL with default=\"\"")
        prompt_parts.append("    # Tests calling func(token) WORK")
        prompt_parts.append("    # Tests calling func(token, org_id) ALSO WORK")
        prompt_parts.append("    prefixed = f\"{org_id}:{user_token}\" if org_id else user_token")
        prompt_parts.append("```")
        prompt_parts.append("")
        prompt_parts.append("YOU MUST USE DEFAULT VALUES: param=\"\" or param=None")
        
        # Add RAG results (similar past fixes)
        prompt_parts.append("\n## SIMILAR PAST FIXES (Internal Knowledge)")
        if rag_results.get('success') and rag_results.get('results'):
            for idx, result in enumerate(rag_results['results'][:3], 1):  # Top 3
                prompt_parts.append(f"\n### Past Fix #{idx}: {result.get('source_id', 'Unknown')}")
                prompt_parts.append(f"**Summary**: {result.get('ticket_summary', 'N/A')}")
                prompt_parts.append(f"**Module**: {result.get('project_module', 'N/A')}")
                prompt_parts.append(f"**Fix Type**: {result.get('fix_type', 'N/A')}")
                prompt_parts.append(f"**Context**: {result.get('fix_context', 'N/A')}")
                if 'code_example' in result:
                    prompt_parts.append(f"**Code Example**:\n```\n{result['code_example']}\n```")
        else:
            prompt_parts.append("No similar past fixes found.")
        
        # Add Tavily results (external knowledge)
        prompt_parts.append("\n## EXTERNAL RESOURCES (Web Search)")
        if tavily_results.get('success') and tavily_results.get('results'):
            for idx, result in enumerate(tavily_results['results'][:3], 1):  # Top 3
                prompt_parts.append(f"\n### Resource #{idx}: {result.get('title', 'Unknown')}")
                prompt_parts.append(f"**URL**: {result.get('url', 'N/A')}")
                prompt_parts.append(f"**Content**: {result.get('content', 'N/A')[:500]}...")  # Truncate long content
        else:
            prompt_parts.append("No external resources found.")
        
        # Final instruction
        prompt_parts.append("\n## YOUR TASK")
        prompt_parts.append("Based on ALL the information above, generate a complete, production-ready fix.")
        prompt_parts.append("Follow the patterns from similar past fixes, and incorporate relevant external knowledge.")
        prompt_parts.append("Provide the fix in the specified format with diffs, explanations, and testing notes.")
        
        return "\n".join(prompt_parts)
    
    def _parse_generated_fix(self, generated_content: str) -> Dict[str, Any]:
        """
        Parse the LLM's generated response into structured format.
        
        Extracts:
        - Explanation
        - Code changes (diffs)
        - Files affected
        - Testing notes
        - Confidence level
        """
        result = {
            'explanation': '',
            'code_changes': [],
            'files_affected': [],
            'testing_notes': '',
            'confidence': 0.8
        }
        
        try:
            # Extract explanation
            if "## EXPLANATION" in generated_content:
                explanation_start = generated_content.index("## EXPLANATION") + len("## EXPLANATION")
                explanation_end = generated_content.index("## FILES AFFECTED") if "## FILES AFFECTED" in generated_content else len(generated_content)
                result['explanation'] = generated_content[explanation_start:explanation_end].strip()
            
            # Extract files affected
            if "## FILES AFFECTED" in generated_content:
                files_start = generated_content.index("## FILES AFFECTED") + len("## FILES AFFECTED")
                files_end = generated_content.index("## CODE CHANGES") if "## CODE CHANGES" in generated_content else len(generated_content)
                files_section = generated_content[files_start:files_end].strip()
                # Parse file list (assume bullet points or lines)
                result['files_affected'] = [
                    line.strip().lstrip('-*•').strip() 
                    for line in files_section.split('\n') 
                    if line.strip() and not line.startswith('#')
                ]
            
            # Extract code changes
            if "## CODE CHANGES" in generated_content:
                changes_start = generated_content.index("## CODE CHANGES") + len("## CODE CHANGES")
                changes_end = generated_content.index("## TESTING NOTES") if "## TESTING NOTES" in generated_content else len(generated_content)
                changes_section = generated_content[changes_start:changes_end]
                
                # Parse individual file changes
                file_changes = self._extract_file_changes(changes_section)
                result['code_changes'] = file_changes
                
                # Update files_affected if not already populated
                if not result['files_affected']:
                    result['files_affected'] = [change['file_path'] for change in file_changes]
            
            # Extract testing notes
            if "## TESTING NOTES" in generated_content:
                testing_start = generated_content.index("## TESTING NOTES") + len("## TESTING NOTES")
                testing_end = generated_content.index("## CONFIDENCE") if "## CONFIDENCE" in generated_content else len(generated_content)
                result['testing_notes'] = generated_content[testing_start:testing_end].strip()
            
            # Extract confidence
            if "## CONFIDENCE" in generated_content:
                confidence_start = generated_content.index("## CONFIDENCE") + len("## CONFIDENCE")
                confidence_text = generated_content[confidence_start:].strip().lower()
                if 'high' in confidence_text:
                    result['confidence'] = 0.9
                elif 'medium' in confidence_text:
                    result['confidence'] = 0.7
                elif 'low' in confidence_text:
                    result['confidence'] = 0.5
            
        except Exception as e:
            logger.warning(f"⚠️ Error parsing generated fix: {e}. Returning raw content.")
            result['explanation'] = generated_content
        
        return result
    
    def _extract_file_changes(self, changes_section: str) -> List[Dict[str, Any]]:
        """Extract individual file changes from the code changes section."""
        file_changes = []
        
        # Split by ### File: markers
        file_sections = changes_section.split("### File:")
        
        for section in file_sections[1:]:  # Skip first empty split
            try:
                lines = section.strip().split('\n')
                file_path = lines[0].strip()
                
                # Extract code blocks (could be diff or complete code)
                code_content = []
                in_code_block = False
                code_language = None
                explanation = []
                
                for line in lines[1:]:
                    # Detect code block start
                    if line.strip().startswith('```'):
                        if not in_code_block:
                            # Starting code block
                            in_code_block = True
                            # Extract language (e.g., ```python, ```diff)
                            code_language = line.strip()[3:].strip() or 'unknown'
                            continue
                        else:
                            # Ending code block
                            in_code_block = False
                            continue
                    
                    if in_code_block:
                        code_content.append(line)
                    elif line.strip() and not line.startswith('#') and not line.startswith('**'):
                        explanation.append(line.strip())
                
                # Determine if this is a diff or complete file
                code_str = '\n'.join(code_content)
                is_diff = (code_language == 'diff' or 
                          code_str.startswith('---') or 
                          code_str.startswith('@@') or
                          any(line.startswith(('+', '-', '@@')) for line in code_content[:5]))
                
                file_changes.append({
                    'file_path': file_path,
                    'diff': code_str,  # Could be diff or complete file
                    'is_complete_file': not is_diff,
                    'language': code_language,
                    'explanation': ' '.join(explanation),
                    'change_type': 'modification'
                })
                
                logger.info(f"      Extracted change for {file_path} (complete_file={not is_diff})")
            
            except Exception as e:
                logger.warning(f"⚠️ Could not parse file change section: {e}")
                continue
        
        return file_changes
    
    def _extract_file_path_from_description(self, description: str) -> Optional[str]:
        """Extract file path from ticket description."""
        import re
        # Look for patterns like: services/auth_service.py, config/api_config.py, etc.
        patterns = [
            r'File:\s*([a-zA-Z0-9_/\.]+\.py)',
            r'file:\s*([a-zA-Z0-9_/\.]+\.py)',
            r'in\s+([a-zA-Z0-9_/\.]+\.py)',
            r'([a-zA-Z0-9_/]+/[a-zA-Z0-9_]+\.py)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _derive_test_file_path(self, source_file_path: str) -> str:
        """
        Derive the test file path from source file path.
        
        Examples:
            services/auth_service.py -> tests/test_auth_service.py
            config/api_config.py -> tests/test_api_config.py
            utils/logger.py -> tests/test_logger.py
        """
        from pathlib import Path
        
        file_name = Path(source_file_path).name
        # Convert service_name.py -> test_service_name.py
        test_file_name = f"test_{file_name}"
        
        return f"tests/{test_file_name}"
    
    def _fetch_file_from_github(self, github_url: str, file_path: str) -> Optional[str]:
        """Fetch actual file content from GitHub by cloning."""
        import tempfile
        import subprocess
        import shutil
        from pathlib import Path
        
        temp_dir = None
        try:
            # Create temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix='codegen_fetch_'))
            
            # Clone repository (shallow clone for speed)
            logger.info(f"   📥 Cloning repo to fetch {file_path}...")
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', github_url, str(temp_dir)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"   ⚠️ Git clone failed: {result.stderr[:200]}")
                return None
            
            # Read the file
            file_full_path = temp_dir / file_path
            if not file_full_path.exists():
                logger.warning(f"   ⚠️ File {file_path} not found in repo")
                return None
            
            with open(file_full_path, 'r') as f:
                content = f.read()
            
            logger.info(f"   ✅ Fetched {file_path} from GitHub ({len(content)} chars)")
            return content
            
        except Exception as e:
            logger.warning(f"   ⚠️ Error fetching file from GitHub: {e}")
            return None
        
        finally:
            # Cleanup temp directory
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    def _validate_generated_fix(self, parsed_fix: Dict[str, Any], ticket_data: Dict[str, Any]) -> List[str]:
        """
        Validate generated fix for common mistakes.
        
        Returns list of warnings (empty if no issues).
        """
        warnings = []
        
        import re
        
        for change in parsed_fix.get('code_changes', []):
            code = change.get('diff', '')
            file_path = change.get('file_path', '')
            
            # Check 1: org_id parameter without default value
            pattern = r'def\s+\w+\([^)]*\borg_id\s*:?\s*\w*\s*(?!=)[,)]'
            if re.search(pattern, code):
                warnings.append(
                    f"{file_path}: Function has 'org_id' parameter without default value. "
                    "This may break existing tests. Consider: org_id: str = \"\""
                )
            
            # Check 2: Class attributes being removed (especially service URLs)
            if 'class ' in code and ('SERVICE_URL' in code or 'Config' in file_path):
                # Check if we're removing any URL attributes
                # Original might have USER_SERVICE_URL, ACTIVITY_SERVICE_URL, etc.
                # If the diff doesn't contain them, we might be removing them
                service_attrs = ['AUTH_SERVICE_URL', 'USER_SERVICE_URL', 'ACTIVITY_SERVICE_URL', 
                               'PAYMENT_SERVICE_URL', 'NOTIFICATION_SERVICE_URL']
                
                # Count how many service URLs are in the new code
                found_services = [attr for attr in service_attrs if attr in code]
                
                if found_services and len(found_services) < 3:
                    warnings.append(
                        f"{file_path}: Only {len(found_services)} service URL(s) found. "
                        f"Original file likely has more. Ensure ALL service URLs are preserved with updated port. "
                        f"Found: {', '.join(found_services)}"
                    )
            
            # Check 3: get_service_url method losing service mappings
            if 'def get_service_url' in code and 'service_map' in code:
                # Extract service names from service_map
                service_map_match = re.search(r"service_map\s*=\s*\{([^}]+)\}", code, re.DOTALL)
                if service_map_match:
                    service_keys = re.findall(r"['\"](\w+)['\"]:", service_map_match.group(1))
                    if len(service_keys) < 3:
                        warnings.append(
                            f"{file_path}: get_service_url() service_map only has {len(service_keys)} service(s): {service_keys}. "
                            "Tests may expect 'users', 'auth', 'activity', etc. Ensure ALL services are preserved."
                        )
            
            # Check 4: Removing standalone functions
            function_defs = re.findall(r'^def\s+(\w+)\s*\(', code, re.MULTILINE)
            if 'call_internal_service' in ticket_data.get('description', ''):
                if function_defs and 'call_internal_service' not in function_defs:
                    warnings.append(
                        f"{file_path}: File likely has call_internal_service() function but it's not in the generated code. "
                        "Include ALL functions from the original file."
                    )
            
            # Check 5: General completeness check
            if 'def ' in code:
                # If we have fewer than 2 functions but it's a config file, might be incomplete
                if len(function_defs) < 2 and 'config' in file_path.lower():
                    warnings.append(
                        f"{file_path}: Only {len(function_defs)} function(s) found. "
                        "Config files often have multiple helper functions. Verify all are included."
                    )
        
        return warnings
    
    def format_for_display(self, fix_result: Dict[str, Any]) -> str:
        """Format the generated fix for concise, developer-friendly display."""
        if not fix_result.get('success'):
            return f"❌ Code generation failed: {fix_result.get('error', 'Unknown error')}"
        
        output = []
        
        # Quick summary line
        files = fix_result.get('files_affected', [])
        file_list = ", ".join([f"`{f}`" for f in files[:2]])
        if len(files) > 2:
            file_list += f" (+{len(files)-2} more)"
        
        output.append(f"**🔧 Fix Summary:** Updated {file_list}")
        output.append("")
        
        # Get first 150 chars of explanation (the "why")
        explanation = fix_result.get('explanation', 'Port configuration corrected per AD-204.')
        # Get just the first sentence or up to 150 chars
        short_explanation = explanation.split('\n')[0]
        if len(short_explanation) > 150:
            short_explanation = short_explanation[:150] + "..."
        output.append(f"**Root Cause:** {short_explanation}")
        output.append("")
        
        # Show key changes only (first file)
        changes = fix_result.get('code_changes', [])
        if changes:
            main_change = changes[0]
            output.append(f"**Key Change in `{main_change['file_path']}`:**")
            
            # Extract just the important lines (look for +/- lines)
            diff_lines = main_change.get('diff', '').split('\n')
            important_lines = [line for line in diff_lines if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
            
            if important_lines:
                output.append("```diff")
                # Show max 8 lines of changes
                for line in important_lines[:8]:
                    output.append(line)
                if len(important_lines) > 8:
                    output.append(f"... ({len(important_lines)-8} more lines)")
                output.append("```")
            
            if len(changes) > 1:
                output.append(f"\n_+ {len(changes)-1} more file(s) modified_")
        
        output.append("")
        output.append(f"**Confidence:** {fix_result.get('confidence', 0) * 100:.0f}%")
        
        return "\n".join(output)


# Singleton pattern
_code_generator_instance = None

def get_code_generator() -> CodeGenerator:
    """Get or create the singleton CodeGenerator instance."""
    global _code_generator_instance
    if _code_generator_instance is None:
        _code_generator_instance = CodeGenerator()
    return _code_generator_instance
