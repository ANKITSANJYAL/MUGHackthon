"""
Integration modules for external services.
Includes Jira and webhook listeners.
"""

from .jira_client import get_jira_client, get_issue, add_comment, transition_issue

# Note: webhook_listener.app is not imported here to avoid circular imports
# Import directly when needed: from integrations.webhook_listener import app

__all__ = [
    'get_jira_client',
    'get_issue',
    'add_comment',
    'transition_issue'
]
