import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    from jira import JIRA
except Exception:
    JIRA = None

# try to load a local .env for convenience during development
try:
    from dotenv import load_dotenv
    import os as os_module
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
except Exception:
    pass


def get_jira_client():
    if JIRA is None:
        raise RuntimeError("python-jira not installed; run: pip install jira")

    jira_base = os.getenv("JIRA_BASE")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not jira_base or not jira_email or not jira_token:
        raise ValueError("Missing Jira environment variables. Set JIRA_BASE, JIRA_EMAIL, JIRA_API_TOKEN.")

    options = {"server": jira_base}
    client = JIRA(options, basic_auth=(jira_email, jira_token))
    logger.info("Connected to Jira %s", jira_base)
    return client


def get_issue(jira, issue_key: str):
    return jira.issue(issue_key)


def add_comment(jira, issue_key: str, body: str, visibility: Optional[Dict] = None):
    return jira.add_comment(issue_key, body, visibility=visibility)


def list_transitions(jira, issue_key: str) -> List[Dict]:
    return jira.transitions(issue_key)


def transition_issue(jira, issue_key: str, target: str):
    transitions = list_transitions(jira, issue_key)
    for t in transitions:
        if t.get("name", "").lower() == target.lower():
            jira.transition_issue(issue_key, t["id"])
            return t
    for t in transitions:
        to = t.get("to") or {}
        if to.get("name", "").lower() == target.lower():
            jira.transition_issue(issue_key, t["id"])
            return t
    raise ValueError(f"No transition found for {target} on {issue_key}")


if __name__ == "__main__":
    print("jira_client helper module")
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    from jira import JIRA
except Exception:
    # allow import-time failure; raise later when used
    JIRA = None


def get_jira_client():
    """Create and return an authenticated JIRA client using env vars.

    Requires JIRA_BASE, JIRA_EMAIL, JIRA_API_TOKEN set in the environment.
    """
    if JIRA is None:
        raise RuntimeError("python-jira library not installed. Run: pip install jira")

    jira_base = os.getenv("JIRA_BASE")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not jira_base or not jira_email or not jira_token:
        raise ValueError("Missing Jira environment variables. Set JIRA_BASE, JIRA_EMAIL, JIRA_API_TOKEN.")

    options = {"server": jira_base}
    client = JIRA(options, basic_auth=(jira_email, jira_token))
    logger.info("Connected to Jira %s as %s", jira_base, jira_email)
    return client


def get_issue(jira, issue_key: str):
    return jira.issue(issue_key)


def add_comment(jira, issue_key: str, body: str, visibility: Optional[Dict] = None):
    return jira.add_comment(issue_key, body, visibility=visibility)


def list_transitions(jira, issue_key: str) -> List[Dict]:
    return jira.transitions(issue_key)


def transition_issue(jira, issue_key: str, target: str):
    """
    Transition a Jira issue to a target status.
    
    Args:
        jira: JIRA client instance
        issue_key: Issue key (e.g., 'PROJ-123')
        target: Target status name (e.g., 'In Progress', 'Done')
    
    Returns:
        Transition dict if successful
    
    Raises:
        ValueError: If no matching transition found
    """
    transitions = list_transitions(jira, issue_key)
    
    # try match by transition name
    for t in transitions:
        if t.get("name", "").lower() == target.lower():
            jira.transition_issue(issue_key, t["id"])
            logger.info(f"✅ Transitioned {issue_key} to {target}")
            return t
    
    # try match by destination status name
    for t in transitions:
        to = t.get("to") or {}
        if to.get("name", "").lower() == target.lower():
            jira.transition_issue(issue_key, t["id"])
            logger.info(f"✅ Transitioned {issue_key} to {target}")
            return t
    
    available = [t.get("name", "?") for t in transitions]
    logger.error(f"❌ No transition to '{target}' found. Available: {available}")
    raise ValueError(f"No transition found for target '{target}' on {issue_key}. Available: {available}")


def safe_transition(jira, issue_key: str, target: str) -> bool:
    """
    Safely attempt to transition an issue (doesn't raise on failure).
    
    Args:
        jira: JIRA client instance
        issue_key: Issue key
        target: Target status name
    
    Returns:
        True if successful, False otherwise
    """
    try:
        transition_issue(jira, issue_key, target)
        return True
    except Exception as e:
        logger.warning(f"⚠️ Could not transition {issue_key} to {target}: {e}")
        return False


def add_agent_comment(jira, issue_key: str, title: str, body: str, is_success: bool = True) -> bool:
    """
    Add a formatted comment from the H-KFX agent to a Jira issue.
    
    Args:
        jira: JIRA client instance
        issue_key: Issue key
        title: Comment title/summary
        body: Main comment body
        is_success: Whether this is a success or failure message
    
    Returns:
        True if successful, False otherwise
    """
    try:
        icon = "✅" if is_success else "❌"
        formatted_comment = f"""
{icon} *H-KFX Agent Update*

*{title}*

{body}

---
_Automated by H-KFX (Hybrid Knowledge Fixer)_
        """.strip()
        
        add_comment(jira, issue_key, formatted_comment)
        logger.info(f"✅ Added comment to {issue_key}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to add comment to {issue_key}: {e}")
        return False


def update_issue_with_analysis(
    jira,
    issue_key: str,
    ai_summary: str,
    rag_results: Optional[List[Dict]] = None,
    tavily_results: Optional[List[Dict]] = None,
    status: str = "In Progress"
) -> bool:
    """
    Complete Jira update: transition + comment with analysis results.
    
    Args:
        jira: JIRA client instance
        issue_key: Issue key
        ai_summary: AI-generated problem summary
        rag_results: Results from RAG internal knowledge search
        tavily_results: Results from Tavily external search
        status: Target status to transition to
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Transition to In Progress
        safe_transition(jira, issue_key, status)
        
        # Build comment body
        body_parts = [f"*Problem Analysis:*\n{ai_summary}\n"]
        
        # Add RAG results
        if rag_results and len(rag_results) > 0:
            body_parts.append("\n*📚 Internal Knowledge (Past Fixes):*")
            for result in rag_results[:3]:  # Top 3
                body_parts.append(
                    f"• {result.get('source_id', 'Unknown')}: {result.get('summary', 'N/A')} "
                    f"(score: {result.get('relevance_score', 0):.2f})"
                )
        else:
            body_parts.append("\n*📚 Internal Knowledge:* No similar past fixes found")
        
        # Add Tavily results
        if tavily_results and len(tavily_results) > 0:
            is_mock = tavily_results[0].get('mock', False) if isinstance(tavily_results[0], dict) else False
            body_parts.append(f"\n*🌐 External Knowledge {'(Mock)' if is_mock else ''}:*")
            for result in tavily_results[:3]:  # Top 3
                if isinstance(result, dict):
                    body_parts.append(
                        f"• [{result.get('title', 'Unknown')}]({result.get('url', '#')}) "
                        f"(score: {result.get('score', 0):.2f})"
                    )
        else:
            body_parts.append("\n*🌐 External Knowledge:* No relevant documentation found")
        
        body_parts.append("\n*Next Steps:*\nAgent is analyzing the codebase and will generate a fix proposal...")
        
        comment_body = "\n".join(body_parts)
        
        # Add comment
        add_agent_comment(
            jira,
            issue_key,
            "Analysis Complete - Knowledge Retrieved",
            comment_body,
            is_success=True
        )
        
        logger.info(f"✅ Successfully updated {issue_key} with analysis")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update {issue_key}: {e}")
        return False


if __name__ == "__main__":
    print("jira_client module - import and call get_jira_client() for a live check")
