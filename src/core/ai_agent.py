import os
import logging
import json
import re

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def openai_summarize(text: str, max_tokens: int = 256) -> str:
    if OpenAI is None:
        return "(openai not configured)"
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "(OPENAI_API_KEY not set)"
    
    try:
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": text}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("OpenAI call failed")
        return f"(openai error: {e})"


def analyze_ticket(ticket_number: str, title: str, description: str) -> dict:
    """
    Analyze a Jira ticket to understand the problem and determine if it's code-related.
    Uses OpenAI if API key is available, otherwise uses heuristic analysis.
    Returns a dict with:
    - problem_summary: Brief summary of the issue
    - is_code_related: Whether the issue is related to code
    - github_url: Extracted GitHub URL if found in description
    - analysis: Detailed analysis from AI
    """
    
    analysis_prompt = f"""
Analyze this support ticket and provide a structured response:

Ticket: {ticket_number}
Title: {title}
Description: {description}

Please analyze:
1. What is the core problem described in this ticket?
2. Is this problem related to code/software development or infrastructure/deployment?
3. If code-related, what area of code (frontend, backend, database, etc.)?
4. What are the key error messages or symptoms mentioned?
5. What GitHub/repository information is mentioned (if any)?

Provide your response as a concise analysis.
"""
    
    # Try to extract GitHub URL from description
    github_match = re.search(
        r'(https?://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?)',
        description or ""
    )
    github_url = github_match.group(1) if github_match else None
    
    # Try AI analysis first if OpenAI is configured
    ai_analysis = None
    if OpenAI and os.getenv("OPENAI_API_KEY"):
        try:
            ai_analysis = openai_summarize(analysis_prompt, max_tokens=512)
        except Exception as e:
            logger.debug("OpenAI analysis failed, falling back to heuristic: %s", e)
    
    # Fallback: basic heuristic analysis if OpenAI not available or failed
    if not ai_analysis:
        keywords = {
            "code_related": [
                "error", "bug", "crash", "fail", "code", "repo", "github", "docker",
                "build", "deploy", "exception", "traceback", "syntax", "import", "null",
                "undefined", "npm", "pip", "maven", "gradle", "compile", "runtime"
            ],
            "urgency": ["critical", "urgent", "production", "down", "broken", "unable"],
            "infrastructure": ["server", "database", "connection", "timeout", "memory", "cpu"]
        }
        
        full_text = (title + " " + (description or "")).lower()
        
        code_score = sum(1 for kw in keywords["code_related"] if kw in full_text)
        infra_score = sum(1 for kw in keywords["infrastructure"] if kw in full_text)
        urgency_score = sum(1 for kw in keywords["urgency"] if kw in full_text)
        
        is_code = code_score > infra_score
        
        problem_type = "code issue" if is_code else "infrastructure/configuration issue"
        urgency_level = "high" if urgency_score > 0 else "normal"
        
        ai_analysis = f"Analysis: {problem_type} with {urgency_level} urgency. "
        ai_analysis += f"Title: {title}. "
        if description:
            ai_analysis += f"Key details: {description[:150]}..."
    
    result = {
        "ticket_number": ticket_number,
        "title": title,
        "problem_summary": ai_analysis,  # Return full analysis without truncation
        "is_code_related": "code" in ai_analysis.lower() or "bug" in ai_analysis.lower() or "error" in ai_analysis.lower(),
        "github_url": github_url,
        "detailed_analysis": ai_analysis,
    }
    
    return result
