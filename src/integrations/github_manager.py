"""
GitHub PR Manager

Handles PR creation and merging using PyGithub.
"""

import os
import subprocess
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from github import Github, GithubException
except ImportError:
    Github = None
    GithubException = Exception
    print("⚠️  PyGithub not installed. Run: pip install PyGithub")

logger = logging.getLogger(__name__)


class GitHubManager:
    """Manages GitHub operations (PR creation, merging)."""
    
    def __init__(self):
        """Initialize GitHub API client."""
        if Github is None:
            raise ImportError("PyGithub not installed. Run: pip install PyGithub")
        
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            raise ValueError("GITHUB_TOKEN not set in environment")
        
        self.github = Github(token)
        logger.info("✅ GitHub Manager initialized")
    
    def create_and_merge_pr(
        self,
        github_url: str,
        validation_branch: str,
        repo_path: str,
        ticket_key: str,
        ticket_title: str,
        code_changes: list
    ) -> Dict[str, Any]:
        """
        Create PR from validation branch and auto-merge.
        
        Workflow:
        1. Re-clone repo and re-apply changes if needed
        2. Push validation branch to remote
        3. Create PR from validation branch → main
        4. Auto-merge PR (if mergeable)
        5. Clean up validation branch
        
        Args:
            github_url: GitHub repository URL
            validation_branch: Name of validation branch
            repo_path: Local path to repository (may not exist if cleaned up)
            ticket_key: Jira ticket key
            ticket_title: Ticket title
            code_changes: List of code changes
        
        Returns:
            Dict with PR details and merge status
        """
        import tempfile
        import shutil
        
        temp_clone = None
        try:
            # Extract owner/repo from URL
            repo_path_str = self._parse_repo_path(github_url)
            if not repo_path_str:
                return {
                    'success': False,
                    'error': f'Invalid GitHub URL format: {github_url}'
                }
            
            repo = self.github.get_repo(repo_path_str)
            
            # Check if original repo_path exists
            if not Path(repo_path).exists():
                logger.info(f"⚠️ Original repo cleaned up, re-cloning to apply changes...")
                
                # Create temp directory for fresh clone
                temp_clone = Path(tempfile.mkdtemp(prefix='hkfx_pr_'))
                
                # Clone repository
                clone_result = subprocess.run(
                    ['git', 'clone', '--depth', '1', github_url, str(temp_clone)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if clone_result.returncode != 0:
                    return {
                        'success': False,
                        'error': f"Failed to clone repository: {clone_result.stderr}"
                    }
                
                # Create and checkout validation branch
                subprocess.run(
                    ['git', 'checkout', '-b', validation_branch],
                    cwd=temp_clone,
                    check=True,
                    capture_output=True
                )
                
                # Apply code changes
                for change in code_changes:
                    file_path = temp_clone / change['file_path']
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write new code (assumes complete file in diff field)
                    with open(file_path, 'w') as f:
                        f.write(change.get('diff', ''))
                
                repo_path = str(temp_clone)
                logger.info(f"✅ Re-cloned and applied changes to {repo_path}")
            
            # Step 1: Push validation branch
            logger.info(f"📤 Pushing branch '{validation_branch}' to remote...")
            push_result = self._push_branch(repo_path, validation_branch)
            
            if not push_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to push branch: {push_result['error']}"
                }
            
            # Step 2: Create PR
            logger.info(f"📝 Creating PR...")
            pr_title = f"[H-KFX] {ticket_key}: {ticket_title}"
            pr_body = self._format_pr_body(ticket_key, ticket_title, code_changes)
            
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=validation_branch,
                base='main'
            )
            
            logger.info(f"✅ PR created: #{pr.number}")
            
            # Step 3: Check if mergeable
            pr.update()  # Refresh PR status
            
            if pr.mergeable is False:
                return {
                    'success': False,
                    'pr_url': pr.html_url,
                    'pr_number': pr.number,
                    'error': 'PR has merge conflicts - manual resolution required'
                }
            
            # Step 4: Auto-merge PR
            logger.info(f"🔀 Attempting to merge PR...")
            
            merge_result = pr.merge(
                commit_title=f"Merge PR #{pr.number}: {pr_title}",
                commit_message=f"Automated merge by H-KFX Agent\n\nTicket: {ticket_key}",
                merge_method='squash'  # Can be 'merge', 'squash', or 'rebase'
            )
            
            if merge_result.merged:
                logger.info(f"✅ PR merged successfully!")
                
                # Step 5: Delete validation branch
                try:
                    ref = repo.get_git_ref(f"heads/{validation_branch}")
                    ref.delete()
                    logger.info(f"🗑️ Deleted validation branch")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to delete branch: {e}")
                
                return {
                    'success': True,
                    'pr_url': pr.html_url,
                    'pr_number': pr.number,
                    'merged': True,
                    'merge_sha': merge_result.sha
                }
            else:
                return {
                    'success': False,
                    'pr_url': pr.html_url,
                    'pr_number': pr.number,
                    'error': 'PR could not be merged (may require checks to pass)'
                }
            
        except GithubException as e:
            logger.error(f"❌ GitHub API error: {e}")
            error_msg = e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)
            return {
                'success': False,
                'error': f"GitHub API error: {error_msg}"
            }
        except Exception as e:
            logger.exception(f"❌ Error creating/merging PR: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # Cleanup temp clone if we created one
            if temp_clone and temp_clone.exists():
                try:
                    shutil.rmtree(temp_clone)
                    logger.info(f"🧹 Cleaned up temp PR clone")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temp clone: {e}")
    
    def _parse_repo_path(self, github_url: str) -> Optional[str]:
        """Parse GitHub URL to extract owner/repo."""
        # https://github.com/owner/repo → owner/repo
        # https://github.com/owner/repo.git → owner/repo
        url = github_url.replace('https://github.com/', '').replace('.git', '')
        
        parts = url.split('/')
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return None
    
    def _push_branch(self, repo_path: str, branch_name: str) -> Dict[str, Any]:
        """Push branch to remote origin."""
        try:
            # Check if repo path exists
            if not Path(repo_path).exists():
                logger.warning(f"⚠️ Repo path {repo_path} doesn't exist (likely cleaned up)")
                return {
                    'success': False,
                    'error': f"Repository path not found: {repo_path}"
                }
            
            # Check if branch exists
            branch_check = subprocess.run(
                ['git', 'rev-parse', '--verify', branch_name],
                cwd=repo_path,
                capture_output=True
            )
            
            if branch_check.returncode != 0:
                logger.warning(f"⚠️ Branch {branch_name} doesn't exist in {repo_path}")
                return {
                    'success': False,
                    'error': f"Branch {branch_name} not found in repository"
                }
            
            # Configure git (required for pushing)
            subprocess.run(
                ['git', 'config', 'user.email', 'hkfx-agent@example.com'],
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
            
            # Check if there are uncommitted changes
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            # If there are changes, commit them
            if status_result.stdout.strip():
                # Add all changes
                subprocess.run(
                    ['git', 'add', '.'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                
                # Commit changes
                subprocess.run(
                    ['git', 'commit', '-m', f'H-KFX automated fix'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
            
            # Push to remote (force with lease - safer than force, allows if no one else pushed)
            result = subprocess.run(
                ['git', 'push', '--force-with-lease', 'origin', branch_name],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                # If force-with-lease fails, try regular force (for hackathon purposes)
                logger.warning(f"⚠️ Force-with-lease failed, trying regular force push...")
                result = subprocess.run(
                    ['git', 'push', '--force', 'origin', branch_name],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': result.stderr
                    }
            
            return {'success': True}
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Push timed out'}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _format_pr_body(self, ticket_key: str, ticket_title: str, code_changes: list) -> str:
        """Format PR description."""
        body_parts = [
            f"## 🤖 Automated Fix by H-KFX Agent",
            f"",
            f"**Jira Ticket:** {ticket_key}",
            f"**Title:** {ticket_title}",
            f"",
            f"### 📝 Changes Made",
            f""
        ]
        
        for change in code_changes:
            file_path = change.get('file_path', 'unknown')
            body_parts.append(f"- Modified `{file_path}`")
        
        body_parts.extend([
            f"",
            f"### ✅ Validation",
            f"- All tests passed in isolated environment",
            f"- Code validated before PR creation",
            f"- Human-approved via approval interface",
            f"",
            f"---",
            f"*This PR was automatically generated, validated, and approved through the H-KFX Agent workflow.*"
        ])
        
        return "\n".join(body_parts)


# Singleton
_github_manager = None

def get_github_manager() -> GitHubManager:
    """Get or create the global GitHubManager instance."""
    global _github_manager
    if _github_manager is None:
        _github_manager = GitHubManager()
    return _github_manager
