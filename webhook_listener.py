import os
import sys
import logging
import json
from flask import Flask, request, jsonify
from jira_client import get_jira_client, get_issue
from analyzer import ComprehensiveAnalysisAgent
from ai_agent import analyze_ticket

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
        
        # Phase 1: Quick AI Analysis
        log_and_print(f"\n🤖 PHASE 1: Quick AI Analysis (Parsing Jira Ticket)", "INFO")
        log_and_print(f"   ⏳ Calling AI to analyze ticket...\n", "INFO")
        ai_analysis = analyze_ticket(ticket_number, ticket_title, ticket_description)
        
        log_and_print(f"   ✅ AI Analysis Complete:", "INFO")
        log_and_print(f"      • Problem Summary: {ai_analysis['problem_summary']}", "INFO")
        log_and_print(f"      • Is Code Related: {ai_analysis['is_code_related']}", "INFO")
        if ai_analysis.get('github_url'):
            log_and_print(f"      • GitHub URL: {ai_analysis['github_url']}", "INFO")
        
        # Phase 2: Comprehensive Code Analysis
        verification_result = None
        default_repo = os.getenv("DEFAULT_REPO_URL")
        
        if default_repo and ai_analysis['is_code_related']:
            log_and_print(f"\n🚀 PHASE 2: Comprehensive Code Analysis", "INFO")
            log_and_print(f"   Repository URL: {default_repo}", "INFO")
            log_and_print(f"{'='*80}\n", "INFO")
            
            analyzer = ComprehensiveAnalysisAgent()
            verification_result = analyzer.analyze_issue(
                ticket_number,
                ticket_description,
                default_repo
            )
            
            log_and_print(f"\n{'='*80}", "INFO")
            log_and_print(f"✅ PHASE 2 COMPLETE", "INFO")
            log_and_print(f"   Final Status: {verification_result.get('status', 'UNKNOWN')}", "INFO")
            log_and_print(f"   Analysis: {verification_result.get('final_analysis', 'N/A')}", "INFO")
            log_and_print(f"{'='*80}\n", "INFO")
        else:
            if not ai_analysis['is_code_related']:
                log_and_print(f"\n⏭️  Skipping comprehensive analysis (ticket is not code-related)", "INFO")
            if not default_repo:
                log_and_print(f"\n⏭️  Skipping comprehensive analysis (no DEFAULT_REPO_URL configured)", "INFO")

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
    port = int(os.getenv("PORT", 5000))
    log_and_print(f"\n{'='*80}", "INFO")
    log_and_print(f"🚀 Starting Flask Webhook Listener", "INFO")
    log_and_print(f"   Host: 0.0.0.0", "INFO")
    log_and_print(f"   Port: {port}", "INFO")
    log_and_print(f"{'='*80}\n", "INFO")
    app.run(host="0.0.0.0", port=port)
