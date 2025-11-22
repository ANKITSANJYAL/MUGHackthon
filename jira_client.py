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
    transitions = list_transitions(jira, issue_key)
    # try match by name
    for t in transitions:
        if t.get("name", "").lower() == target.lower():
            jira.transition_issue(issue_key, t["id"])
            return t
    # try match by status 'to'
    for t in transitions:
        to = t.get("to") or {}
        if to.get("name", "").lower() == target.lower():
            jira.transition_issue(issue_key, t["id"])
            return t
    raise ValueError(f"No transition found for target {target} on {issue_key}")


if __name__ == "__main__":
    print("jira_client module - import and call get_jira_client() for a live check")
