"""
Approval API

REST endpoints for frontend approval interface.
"""

from flask import Blueprint, jsonify, request
from flask_cors import CORS
import logging
import os

logger = logging.getLogger(__name__)

# Create Blueprint
approval_bp = Blueprint('approval', __name__)
CORS(approval_bp)  # Enable CORS for frontend

# Module-level variables (will be injected)
approval_manager = None
github_manager = None
jira_client = None


def init_approval_api(app_manager, gh_manager, jira):
    """Initialize API with managers."""
    global approval_manager, github_manager, jira_client
    approval_manager = app_manager
    github_manager = gh_manager
    jira_client = jira
    logger.info("✅ Approval API initialized")


def _clean_ai_summary(summary: str) -> str:
    """Clean AI summary by removing markdown and emojis."""
    import re
    
    # Remove markdown bold/italic
    summary = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', summary)  # ***text***
    summary = re.sub(r'\*\*(.+?)\*\*', r'\1', summary)      # **text**
    summary = re.sub(r'\*(.+?)\*', r'\1', summary)          # *text*
    summary = re.sub(r'__(.+?)__', r'\1', summary)          # __text__
    summary = re.sub(r'_(.+?)_', r'\1', summary)            # _text_
    
    # Remove markdown headers
    summary = re.sub(r'^#{1,6}\s+', '', summary, flags=re.MULTILINE)
    
    # Remove list markers (bullets and numbers)
    summary = re.sub(r'^\s*[-*•]\s+', '', summary, flags=re.MULTILINE)
    summary = re.sub(r'^\s*\d+\.\s+', '', summary, flags=re.MULTILINE)
    
    # Remove emojis (basic approach - removes most common emojis)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    summary = emoji_pattern.sub('', summary)
    
    # Clean up extra whitespace
    summary = re.sub(r'\n\s*\n', '\n\n', summary)  # Multiple newlines to double
    summary = summary.strip()
    
    return summary


def _format_structured_summary(session: dict) -> str:
    """Format summary into structured sections."""
    import re
    
    # Get raw AI analysis and other data
    ai_analysis = session.get('ai_analysis', {})
    raw_summary = session.get('ai_summary', '')
    
    # Clean the raw summary
    clean_summary = _clean_ai_summary(raw_summary)
    
    # Build structured sections
    sections = []
    
    # 1. PROBLEM
    problem_text = clean_summary[:500] if clean_summary else "No problem description available."
    sections.append(f"PROBLEM:\n{problem_text}")
    
    # 2. RESEARCH RESULTS (RAG)
    rag_results = session.get('rag_results', [])
    if rag_results:
        rag_text = f"Found {len(rag_results)} similar past fixes in knowledge base."
        if len(rag_results) > 0:
            top_result = rag_results[0]
            ticket_key = top_result.get('ticket_key', 'N/A')
            similarity = top_result.get('similarity_score', 0)
            rag_text += f" Most relevant: {ticket_key} (similarity: {similarity:.0%})"
        sections.append(f"RESEARCH RESULTS:\n{rag_text}")
    
    # 3. OLD TICKETS REFERRED TO
    if rag_results:
        tickets_list = []
        for i, result in enumerate(rag_results[:3], 1):  # Top 3
            ticket_key = result.get('ticket_key', 'Unknown')
            summary = result.get('summary', 'No summary')
            tickets_list.append(f"{i}. {ticket_key}: {summary[:80]}...")
        sections.append(f"OLD TICKETS REFERRED TO:\n" + "\n".join(tickets_list))
    
    # 4. TAVILY SEARCH SUMMARY
    tavily_results = session.get('tavily_results', [])
    if tavily_results:
        tavily_text = f"Found {len(tavily_results)} external resources."
        if len(tavily_results) > 0:
            top_tavily = tavily_results[0]
            title = top_tavily.get('title', 'Resource')
            tavily_text += f" Top resource: {title[:60]}..."
        sections.append(f"TAVILY SEARCH SUMMARY:\n{tavily_text}")
    
    # 5. CODE UPDATES DONE
    code_changes = session.get('code_changes', [])
    if code_changes:
        updates_list = []
        for change in code_changes:
            file_path = change.get('file_path', 'Unknown file')
            explanation = change.get('explanation', 'No explanation')
            updates_list.append(f"File: {file_path}\nChange: {explanation[:100]}")
        sections.append(f"CODE UPDATES DONE:\n" + "\n\n".join(updates_list))
    
    # Join all sections
    return "\n\n".join(sections)


def _fetch_old_file_from_github(github_url: str, file_path: str, branch: str = 'main') -> str:
    """Fetch old file content from GitHub using GitHub API."""
    import base64
    import requests
    
    try:
        # Parse GitHub URL to extract owner/repo
        # https://github.com/owner/repo → owner/repo
        url = github_url.replace('https://github.com/', '').replace('.git', '')
        parts = url.split('/')
        
        if len(parts) < 2:
            return '(invalid GitHub URL format)'
        
        owner, repo = parts[0], parts[1]
        
        # GitHub API endpoint for file content
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{file_path}'
        
        # Add authorization if GITHUB_TOKEN is available
        headers = {}
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        # Try both 'main' and 'master' branches (common default branches)
        branches_to_try = [branch, 'master', 'main'] if branch not in ['main', 'master'] else [branch, 'master' if branch == 'main' else 'main']
        
        for try_branch in branches_to_try:
            params = {'ref': try_branch}
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                # Success! Parse and return content
                data = response.json()
                if 'content' in data:
                    content = base64.b64decode(data['content']).decode('utf-8')
                    logger.info(f"✅ Fetched {file_path} from {try_branch} branch")
                    return content
            elif response.status_code == 404:
                # Try next branch
                continue
            else:
                # Other error
                return f'(GitHub API error: {response.status_code})'
        
        # If we get here, file not found in any branch
        return f'(file not found in main/master branch)'
        
    except requests.Timeout:
        return '(timeout fetching old file)'
    except requests.RequestException as e:
        return f'(network error: {str(e)[:50]})'
    except Exception as e:
        return f'(error: {str(e)[:100]})'


def _format_code_changes(code_changes: list, github_url: str = None) -> list:
    """Format code changes to include old_code and new_code fields."""
    formatted_changes = []
    
    for change in code_changes:
        diff_content = change.get('diff', '')
        is_complete = change.get('is_complete_file', False)
        file_path = change.get('file_path', '')
        
        if is_complete:
            # Fetch the old version from GitHub
            old_code = '(old file not available)'
            if github_url:
                logger.info(f"📥 Fetching old version of {file_path} from GitHub...")
                old_code = _fetch_old_file_from_github(github_url, file_path)
            
            formatted_changes.append({
                'file_path': file_path,
                'old_code': old_code,
                'new_code': diff_content,
                'explanation': change.get('explanation', '')
            })
        else:
            # It's a diff - parse to extract old and new
            old_lines = []
            new_lines = []
            
            for line in diff_content.split('\n'):
                line_stripped = line.rstrip()
                if line_stripped.startswith('+++') or line_stripped.startswith('---') or line_stripped.startswith('@@'):
                    continue  # Skip diff metadata
                elif line_stripped.startswith('-'):
                    old_lines.append(line_stripped[1:])  # Remove the '-'
                elif line_stripped.startswith('+'):
                    new_lines.append(line_stripped[1:])  # Remove the '+'
                else:
                    # Context line (unchanged)
                    old_lines.append(line_stripped)
                    new_lines.append(line_stripped)
            
            formatted_changes.append({
                'file_path': file_path,
                'old_code': '\n'.join(old_lines) if old_lines else '(no changes)',
                'new_code': '\n'.join(new_lines) if new_lines else '(no changes)',
                'explanation': change.get('explanation', '')
            })
    
    return formatted_changes


@approval_bp.route('/api/approval/<session_id>', methods=['GET'])
def get_approval_session(session_id: str):
    """
    Get approval session details.
    
    Returns session data including code changes, test results, etc.
    """
    try:
        if not approval_manager:
            return jsonify({
                'success': False,
                'error': 'Approval manager not initialized'
            }), 500
        
        session = approval_manager.get_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found or expired'
            }), 404
        
        # Format structured summary with sections
        structured_summary = _format_structured_summary(session)
        
        # Format code changes (add old_code and new_code fields, fetch old files from GitHub)
        formatted_changes = _format_code_changes(
            session.get('code_changes', []),
            github_url=session.get('github_url')
        )
        
        # Format for frontend consumption
        response = {
            'success': True,
            'session': {
                'session_id': session['session_id'],
                'ticket_key': session['ticket_key'],
                'ticket_title': session['ticket_title'],
                'ticket_description': session['ticket_description'],
                'github_url': session['github_url'],
                'validation_branch': session['validation_branch'],
                'code_changes': formatted_changes,
                'test_results': session['test_results'],
                'ai_summary': structured_summary,
                'confidence': session['confidence'],
                'status': session['status'],
                'created_at': session['created_at'].isoformat(),
                'expires_at': session['expires_at'].isoformat(),
                'pr_url': session.get('pr_url'),
                'pr_number': session.get('pr_number')
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@approval_bp.route('/api/approval/<session_id>/approve', methods=['POST'])
def approve_fix(session_id: str):
    """
    Approve a fix and trigger PR creation + merge.
    
    Request body:
    {
        "approved_by": "developer@example.com"  // optional
    }
    """
    try:
        if not approval_manager or not github_manager:
            return jsonify({
                'success': False,
                'error': 'Managers not initialized'
            }), 500
        
        data = request.get_json() or {}
        approved_by = data.get('approved_by', 'developer')
        
        # Get session
        session = approval_manager.get_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found or expired'
            }), 404
        
        if session['status'] != 'PENDING_APPROVAL':
            return jsonify({
                'success': False,
                'error': f'Session already {session["status"]}'
            }), 400
        
        # Create and merge PR
        logger.info(f"🚀 Creating and merging PR for {session['ticket_key']}...")
        
        pr_result = github_manager.create_and_merge_pr(
            github_url=session['github_url'],
            validation_branch=session['validation_branch'],
            repo_path=session['repo_path'],
            ticket_key=session['ticket_key'],
            ticket_title=session['ticket_title'],
            code_changes=session['code_changes']
        )
        
        if pr_result['success'] and pr_result.get('merged'):
            # Mark as approved with PR info
            approval_manager.approve_session(
                session_id,
                approved_by,
                pr_url=pr_result.get('pr_url'),
                pr_number=pr_result.get('pr_number')
            )
            
            # Update Jira to Done
            try:
                from integrations.jira_client import safe_transition, add_agent_comment
                
                if jira_client:
                    safe_transition(jira_client, session['ticket_key'], 'Done')
                    add_agent_comment(
                        jira=jira_client,
                        issue_key=session['ticket_key'],
                        title="✅ Fix Merged to Main",
                        body=f"PR #{pr_result['pr_number']} merged successfully!\n\n{pr_result['pr_url']}"
                    )
            except Exception as e:
                logger.error(f"Failed to update Jira: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Fix approved and merged!',
                'pr_url': pr_result['pr_url'],
                'pr_number': pr_result['pr_number']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': pr_result.get('error', 'PR creation/merge failed'),
                'pr_url': pr_result.get('pr_url')
            }), 500
        
    except Exception as e:
        logger.exception(f"Error approving fix: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@approval_bp.route('/api/approval/<session_id>/reject', methods=['POST'])
def reject_fix(session_id: str):
    """
    Reject a fix (mark as rejected, don't create PR).
    
    Request body:
    {
        "reason": "Needs more testing"
    }
    """
    try:
        if not approval_manager:
            return jsonify({
                'success': False,
                'error': 'Approval manager not initialized'
            }), 500
        
        data = request.get_json() or {}
        reason = data.get('reason', 'No reason provided')
        rejected_by = data.get('rejected_by', 'developer')
        
        session = approval_manager.get_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Update session status
        approval_manager.reject_session(session_id, reason, rejected_by)
        
        # Comment on Jira
        try:
            from integrations.jira_client import add_agent_comment
            if jira_client:
                add_agent_comment(
                    jira=jira_client,
                    issue_key=session['ticket_key'],
                    title="❌ Fix Rejected by Developer",
                    body=f"Reason: {reason}"
                )
        except Exception as e:
            logger.error(f"Failed to update Jira: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Fix rejected'
        }), 200
        
    except Exception as e:
        logger.exception(f"Error rejecting fix: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@approval_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'approval-api',
        'managers': {
            'approval': approval_manager is not None,
            'github': github_manager is not None,
            'jira': jira_client is not None
        }
    }), 200
