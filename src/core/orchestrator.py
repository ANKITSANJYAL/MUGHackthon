"""
Orchestrator for H-KFX Agent

Coordinates the workflow between AI analysis, RAG retrieval, Tavily search,
and Jira updates. This serves as the "brain" that sequences operations.
"""

import logging
from typing import Dict, Any, Optional
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_agent import analyze_ticket
from rag_system.rag_tool import get_rag_tool
from rag_system.tavily_tool import get_tavily_tool
from integrations.jira_client import get_jira_client, update_issue_with_analysis
from core.code_generator import get_code_generator
from core.code_validator import get_code_validator
from core.reflection_agent import get_reflection_agent

logger = logging.getLogger(__name__)

# Import progress tracker (will be initialized on first use)
try:
    from integrations.progress_tracker import get_progress_tracker
    _progress_tracker_available = True
except ImportError:
    _progress_tracker_available = False
    logger.warning("⚠️ Progress tracker not available")


class AgentOrchestrator:
    """
    Orchestrates the H-KFX agent workflow.
    
    This is a simplified orchestrator that coordinates:
    1. AI ticket analysis
    2. RAG internal knowledge retrieval
    3. Tavily external knowledge retrieval
    4. Jira updates with results
    """
    
    def __init__(self):
        """Initialize orchestrator with tools."""
        self.rag_tool = get_rag_tool()
        self.tavily_tool = get_tavily_tool()
        self.code_generator = get_code_generator()
        self.code_validator = get_code_validator()
        self.reflection_agent = get_reflection_agent(self.code_generator)
        self.jira_client = None
    
    def _get_jira_client(self):
        """Lazy initialize Jira client."""
        if self.jira_client is None:
            try:
                self.jira_client = get_jira_client()
            except Exception as e:
                logger.error(f"❌ Failed to initialize Jira client: {e}")
        return self.jira_client
    
    def process_ticket(
        self,
        ticket_key: str,
        ticket_title: str,
        ticket_description: str,
        update_jira: bool = True
    ) -> Dict[str, Any]:
        """
        Process a ticket through the complete H-KFX workflow.
        
        Workflow:
        1. Analyze ticket with AI
        2. Query RAG for similar past fixes
        3. Query Tavily for external knowledge
        4. Update Jira with findings
        5. Return consolidated results
        
        Args:
            ticket_key: Jira ticket key (e.g., 'PROJ-123')
            ticket_title: Ticket title/summary
            ticket_description: Full ticket description
            update_jira: Whether to post results back to Jira
        
        Returns:
            Dict with all results from the workflow
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 ORCHESTRATOR: Processing {ticket_key}")
        logger.info(f"{'='*80}\n")
        
        # Initialize progress tracking
        tracker = None
        if _progress_tracker_available:
            try:
                tracker = get_progress_tracker()
                tracker.start_ticket(ticket_key, {
                    'ticket_title': ticket_title,
                    'ticket_description': ticket_description[:200]
                })
            except Exception as e:
                logger.warning(f"⚠️ Failed to start progress tracking: {e}")
        
        result = {
            'ticket_key': ticket_key,
            'ticket_title': ticket_title,
            'phase_1_analysis': None,
            'phase_2_rag': None,
            'phase_3_tavily': None,
            'phase_4_jira_update': None,
            'status': 'UNKNOWN'
        }
        
        try:
            # ===== PHASE 1: AI Ticket Analysis =====
            if tracker:
                tracker.update_phase(ticket_key, 1, 'active')
            
            logger.info("📋 PHASE 1: AI Ticket Analysis")
            ai_analysis = analyze_ticket(ticket_key, ticket_title, ticket_description)
            result['phase_1_analysis'] = ai_analysis
            
            if tracker:
                tracker.update_phase(ticket_key, 1, 'completed', {
                    'problem_summary': ai_analysis.get('problem_summary', '')[:100],
                    'is_code_related': ai_analysis.get('is_code_related', False)
                })
            
            logger.info(f"   • Problem: {ai_analysis.get('problem_summary', 'N/A')[:100]}")
            logger.info(f"   • Code Related: {ai_analysis.get('is_code_related', False)}")
            
            if not ai_analysis.get('is_code_related'):
                logger.info("   ⏭️ Skipping further analysis (not code-related)")
                result['status'] = 'NOT_CODE_RELATED'
                if tracker:
                    tracker.complete_ticket(ticket_key, result)
                return result
            
            # ===== PHASE 2: RAG Internal Knowledge Search =====
            if tracker:
                tracker.update_phase(ticket_key, 2, 'active')
            
            logger.info("\n🔍 PHASE 2: RAG Internal Knowledge Search")
            rag_search_query = self._build_rag_query(ai_analysis)
            logger.info(f"   • Query: {rag_search_query[:100]}")
            
            rag_response = self.rag_tool.search_internal_knowledge(
                query=rag_search_query,
                limit=5
            )
            result['phase_2_rag'] = rag_response
            
            if rag_response['success']:
                logger.info(f"   ✅ Found {rag_response['count']} similar past fix(es)")
                if rag_response['count'] > 0:
                    top_result = rag_response['results'][0]
                    logger.info(f"   • Top: {top_result['source_id']} - {top_result['summary'][:60]}")
            else:
                logger.warning(f"   ⚠️ RAG search failed: {rag_response.get('error')}")
            
            if tracker:
                tracker.update_phase(ticket_key, 2, 'completed', {
                    'count': rag_response.get('count', 0)
                })
            
            # ===== PHASE 3: Tavily External Knowledge Search =====
            if tracker:
                tracker.update_phase(ticket_key, 3, 'active')
            
            logger.info("\n🌐 PHASE 3: Tavily External Knowledge Search")
            tavily_search_query = self._build_tavily_query(ai_analysis)
            logger.info(f"   • Query: {tavily_search_query[:100]}")
            
            tavily_response = self.tavily_tool.search_external_knowledge(
                query=tavily_search_query,
                max_results=5
            )
            result['phase_3_tavily'] = tavily_response
            
            if tavily_response['success']:
                is_mock = tavily_response.get('mock', False)
                logger.info(f"   ✅ Found {tavily_response['count']} external resource(s) {'[MOCK]' if is_mock else ''}")
            else:
                logger.warning(f"   ⚠️ Tavily search failed: {tavily_response.get('error')}")
            
            if tracker:
                tracker.update_phase(ticket_key, 3, 'completed', {
                    'count': tavily_response.get('count', 0)
                })
            
            # ===== PHASE 4: Update Jira with Findings =====
            if update_jira:
                logger.info("\n📤 PHASE 4: Updating Jira with findings")
                jira_client = self._get_jira_client()
                
                if jira_client:
                    jira_updated = update_issue_with_analysis(
                        jira=jira_client,
                        issue_key=ticket_key,
                        ai_summary=ai_analysis.get('problem_summary', 'N/A'),
                        rag_results=rag_response.get('results', []),
                        tavily_results=tavily_response.get('results', []),
                        status="In Progress"
                    )
                    result['phase_4_jira_update'] = {
                        'success': jira_updated,
                        'message': 'Jira updated with analysis' if jira_updated else 'Failed to update Jira'
                    }
                    
                    if jira_updated:
                        logger.info("   ✅ Jira updated successfully")
                    else:
                        logger.warning("   ⚠️ Failed to update Jira")
                else:
                    logger.warning("   ⚠️ Jira client not available")
                    result['phase_4_jira_update'] = {'success': False, 'message': 'Jira client unavailable'}
            else:
                logger.info("\n⏭️ PHASE 4: Skipping Jira update (disabled)")
                result['phase_4_jira_update'] = {'success': True, 'message': 'Skipped (disabled)'}
            
            result['status'] = 'KNOWLEDGE_RETRIEVAL_COMPLETE'
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ ORCHESTRATOR: Knowledge retrieval complete for {ticket_key}")
            logger.info(f"{'='*80}\n")
            
            return result
            
        except Exception as e:
            logger.exception(f"❌ ORCHESTRATOR: Error processing {ticket_key}")
            result['status'] = 'ERROR'
            result['error'] = str(e)
            return result
    
    def _build_rag_query(self, ai_analysis: Dict[str, Any]) -> str:
        """
        Build an optimized query for RAG based on AI analysis.
        
        Args:
            ai_analysis: Results from AI ticket analysis
        
        Returns:
            Optimized query string for semantic search
        """
        problem_summary = ai_analysis.get('problem_summary', '')
        analysis = ai_analysis.get('analysis', '')
        
        # Combine key information for semantic search
        query_parts = []
        
        if problem_summary:
            query_parts.append(problem_summary)
        
        if analysis and len(analysis) < 500:
            query_parts.append(analysis)
        
        query = " ".join(query_parts)
        
        # Limit query length for embedding
        if len(query) > 1000:
            query = query[:1000]
        
        return query
    
    def _build_tavily_query(self, ai_analysis: Dict[str, Any]) -> str:
        """
        Build an optimized query for Tavily based on AI analysis.
        
        Focus on API/library specific terms for better web search.
        
        Args:
            ai_analysis: Results from AI ticket analysis
        
        Returns:
            Optimized query string for web search
        """
        problem_summary = ai_analysis.get('problem_summary', '')
        
        # Extract key technical terms for web search
        # For better results, focus on error messages, library names, API calls
        query = problem_summary
        
        # Add keywords to improve search
        if any(term in problem_summary.lower() for term in ['error', 'exception', 'failed']):
            # Likely looking for error documentation
            query = f"{query} documentation fix solution"
        elif any(term in problem_summary.lower() for term in ['deprecated', 'version', 'upgrade']):
            # Likely looking for migration guides
            query = f"{query} migration guide changelog"
        
        # Limit query length
        if len(query) > 200:
            query = query[:200]
        
        return query
    
    def generate_code_fix(
        self,
        ticket_key: str,
        ticket_title: str,
        ticket_description: str,
        github_url: Optional[str] = None,
        update_jira: bool = True
    ) -> Dict[str, Any]:
        """
        Complete workflow: Analyze ticket → Retrieve knowledge → Generate code fix.
        
        This is an enhanced version of process_ticket() that also generates
        actual code fixes using the Code Generator.
        
        Args:
            ticket_key: Jira ticket key
            ticket_title: Ticket title/summary
            ticket_description: Full ticket description
            github_url: Optional GitHub repository URL
            update_jira: Whether to update Jira with results
        
        Returns:
            Dict with all phases including generated code fix
        """
        # First, run the knowledge retrieval workflow
        result = self.process_ticket(
            ticket_key=ticket_key,
            ticket_title=ticket_title,
            ticket_description=ticket_description,
            update_jira=False  # Don't update Jira yet, wait for code generation
        )
        
        # Only generate code if it's code-related
        if result.get('status') != 'KNOWLEDGE_RETRIEVAL_COMPLETE':
            logger.info("⏭️ Skipping code generation (ticket not suitable)")
            return result
        
        # ===== PHASE 5: Code Generation =====
        logger.info("\n🔧 PHASE 5: Code Generation")
        
        try:
            ticket_data = {
                'key': ticket_key,
                'summary': ticket_title,
                'description': ticket_description
            }
            
            code_fix = self.code_generator.generate_fix(
                ticket_data=ticket_data,
                ai_analysis=result['phase_1_analysis'],
                rag_results=result['phase_2_rag'],
                tavily_results=result['phase_3_tavily'],
                github_url=github_url
            )
            
            result['phase_5_code_generation'] = code_fix
            
            if code_fix['success']:
                logger.info(f"   ✅ Code fix generated successfully")
                logger.info(f"   • Files affected: {len(code_fix.get('files_affected', []))}")
                logger.info(f"   • Confidence: {code_fix.get('confidence', 0) * 100:.0f}%")
                result['status'] = 'CODE_FIX_GENERATED'
            else:
                logger.error(f"   ❌ Code generation failed: {code_fix.get('error')}")
                result['status'] = 'CODE_GENERATION_FAILED'
            
            # Now update Jira with everything (including code fix)
            if update_jira and code_fix['success']:
                logger.info("\n📤 Updating Jira with code fix")
                jira_client = self._get_jira_client()
                
                if jira_client:
                    # Post the generated fix as a comment
                    from integrations.jira_client import add_agent_comment
                    
                    fix_summary = self.code_generator.format_for_display(code_fix)
                    comment_added = add_agent_comment(
                        jira=jira_client,
                        issue_key=ticket_key,
                        title="🤖 Generated Code Fix",
                        body=fix_summary
                    )
                    
                    if comment_added:
                        logger.info("   ✅ Posted code fix to Jira")
                    else:
                        logger.warning("   ⚠️ Failed to post code fix to Jira")
            
        except Exception as e:
            logger.exception(f"❌ Code generation error: {e}")
            result['phase_5_code_generation'] = {
                'success': False,
                'error': str(e)
            }
            result['status'] = 'CODE_GENERATION_ERROR'
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ ORCHESTRATOR: Complete workflow finished for {ticket_key}")
        logger.info(f"{'='*80}\n")
        
        return result
    
    def get_hybrid_context_for_llm(self, orchestrator_result: Dict[str, Any]) -> str:
        """
        Format the hybrid knowledge (RAG + Tavily) into LLM context.
        
        This produces a formatted string that can be injected into
        the code generation LLM's prompt.
        
        Args:
            orchestrator_result: Results from process_ticket()
        
        Returns:
            Formatted context string for LLM prompt
        """
        context_parts = [
            "# KNOWLEDGE CONTEXT FOR CODE GENERATION\n",
            "The following information was retrieved to help fix this issue:\n"
        ]
        
        # Add RAG results
        rag_data = orchestrator_result.get('phase_2_rag', {})
        if rag_data.get('success') and rag_data.get('results'):
            rag_context = self.rag_tool.format_for_llm_context(rag_data['results'])
            context_parts.append(f"\n{rag_context}\n")
        
        # Add Tavily results
        tavily_data = orchestrator_result.get('phase_3_tavily', {})
        if tavily_data.get('success') and tavily_data.get('results'):
            tavily_context = self.tavily_tool.format_for_llm_context(tavily_data['results'])
            context_parts.append(f"\n{tavily_context}\n")
        
        context_parts.append("\n# END KNOWLEDGE CONTEXT\n")
        context_parts.append("Use the above information to generate an appropriate fix.\n")
        
        return "\n".join(context_parts)
    
    def generate_and_validate_fix(
        self,
        ticket_key: str,
        ticket_title: str,
        ticket_description: str,
        github_url: str,
        update_jira: bool = True,
        max_refinement_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Complete workflow WITH validation and feedback loop:
        1. Analyze ticket
        2. Retrieve knowledge
        3. Generate code fix
        4. Validate by applying & running tests
        5. If validation fails, refine and retry (up to max attempts)
        6. Only proceed if tests pass
        
        Args:
            ticket_key: Jira ticket key
            ticket_title: Ticket title
            ticket_description: Ticket description
            github_url: GitHub repository URL (REQUIRED for validation)
            update_jira: Whether to update Jira
            max_refinement_attempts: Maximum refinement iterations
        
        Returns:
            Dict with all phases including validation results
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 ORCHESTRATOR: Starting VALIDATED workflow for {ticket_key}")
        logger.info(f"{'='*80}\n")
        
        if not github_url:
            return {
                'success': False,
                'error': 'GitHub URL required for validation',
                'status': 'VALIDATION_IMPOSSIBLE'
            }
        
        # Phase 1-3: Knowledge Retrieval
        result = self.process_ticket(
            ticket_key=ticket_key,
            ticket_title=ticket_title,
            ticket_description=ticket_description,
            update_jira=False
        )
        
        if result.get('status') != 'KNOWLEDGE_RETRIEVAL_COMPLETE':
            logger.info("⏭️ Skipping code generation (ticket not suitable)")
            return result
        
        # Store original data for refinement
        ticket_data = {
            'key': ticket_key,
            'summary': ticket_title,
            'description': ticket_description
        }
        
        # Get progress tracker
        tracker = None
        if _progress_tracker_available:
            try:
                tracker = get_progress_tracker()
            except Exception as e:
                logger.warning(f"⚠️ Failed to get progress tracker: {e}")
        
        # Phase 5: Initial Code Generation
        if tracker:
            tracker.update_phase(ticket_key, 4, 'active')
        
        logger.info("\n🔧 PHASE 5: Initial Code Generation")
        
        code_fix = self.code_generator.generate_fix(
            ticket_data=ticket_data,
            ai_analysis=result['phase_1_analysis'],
            rag_results=result['phase_2_rag'],
            tavily_results=result['phase_3_tavily'],
            github_url=github_url
        )
        
        result['phase_5_code_generation'] = code_fix
        
        if not code_fix['success']:
            logger.error(f"   ❌ Initial code generation failed")
            result['status'] = 'CODE_GENERATION_FAILED'
            if tracker:
                tracker.error_ticket(ticket_key, 'Code generation failed', 4)
            return result
        
        logger.info(f"   ✅ Initial code fix generated")
        logger.info(f"   • Files: {len(code_fix.get('files_affected', []))}")
        logger.info(f"   • Confidence: {code_fix.get('confidence', 0) * 100:.0f}%")
        
        if tracker:
            tracker.update_phase(ticket_key, 4, 'completed', {
                'files_affected': len(code_fix.get('files_affected', [])),
                'confidence': code_fix.get('confidence', 0)
            })
        
        # Phase 6: Validation Loop
        validation_attempts = []
        current_fix = code_fix
        
        for attempt in range(max_refinement_attempts + 1):  # +1 for initial attempt
            if tracker:
                tracker.update_phase(ticket_key, 5, 'active')
            
            logger.info(f"\n🧪 PHASE 6.{attempt}: Code Validation (Attempt {attempt + 1}/{max_refinement_attempts + 1})")
            
            validation_result = self.code_validator.validate_fix(
                github_url=github_url,
                code_changes=current_fix.get('code_changes', []),
                ticket_key=ticket_key,
                ticket_description=ticket_description
            )
            
            validation_attempts.append({
                'attempt': attempt + 1,
                'code_fix': current_fix,
                'validation': validation_result
            })
            
            if validation_result.get('tests_passed'):
                logger.info(f"   ✅ VALIDATION PASSED! Tests successful.")
                logger.info(f"   • Branch: {validation_result.get('validation_branch')}")
                logger.info(f"   • Repo: {validation_result.get('repo_path')}")
                
                result['phase_6_validation'] = validation_result
                result['status'] = 'VALIDATED_FIX_READY'
                result['validation_attempts'] = validation_attempts
                result['final_code_fix'] = current_fix
                
                if tracker:
                    tracker.update_phase(ticket_key, 5, 'completed', {
                        'tests_passed': True,
                        'validation_branch': validation_result.get('validation_branch')
                    })
                
                # Update Jira with success
                if update_jira:
                    if tracker:
                        tracker.update_phase(ticket_key, 7, 'active')
                    
                    self._update_jira_with_validated_fix(
                        ticket_key=ticket_key,
                        code_fix=current_fix,
                        validation_result=validation_result,
                        ticket_title=ticket_title,
                        ticket_description=ticket_description,
                        github_url=github_url,
                        orchestration_result=result
                    )
                    
                    if tracker:
                        tracker.update_phase(ticket_key, 7, 'completed')
                        tracker.complete_ticket(ticket_key, result)
                
                logger.info(f"\n{'='*80}")
                logger.info(f"✅ VALIDATED WORKFLOW COMPLETE: Fix ready for PR!")
                logger.info(f"{'='*80}\n")
                
                return result
            
            else:
                logger.warning(f"   ❌ Validation failed")
                logger.warning(f"   • Errors: {len(validation_result.get('errors', []))}")
                
                # If this was the last attempt, give up
                if attempt >= max_refinement_attempts:
                    logger.error(f"   ⚠️ Max refinement attempts ({max_refinement_attempts}) reached")
                    result['phase_6_validation'] = validation_result
                    result['status'] = 'VALIDATION_FAILED_MAX_ATTEMPTS'
                    result['validation_attempts'] = validation_attempts
                    return result
                
                # Phase 7: Reflection & Refinement
                if tracker:
                    tracker.update_phase(ticket_key, 6, 'active')
                
                logger.info(f"\n🔄 PHASE 7.{attempt}: Reflection & Refinement")
                
                refinement_result = self.reflection_agent.refine_with_feedback(
                    original_ticket_data=ticket_data,
                    original_ai_analysis=result['phase_1_analysis'],
                    rag_results=result['phase_2_rag'],
                    tavily_results=result['phase_3_tavily'],
                    failed_code_fix=current_fix,
                    validation_result=validation_result,
                    github_url=github_url
                )
                
                if refinement_result['success']:
                    logger.info(f"   ✅ Refined fix generated, will re-validate")
                    current_fix = refinement_result['refined_fix']
                    
                    if tracker:
                        tracker.update_phase(ticket_key, 6, 'completed', {
                            'refinement_success': True
                        })
                else:
                    logger.error(f"   ❌ Refinement failed, giving up")
                    result['status'] = 'REFINEMENT_FAILED'
                    result['validation_attempts'] = validation_attempts
                    
                    if tracker:
                        tracker.error_ticket(ticket_key, 'Refinement failed', 6)
                    return result
        
        # Should never reach here
        result['status'] = 'UNKNOWN_ERROR'
        return result
    
    def _update_jira_with_validated_fix(
        self,
        ticket_key: str,
        code_fix: Dict[str, Any],
        validation_result: Dict[str, Any],
        ticket_title: str = "",
        ticket_description: str = "",
        github_url: str = "",
        orchestration_result: Dict[str, Any] = None
    ):
        """Update Jira with a validated code fix and create approval session."""
        try:
            jira_client = self._get_jira_client()
            if not jira_client:
                logger.warning("   ⚠️ No Jira client available, skipping update")
                return
            
            from integrations.jira_client import add_agent_comment, safe_transition
            
            # First, transition to "Ready for Review" status
            logger.info(f"   🔄 Transitioning {ticket_key} to 'Ready for Review'...")
            transitioned = safe_transition(jira_client, ticket_key, "Ready for Review")
            
            # If that fails, try "In Review" as fallback
            if not transitioned:
                logger.info(f"   🔄 Trying 'In Review' instead...")
                transitioned = safe_transition(jira_client, ticket_key, "In Review")
            
            if not transitioned:
                logger.warning(f"   ⚠️ Could not transition status (workflow may not support it)")
            
            # Create approval session if github_url provided
            approval_url = None
            if github_url and orchestration_result:
                try:
                    from core.approval_manager import get_approval_manager
                    
                    approval_manager = get_approval_manager()
                    session_id = approval_manager.create_session(
                        ticket_key=ticket_key,
                        ticket_title=ticket_title,
                        ticket_description=ticket_description,
                        orchestration_result=orchestration_result,
                        github_url=github_url
                    )
                    
                    # Generate approval URL
                    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
                    approval_url = f"{frontend_url}/approve/{session_id}"
                    logger.info(f"   ✅ Approval session created: {approval_url}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to create approval session: {e}")
            
            # Format the validated fix (concise)
            fix_summary = self.code_generator.format_for_display(code_fix)
            
            # Add validation details
            validation_info = [
                "\n---",
                f"✅ **All tests passed** | Branch: `{validation_result.get('validation_branch')}`"
            ]
            
            if approval_url:
                validation_info.extend([
                    f"",
                    f"🔗 **Review and Approve:** {approval_url}",
                    f"",
                    f"Click the link above to review the changes and approve the merge."
                ])
            else:
                validation_info.append("\n**Action Required:** Review changes and approve for PR creation")
            
            full_comment = fix_summary + "\n".join(validation_info)
            
            # Post the comment with the fix details
            comment_success = add_agent_comment(
                jira=jira_client,
                issue_key=ticket_key,
                title="✅ Fix Ready for Review",
                body=full_comment
            )
            
            if comment_success:
                logger.info("   ✅ Posted validated fix to Jira")
            else:
                logger.error("   ❌ Failed to post comment to Jira")
            
        except Exception as e:
            logger.error(f"   ❌ Failed to update Jira: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def close(self):
        """Clean up resources."""
        self.rag_tool.close()
        self.tavily_tool.close()
        self.code_validator.cleanup_all()
        logger.info("🔌 Orchestrator shutdown complete")


# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
