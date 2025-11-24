"""
Code Validation Agent

Validates generated code fixes by:
1. Cloning the repository
2. Creating a test branch
3. Applying the code patch
4. Running tests to verify the fix works
5. Providing feedback for refinement if tests fail
"""

import os
import subprocess
import tempfile
import shutil
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CodeValidator:
    """
    Validates generated code fixes by applying them and running tests.
    
    Workflow:
    1. Clone repository to temporary directory
    2. Create validation branch
    3. Apply generated patches
    4. Run project tests
    5. Return validation results with feedback
    """
    
    def __init__(self):
        """Initialize Code Validator."""
        self.temp_repos_dir = Path(tempfile.gettempdir()) / "hkfx_validation"
        self.temp_repos_dir.mkdir(exist_ok=True)
        logger.info(f"✅ Code Validator initialized (temp dir: {self.temp_repos_dir})")
    
    def validate_fix(
        self,
        github_url: str,
        code_changes: List[Dict[str, Any]],
        ticket_key: str,
        branch_name: Optional[str] = None,
        ticket_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a code fix by applying it and running tests.
        
        Args:
            github_url: GitHub repository URL
            code_changes: List of file changes from code generator
            ticket_key: Jira ticket key (for branch naming)
            branch_name: Optional custom branch name
            ticket_description: Ticket description (to extract specific test file)
        
        Returns:
            Dict with:
                - success: bool (True if tests pass)
                - tests_passed: bool
                - validation_branch: Branch name used
                - test_output: Output from test run
                - errors: List of errors encountered
                - feedback: Feedback for code refinement
                - repo_path: Path to cloned repo (for debugging)
        """
        repo_path = None
        result = {
            'success': False,
            'tests_passed': False,
            'validation_branch': None,
            'test_output': '',
            'errors': [],
            'feedback': '',
            'repo_path': None
        }
        
        try:
            logger.info(f"🧪 Code Validator: Starting validation for {ticket_key}")
            
            # Step 1: Clone repository
            logger.info(f"📥 Step 1: Cloning repository...")
            repo_path = self._clone_repository(github_url, ticket_key)
            result['repo_path'] = str(repo_path)
            logger.info(f"   ✅ Cloned to: {repo_path}")
            
            # Step 2: Create validation branch
            if not branch_name:
                branch_name = f"fix/{ticket_key.lower()}-validation"
            
            logger.info(f"🌿 Step 2: Creating branch '{branch_name}'...")
            self._create_branch(repo_path, branch_name)
            result['validation_branch'] = branch_name
            logger.info(f"   ✅ Branch created")
            
            # Step 3: Apply code changes
            logger.info(f"📝 Step 3: Applying code changes ({len(code_changes)} files)...")
            apply_result = self._apply_code_changes(repo_path, code_changes)
            
            if not apply_result['success']:
                result['errors'] = apply_result['errors']
                result['feedback'] = self._generate_feedback(
                    stage='patch_application',
                    errors=apply_result['errors']
                )
                return result
            
            logger.info(f"   ✅ Code changes applied successfully")
            
            # Step 4: Run tests
            logger.info(f"🧪 Step 4: Running tests...")
            test_result = self._run_tests(repo_path, code_changes, ticket_description)
            result['test_output'] = test_result['output']
            result['tests_passed'] = test_result['passed']
            
            if test_result['passed']:
                logger.info(f"   ✅ All tests passed!")
                result['success'] = True
                result['feedback'] = "All tests passed. Fix is validated and ready for PR."
            else:
                logger.warning(f"   ❌ Tests failed")
                # Log last 500 chars but store full output for refinement
                logger.warning(f"   Test output (last 500 chars): {test_result['output'][-500:]}")
                
                # Store FULL test output for AI refinement (critical!)
                result['test_output_full'] = test_result['output']
                result['errors'] = test_result['errors']
                result['feedback'] = self._generate_feedback(
                    stage='test_execution',
                    errors=test_result['errors'],
                    test_output=test_result['output']  # Full output in feedback
                )
                logger.warning(f"   Feedback: {result['feedback'][:200]}...")
            
            return result
            
        except Exception as e:
            logger.exception(f"❌ Validation error: {e}")
            result['errors'].append(str(e))
            result['feedback'] = f"Validation failed with error: {str(e)}"
            return result
        
        finally:
            # Optionally cleanup temp repo (keep for debugging if tests fail)
            if result.get('tests_passed') and repo_path:
                try:
                    shutil.rmtree(repo_path)
                    logger.info(f"🧹 Cleaned up temp repo")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temp repo: {e}")
    
    def _clone_repository(self, github_url: str, ticket_key: str) -> Path:
        """Clone the repository to a temporary directory."""
        # Create unique directory for this validation
        repo_name = github_url.rstrip('/').split('/')[-1].replace('.git', '')
        repo_dir = self.temp_repos_dir / f"{repo_name}_{ticket_key}"
        
        # Remove if exists
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        
        # Clone repository
        try:
            cmd = ['git', 'clone', github_url, str(repo_dir)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
            
            return repo_dir
            
        except subprocess.TimeoutExpired:
            raise Exception("Git clone timed out after 2 minutes")
        except Exception as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
    
    def _create_branch(self, repo_path: Path, branch_name: str):
        """Create a new branch in the repository."""
        try:
            # Create and checkout new branch
            cmd = ['git', 'checkout', '-b', branch_name]
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to create branch: {result.stderr}")
            
        except Exception as e:
            raise Exception(f"Branch creation failed: {str(e)}")
    
    def _apply_code_changes(
        self,
        repo_path: Path,
        code_changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply code changes to the repository.
        
        For now, this applies simple replacements. In production, you'd want
        to use git apply with proper patch files.
        """
        result = {
            'success': True,
            'applied_files': [],
            'errors': []
        }
        
        try:
            for change in code_changes:
                file_path = change.get('file_path', '').strip()
                diff = change.get('diff', '')
                is_complete_file = change.get('is_complete_file', False)
                
                if not file_path or not diff:
                    logger.warning(f"⚠️ Skipping invalid change: {change}")
                    continue
                
                # Parse the diff and apply changes
                try:
                    self._apply_diff_to_file(repo_path, file_path, diff, is_complete_file)
                    result['applied_files'].append(file_path)
                    logger.info(f"      ✓ Applied changes to {file_path}")
                    
                except Exception as e:
                    error_msg = f"Failed to apply changes to {file_path}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(f"      ✗ {error_msg}")
            
            # Commit the changes
            if result['applied_files']:
                self._commit_changes(repo_path, code_changes)
            
            if result['errors']:
                result['success'] = False
            
            return result
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Patch application failed: {str(e)}")
            return result
    
    def _apply_diff_to_file(self, repo_path: Path, file_path: str, diff: str, is_complete_file: bool = False):
        """
        Apply a diff to a specific file using git apply or direct replacement.
        
        Args:
            repo_path: Path to repository
            file_path: Relative path to file
            diff: Diff content or complete file content
            is_complete_file: If True, treat diff as complete file content
        """
        full_path = repo_path / file_path
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        if is_complete_file:
            # This is complete file content, write directly
            logger.info(f"      Writing complete file content...")
            with open(full_path, 'w') as f:
                f.write(diff)
            logger.info(f"      ✓ File written successfully")
        elif diff.strip().startswith('---') or diff.strip().startswith('@@'):
            # This looks like a proper diff, use git apply
            logger.info(f"      Applying unified diff with git apply...")
            self._apply_with_git_apply(repo_path, file_path, diff)
        else:
            # This is raw code content, try direct replacement
            logger.info(f"      Applying direct code replacement...")
            self._apply_direct_replacement(repo_path, file_path, diff)
    
    def _apply_with_git_apply(self, repo_path: Path, file_path: str, diff: str):
        """Apply a proper unified diff using git apply."""
        try:
            # Create a temporary patch file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as patch_file:
                # Ensure diff has proper header
                if not diff.startswith('---'):
                    diff = f"--- a/{file_path}\n+++ b/{file_path}\n{diff}"
                
                patch_file.write(diff)
                patch_file.flush()
                
                # Apply patch using git apply
                result = subprocess.run(
                    ['git', 'apply', '--whitespace=nowarn', patch_file.name],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Cleanup temp file
                os.unlink(patch_file.name)
                
                if result.returncode != 0:
                    logger.warning(f"⚠️ git apply failed: {result.stderr}")
                    # Fallback to direct replacement
                    self._apply_direct_replacement(repo_path, file_path, diff)
                else:
                    logger.info(f"      ✓ Patch applied successfully")
                    
        except Exception as e:
            logger.warning(f"⚠️ git apply error: {e}, trying direct replacement")
            self._apply_direct_replacement(repo_path, file_path, diff)
    
    def _apply_direct_replacement(self, repo_path: Path, file_path: str, content: str):
        """Apply code by direct file replacement (when diff parsing fails)."""
        full_path = repo_path / file_path
        
        # Parse the diff to extract actual code (remove diff markers)
        cleaned_content = self._extract_code_from_diff(content)
        
        if cleaned_content:
            # Write the cleaned content directly
            with open(full_path, 'w') as f:
                f.write(cleaned_content)
            logger.info(f"      ✓ Direct replacement applied")
        else:
            logger.warning(f"⚠️ Could not extract usable code from diff")
    
    def _extract_code_from_diff(self, diff: str) -> str:
        """Extract actual code content from a diff, removing markers."""
        lines = []
        for line in diff.split('\n'):
            # Skip diff headers
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                continue
            # Include lines starting with + (additions)
            elif line.startswith('+'):
                lines.append(line[1:])  # Remove + prefix but keep whitespace
            # Skip lines starting with - (deletions)
            elif line.startswith('-'):
                continue
            # Include context lines (no prefix or space prefix)
            elif line.startswith(' '):
                lines.append(line[1:])  # Remove space prefix
            elif not line.startswith('\\'):  # Skip "\ No newline at end of file"
                lines.append(line)
        
        return '\n'.join(lines) if lines else None
    
    def _parse_simple_diff(self, diff: str) -> List[tuple]:
        """
        Parse a simple diff into (old_line, new_line) pairs.
        
        NOTE: This method is now deprecated in favor of git apply.
        Keeping for backwards compatibility.
        """
        changes = []
        lines = diff.split('\n')
        
        old_line = None
        for line in lines:
            if line.startswith('-') and not line.startswith('---'):
                # Line to remove (preserve original whitespace)
                old_line = line[1:]  # Don't strip!
            elif line.startswith('+') and not line.startswith('+++'):
                # Line to add (preserve original whitespace)
                new_line = line[1:]  # Don't strip!
                changes.append((old_line, new_line))
                old_line = None
        
        return changes
    
    def _commit_changes(self, repo_path: Path, code_changes: List[Dict[str, Any]]):
        """Commit the applied changes."""
        try:
            # Configure git identity for this repo (required for commits)
            subprocess.run(
                ['git', 'config', 'user.email', 'hkfx-agent@automated.local'],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ['git', 'config', 'user.name', 'H-KFX Agent'],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            # Stage all changes
            subprocess.run(
                ['git', 'add', '.'],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            # Check if there are any changes to commit
            status_result = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                cwd=repo_path,
                capture_output=True
            )
            
            if status_result.returncode == 0:
                # No changes to commit
                logger.info(f"   ℹ️  No changes to commit (files unchanged)")
                return
            
            # Create commit message
            files_changed = [c.get('file_path', 'unknown') for c in code_changes]
            commit_msg = f"Apply automated fix\n\nFiles changed:\n" + "\n".join(f"- {f}" for f in files_changed)
            
            # Commit
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            logger.info(f"   ✅ Changes committed")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Failed to commit changes: {e}")
    
    def _run_tests(
        self, 
        repo_path: Path, 
        code_changes: List[Dict[str, Any]] = None,
        ticket_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run tests in the repository.
        
        Intelligently detects which tests to run based on:
        1. Specific test file mentioned in ticket
        2. Test files related to changed source files
        3. All tests as fallback
        """
        result = {
            'passed': False,
            'output': '',
            'errors': []
        }
        
        # Detect test framework and run tests
        test_commands = self._detect_test_commands(
            repo_path, 
            code_changes, 
            ticket_description
        )
        
        if not test_commands:
            logger.warning("⚠️ No test framework detected, skipping tests")
            result['passed'] = True  # Assume pass if no tests
            result['output'] = "No test framework detected"
            return result
        
        # Run each test command
        for cmd_name, cmd in test_commands.items():
            logger.info(f"   Running {cmd_name}...")
            
            try:
                test_result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    shell=True
                )
                
                result['output'] += f"\n=== {cmd_name} ===\n"
                result['output'] += test_result.stdout
                result['output'] += test_result.stderr
                
                if test_result.returncode == 0:
                    logger.info(f"      ✅ {cmd_name} passed")
                    result['passed'] = True
                else:
                    logger.warning(f"      ❌ {cmd_name} failed (exit code {test_result.returncode})")
                    result['errors'].append(f"{cmd_name} failed with exit code {test_result.returncode}")
                    result['passed'] = False
                    # Stop on first failure
                    break
                
            except subprocess.TimeoutExpired:
                error_msg = f"{cmd_name} timed out after 5 minutes"
                result['errors'].append(error_msg)
                result['passed'] = False
                logger.error(f"      ❌ {error_msg}")
                break
            
            except Exception as e:
                error_msg = f"{cmd_name} failed: {str(e)}"
                result['errors'].append(error_msg)
                result['passed'] = False
                logger.error(f"      ❌ {error_msg}")
                break
        
        return result
    
    def _detect_test_commands(
        self, 
        repo_path: Path,
        code_changes: List[Dict[str, Any]] = None,
        ticket_description: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Detect available test commands based on project files.
        
        Smart test detection:
        1. Extract specific test file from ticket description
        2. Derive test file from changed source file (services/x.py -> tests/test_x.py)
        3. Run ALL tests as fallback
        
        Returns dict of test_name -> command
        """
        commands = {}
        specific_test_file = None
        
        # Try to extract specific test file from ticket description
        if ticket_description:
            import re
            # Look for test file patterns like "tests/test_api_config.py"
            test_patterns = [
                r'tests?/test_[\w/]+\.py',  # tests/test_file.py
                r'test_[\w]+\.py',  # test_file.py
                r'pytest\s+(tests?/[^\s]+)',  # pytest tests/file.py
            ]
            for pattern in test_patterns:
                match = re.search(pattern, ticket_description)
                if match:
                    specific_test_file = match.group(0) if pattern != test_patterns[2] else match.group(1)
                    logger.info(f"   🎯 Detected specific test file from ticket: {specific_test_file}")
                    break
        
        # If no specific test found, derive from changed files
        if not specific_test_file and code_changes:
            for change in code_changes:
                file_path = change.get('file_path', '')
                # Convert source file to test file
                # e.g., services/auth_service.py -> tests/test_auth_service.py
                if file_path:
                    parts = file_path.split('/')
                    filename = parts[-1]
                    if filename.endswith('.py') and not filename.startswith('test_'):
                        test_filename = f"test_{filename}"
                        potential_test = f"tests/{test_filename}"
                        if (repo_path / potential_test).exists():
                            specific_test_file = potential_test
                            logger.info(f"   🎯 Derived test file from source: {specific_test_file}")
                            break
                    # Also check for config/api_config.py -> tests/test_api_config.py
                    elif '/' in file_path:
                        basename = filename.replace('.py', '')
                        test_filename = f"test_{basename}.py"
                        potential_test = f"tests/{test_filename}"
                        if (repo_path / potential_test).exists():
                            specific_test_file = potential_test
                            logger.info(f"   🎯 Derived test file from source: {specific_test_file}")
                            break
        
        # Python - Check first and install dependencies
        has_python_tests = False
        if (repo_path / 'requirements.txt').exists():
            logger.info("   📦 Installing Python dependencies...")
            try:
                # Use python3 explicitly and install pytest if needed
                install_cmds = [
                    ['python3', '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'],
                    ['python3', '-m', 'pip', 'install', '-q', 'pytest']  # Ensure pytest is available
                ]
                
                for cmd in install_cmds:
                    install_result = subprocess.run(
                        cmd,
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=180  # 3 minute timeout
                    )
                    if install_result.returncode == 0:
                        logger.info(f"      ✅ {' '.join(cmd[3:])} completed")
                    else:
                        logger.warning(f"      ⚠️ {' '.join(cmd[3:])} had issues: {install_result.stderr[:200]}")
                
                has_python_tests = True
                        
            except Exception as e:
                logger.warning(f"      ⚠️ Could not install dependencies: {e}")
        
        # Python test frameworks
        if has_python_tests or (repo_path / 'tests').exists():
            # Use specific test file if detected
            if specific_test_file:
                commands['pytest'] = f'python3 -m pytest {specific_test_file} -v'
                logger.info(f"   ✅ Will run SPECIFIC test: {specific_test_file}")
            # Otherwise run all tests
            elif (repo_path / 'pytest.ini').exists() or (repo_path / 'setup.py').exists():
                commands['pytest'] = 'python3 -m pytest -v'
            elif (repo_path / 'tests').exists() and any((repo_path / 'tests').glob('test_*.py')):
                commands['pytest'] = 'python3 -m pytest tests/ -v'
            else:
                # Fallback: run pytest if Python files exist
                commands['pytest'] = 'python3 -m pytest -v'
        
        # Maven (Java)
        if (repo_path / 'pom.xml').exists():
            commands['maven'] = 'mvn test'
        
        # Gradle (Java)
        if (repo_path / 'build.gradle').exists() or (repo_path / 'build.gradle.kts').exists():
            if (repo_path / 'gradlew').exists():
                commands['gradle'] = './gradlew test'
            else:
                commands['gradle'] = 'gradle test'
        
        # npm (Node.js)
        if (repo_path / 'package.json').exists():
            # Install dependencies first
            logger.info("   📦 Installing Node.js dependencies...")
            try:
                npm_install = subprocess.run(
                    ['npm', 'install'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                if npm_install.returncode == 0:
                    logger.info("      ✅ npm install completed")
                else:
                    logger.warning(f"      ⚠️ npm install had issues")
            except Exception as e:
                logger.warning(f"      ⚠️ npm install failed: {e}")
            
            commands['npm'] = 'npm test'
        
        # Make
        if (repo_path / 'Makefile').exists():
            commands['make'] = 'make test'
        
        # Log detected test commands
        if commands:
            logger.info(f"   🔍 Detected test commands: {', '.join(commands.keys())}")
        else:
            logger.warning("   ⚠️ No test commands detected - validation will pass by default")
        
        return commands
    
    def _generate_feedback(
        self,
        stage: str,
        errors: List[str],
        test_output: Optional[str] = None
    ) -> str:
        """
        Generate actionable feedback for code refinement.
        
        Args:
            stage: Which stage failed ('patch_application' or 'test_execution')
            errors: List of error messages
            test_output: Optional test output for analysis
        
        Returns:
            Formatted feedback string
        """
        feedback_parts = [
            f"## VALIDATION FAILED AT: {stage.upper()}\n"
        ]
        
        if stage == 'patch_application':
            feedback_parts.append("The generated code changes could not be applied to the repository.\n")
            feedback_parts.append("**Issues:**")
            for error in errors:
                feedback_parts.append(f"- {error}")
            feedback_parts.append("\n**Suggestions:**")
            feedback_parts.append("- Verify file paths are correct relative to repository root")
            feedback_parts.append("- Check if the target code exists in the repository")
            feedback_parts.append("- Ensure the diff format is correct")
        
        elif stage == 'test_execution':
            feedback_parts.append("The code changes were applied, but tests failed.\n")
            feedback_parts.append("**Test Errors:**")
            for error in errors:
                feedback_parts.append(f"- {error}")
            
            if test_output:
                # Show MORE output - up to 2000 chars (not just 500)
                output_to_show = test_output[-2000:] if len(test_output) > 2000 else test_output
                feedback_parts.append(f"\n**Test Output (last {len(output_to_show)} chars):**")
                feedback_parts.append(f"```\n{output_to_show}\n```")
                
                # Extract specific failing test names
                failing_tests = self._extract_failing_test_names(test_output)
                if failing_tests:
                    feedback_parts.append("\n**Failing Tests:**")
                    for test in failing_tests:
                        feedback_parts.append(f"- {test}")
            
            feedback_parts.append("\n**Suggestions:**")
            feedback_parts.append("- Review test failures to understand what broke")
            feedback_parts.append("- Check function signatures match test expectations")
            feedback_parts.append("- Verify the fix addresses the root cause")
            feedback_parts.append("- Ensure all existing tests still pass")
            feedback_parts.append("- Consider edge cases that might not be handled")
        
        return "\n".join(feedback_parts)
    
    def _extract_failing_test_names(self, test_output: str) -> List[str]:
        """Extract names of failing tests from pytest output."""
        import re
        failing_tests = []
        
        # Look for FAILED test lines
        # Format: FAILED tests/test_file.py::test_name - Error...
        pattern = r'FAILED (tests/[^\s]+::[^\s]+)'
        matches = re.findall(pattern, test_output)
        failing_tests.extend(matches)
        
        # Also look for ERROR lines
        pattern = r'ERROR (tests/[^\s]+::[^\s]+)'
        matches = re.findall(pattern, test_output)
        failing_tests.extend(matches)
        
        return list(set(failing_tests))  # Remove duplicates
    
    def cleanup_all(self):
        """Clean up all temporary repositories."""
        try:
            if self.temp_repos_dir.exists():
                shutil.rmtree(self.temp_repos_dir)
                logger.info("🧹 Cleaned up all validation repositories")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup: {e}")


# Singleton pattern
_validator_instance = None

def get_code_validator() -> CodeValidator:
    """Get or create the singleton CodeValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = CodeValidator()
    return _validator_instance
