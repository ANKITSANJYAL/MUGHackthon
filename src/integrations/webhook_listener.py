import os
import sys
import logging
import json
import shutil
from flask import Flask, request, jsonify

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.jira_client import get_jira_client, get_issue
from core.analyzer import ComprehensiveAnalysisAgent
from core.ai_agent import analyze_ticket
from core.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)

# Register approval API blueprint
try:
    from integrations.approval_api import approval_bp, init_approval_api
    from core.approval_manager import get_approval_manager
    from integrations.github_manager import get_github_manager
    
    app.register_blueprint(approval_bp)
    logger.info("✅ Approval API registered")
    
    # Initialize managers immediately
    _approval_manager = None
    _github_manager = None
    
    def _init_managers():
        """Initialize approval and github managers."""
        global _approval_manager, _github_manager
        try:
            _approval_manager = get_approval_manager()
            _github_manager = get_github_manager()
            _jira = get_jira_client()
            init_approval_api(_approval_manager, _github_manager, _jira)
            logger.info("✅ Approval and GitHub managers initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize managers: {e}")
    
    # Initialize managers when module is imported
    _init_managers()
    
except ImportError as e:
    logger.warning(f"⚠️ Approval API not available: {e}")
    _init_managers = None

# Register progress tracking API blueprint
try:
    from integrations.progress_tracker import progress_bp, get_progress_tracker
    
    app.register_blueprint(progress_bp)
    logger.info("✅ Progress tracking API registered")
    
except ImportError as e:
    logger.warning(f"⚠️ Progress tracking API not available: {e}")

# Track the last processed ticket
last_ticket = {"key": None, "timestamp": None}

def log_and_print(message: str, level: str = "INFO"):
    """Log message both to logger and stdout with flushing."""
    print(message)
    sys.stdout.flush()
    if level == "INFO":
        logger.info(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "DEBUG":
        logger.debug(message)

def extract_github_url_from_ticket(description: str) -> str:
    """
    Extract GitHub repository URL from ticket description.
    
    Looks for patterns like:
    - Repository: https://github.com/org/repo
    - Repo: https://github.com/org/repo
    - GitHub: https://github.com/org/repo
    - https://github.com/org/repo (standalone URL)
    
    Returns:
        GitHub URL if found, None otherwise
    """
    import re
    
    if not description:
        return None
    
    # Pattern 1: Labeled URLs (Repository:, Repo:, GitHub:, etc.)
    labeled_pattern = r'(?:Repository|Repo|GitHub|Github|Code|Codebase)\s*:\s*(https?://github\.com/[\w\-]+/[\w\-\.]+)'
    match = re.search(labeled_pattern, description, re.IGNORECASE)
    if match:
        return match.group(1).rstrip('/')
    
    # Pattern 2: Standalone GitHub URLs
    url_pattern = r'https?://github\.com/([\w\-]+/[\w\-\.]+)'
    match = re.search(url_pattern, description, re.IGNORECASE)
    if match:
        url = match.group(0).rstrip('/')
        # Remove any trailing paths after the repo name (like /issues, /pulls, etc.)
        # Keep only: https://github.com/org/repo
        clean_url = re.match(r'(https?://github\.com/[\w\-]+/[\w\-\.]+)', url)
        if clean_url:
            return clean_url.group(1)
    
    return None

@app.route("/webhook", methods=["POST"])
def jira_webhook():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "missing json payload"}), 400

    webhook_event = data.get("webhookEvent")
    issue = data.get("issue")

    if webhook_event != "jira:issue_created" or not issue:
        logger.info("Ignored event: %s", webhook_event)
        return jsonify({"status": "ignored"}), 200

    issue_key = issue.get("key")
    if not issue_key:
        return jsonify({"error": "issue key missing"}), 400

    # Only process the most recently created ticket
    # Skip if this ticket was already processed
    if last_ticket["key"] == issue_key:
        log_and_print(f"\n⏭️  SKIPPING {issue_key} (already processed)", "INFO")
        return jsonify({"status": "skipped", "reason": "Already processed"}), 200
    
    # Update the last processed ticket
    import time
    last_ticket["key"] = issue_key
    last_ticket["timestamp"] = time.time()

    log_and_print(f"\n{'='*80}", "INFO")
    log_and_print(f"🎯 WEBHOOK TRIGGERED FOR ISSUE: {issue_key} (PROCESSING - Latest Ticket)", "INFO")
    log_and_print(f"{'='*80}\n", "INFO")

    jira = get_jira_client()

    try:
        # Fetch full issue details
        issue_obj = get_issue(jira, issue_key)
        ticket_number = issue_obj.key
        ticket_title = getattr(issue_obj.fields, "summary", "")
        ticket_description = getattr(issue_obj.fields, "description", "")

        log_and_print(f"📋 TICKET DETAILS RECEIVED:", "INFO")
        log_and_print(f"   • Number:      {ticket_number}", "INFO")
        log_and_print(f"   • Title:       {ticket_title}", "INFO")
        log_and_print(f"   • Description: {ticket_description[:100] if ticket_description else 'None'}", "INFO")
        
        # ===== ORCHESTRATED WORKFLOW =====
        # Use the orchestrator to coordinate AI → RAG → Tavily → Code Gen → Validation
        log_and_print(f"\n🎯 Starting Complete Validated Workflow", "INFO")
        log_and_print(f"{'='*80}\n", "INFO")
        
        orchestrator = get_orchestrator()
        
        # Extract GitHub URL from ticket (priority 1) or use default (priority 2)
        github_url = extract_github_url_from_ticket(ticket_description)
        
        if github_url:
            log_and_print(f"   ✅ GitHub URL found in ticket: {github_url}", "INFO")
        else:
            github_url = os.getenv("DEFAULT_REPO_URL")
            if github_url:
                log_and_print(f"   ⚠️  No GitHub URL in ticket, using default: {github_url}", "INFO")
            else:
                log_and_print(f"   ⚠️  No GitHub URL found (neither in ticket nor .env)", "INFO")
        
        # Phase 0: Full Issue Verification (if GitHub URL available)
        # This now does COMPLETE verification including running diagnostics
        verification_result = None
        if github_url:
            log_and_print(f"\n🔍 PHASE 0: Issue Verification & Analysis", "INFO")
            log_and_print(f"   Repository URL: {github_url}", "INFO")
            log_and_print(f"   Running comprehensive diagnostics...\n", "INFO")
            
            # Run FULL comprehensive analysis with diagnostics
            try:
                analyzer = ComprehensiveAnalysisAgent()
                verification_result = analyzer.analyze_issue(
                    issue_key=ticket_number,
                    issue_description=ticket_description,
                    repo_url=github_url
                )
                
                log_and_print(f"   ✅ Verification Status: {verification_result.get('status')}", "INFO")
                log_and_print(f"   ✅ Project Type: {', '.join(verification_result.get('project_detection', {}).get('detected_types', ['Unknown']))}", "INFO")
                
                diagnostic_results = verification_result.get('diagnostic_results', [])
                if diagnostic_results:
                    passed = sum(1 for d in diagnostic_results if d.get('success'))
                    failed = len(diagnostic_results) - passed
                    log_and_print(f"   ✅ Diagnostics: {passed} passed, {failed} failed", "INFO")
                    
                    # Show failures
                    for d in diagnostic_results:
                        if not d.get('success'):
                            log_and_print(f"      ❌ {d.get('command')}: {d.get('stderr', '')[:100]}", "INFO")
                else:
                    log_and_print(f"   ⚠️  No diagnostics run", "INFO")
                
                log_and_print(f"   Analysis: {verification_result.get('final_analysis', 'N/A')}", "INFO")
                        
            except Exception as e:
                log_and_print(f"   ❌ Verification failed: {str(e)}", "ERROR")
                verification_result = {
                    'status': 'ERROR',
                    'project_detection': {},
                    'diagnostic_results': [],
                    'final_analysis': f'Verification error: {str(e)}'
                }
        
        if github_url:
            # Run FULL validated workflow (includes code generation + validation)
            log_and_print(f"   GitHub URL detected: {github_url}", "INFO")
            log_and_print(f"   Running FULL workflow with validation...\n", "INFO")
            
            orchestration_result = orchestrator.generate_and_validate_fix(
                ticket_key=ticket_number,
                ticket_title=ticket_title,
                ticket_description=ticket_description,
                github_url=github_url,
                update_jira=True,
                max_refinement_attempts=3
            )
        else:
            # Run basic workflow (no validation - no GitHub URL)
            log_and_print(f"   No GitHub URL configured", "INFO")
            log_and_print(f"   Running basic workflow (knowledge retrieval only)...\n", "INFO")
            
            orchestration_result = orchestrator.process_ticket(
                ticket_key=ticket_number,
                ticket_title=ticket_title,
                ticket_description=ticket_description,
                update_jira=True
            )
        
        # Extract results from orchestration
        ai_analysis = orchestration_result.get('phase_1_analysis', {})
        rag_results = orchestration_result.get('phase_2_rag', {})
        tavily_results = orchestration_result.get('phase_3_tavily', {})
        jira_update_result = orchestration_result.get('phase_4_jira_update', {})
        code_generation = orchestration_result.get('phase_5_code_generation', {})
        validation_result = orchestration_result.get('phase_6_validation', {})
        
        log_and_print(f"\n{'='*80}", "INFO")
        log_and_print(f"✅ ORCHESTRATION COMPLETE", "INFO")
        log_and_print(f"   Status: {orchestration_result.get('status')}", "INFO")
        log_and_print(f"   RAG Results: {rag_results.get('count', 0)} similar fixes found", "INFO")
        log_and_print(f"   Tavily Results: {tavily_results.get('count', 0)} external resources found", "INFO")
        
        # Show code generation results if present
        if code_generation:
            log_and_print(f"   Code Generated: {code_generation.get('success', False)}", "INFO")
            if code_generation.get('success'):
                log_and_print(f"   Files Affected: {len(code_generation.get('files_affected', []))}", "INFO")
                log_and_print(f"   Confidence: {code_generation.get('confidence', 0) * 100:.0f}%", "INFO")
        
        # Show validation results if present
        if validation_result:
            log_and_print(f"   Validation Run: Yes", "INFO")
            log_and_print(f"   Tests Passed: {validation_result.get('tests_passed', False)}", "INFO")
            if validation_result.get('tests_passed'):
                log_and_print(f"   ✅ FIX VALIDATED AND READY FOR PR!", "INFO")
            else:
                log_and_print(f"   ❌ Validation failed, may need refinement", "INFO")
        
        log_and_print(f"   Jira Updated: {jira_update_result.get('success', False)}", "INFO")
        log_and_print(f"{'='*80}\n", "INFO")

        log_and_print(f"{'='*80}", "INFO")
        log_and_print(f"✅ WEBHOOK PROCESSING COMPLETE FOR {issue_key}", "INFO")
        log_and_print(f"{'='*80}\n", "INFO")

        # Build the clean JSON response with only required fields
        clean_response = {
            "ticket_key": issue_key,
            "ticket_title": ticket_title,
            "ai_summary": ai_analysis.get('problem_summary', 'N/A'),
            "verification_status": verification_result.get('status', 'UNKNOWN') if verification_result else 'SKIPPED',
            "summary_after_verification": {
                "project_detected": verification_result.get('project_detection', {}).get('detected_types', []) if verification_result else [],
                "commands_executed": len(verification_result.get('diagnostic_results', [])) if verification_result else 0,
                "commands_passed": sum(1 for d in verification_result.get('diagnostic_results', []) if d.get('success')) if verification_result else 0,
                "commands_failed": sum(1 for d in verification_result.get('diagnostic_results', []) if not d.get('success')) if verification_result else 0,
                "final_analysis": verification_result.get('final_analysis', 'N/A') if verification_result else 'N/A',
                "issue_verified": verification_result.get('status') == 'ISSUE_VERIFIED' if verification_result else False,
                "diagnostic_details": [
                    {
                        "command": d.get('command'),
                        "status": "PASS" if d.get('success') else "FAIL",
                        "error_message": d.get('stderr', '')[:300] if not d.get('success') else None
                    }
                    for d in (verification_result.get('diagnostic_results', []) if verification_result else [])
                ]
            } if verification_result else None
        }

        # Log the JSON response
        print(f"\n{'='*80}")
        print(f"📤 JSON RESPONSE:")
        print(f"{'='*80}")
        
        # Print full JSON without truncation - DIRECT PRINT ONLY
        json_str = json.dumps(clean_response, indent=2)
        print(json_str)  # Direct print without logging to avoid truncation
        sys.stdout.flush()
        
        print(f"{'='*80}\n")

        return jsonify(clean_response), 200
    except Exception as e:
        log_and_print(f"\n❌ ERROR PROCESSING ISSUE {issue_key}: {str(e)}", "ERROR")
        logger.exception("Failed to process issue %s", issue_key)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Managers are already initialized when module loads
    port = int(os.getenv("PORT", 5001))
    log_and_print(f"\n{'='*80}", "INFO")
    log_and_print(f"🚀 Starting Flask Webhook Listener + Approval API", "INFO")
    log_and_print(f"   Host: 0.0.0.0", "INFO")
    log_and_print(f"   Port: {port}", "INFO")
    log_and_print(f"   Approval API: /api/approval/*", "INFO")
    log_and_print(f"{'='*80}\n", "INFO")
    app.run(host="0.0.0.0", port=port)
