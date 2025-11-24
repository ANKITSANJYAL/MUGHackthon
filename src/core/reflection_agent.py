"""
Reflection Agent

Provides feedback loop for code refinement.
Reviews validation results and regenerates fixes if tests fail.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ReflectionAgent:
    """
    Provides intelligent feedback and refinement loop for generated code.
    
    When validation fails:
    1. Analyzes the failure (patch errors, test failures, etc.)
    2. Generates refined instructions for the code generator
    3. Coordinates regeneration with updated context
    """
    
    def __init__(self, code_generator, max_iterations: int = 3):
        """
        Initialize Reflection Agent.
        
        Args:
            code_generator: CodeGenerator instance to use for regeneration
            max_iterations: Maximum refinement attempts
        """
        self.code_generator = code_generator
        self.max_iterations = max_iterations
        logger.info(f"✅ Reflection Agent initialized (max iterations: {max_iterations})")
    
    def refine_with_feedback(
        self,
        original_ticket_data: Dict[str, Any],
        original_ai_analysis: Dict[str, Any],
        rag_results: Dict[str, Any],
        tavily_results: Dict[str, Any],
        failed_code_fix: Dict[str, Any],
        validation_result: Dict[str, Any],
        github_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attempt to refine a failed code fix based on validation feedback.
        
        Args:
            original_ticket_data: Original ticket information
            original_ai_analysis: Initial AI analysis
            rag_results: RAG search results
            tavily_results: Tavily search results
            failed_code_fix: The code fix that failed validation
            validation_result: Results from code validator
            github_url: Optional GitHub repository URL
        
        Returns:
            Dict with:
                - success: bool
                - refined_fix: New code fix (if successful)
                - iteration: Which iteration succeeded
                - all_attempts: List of all attempts
                - final_message: Summary of refinement process
        """
        logger.info("🔄 Reflection Agent: Starting refinement process")
        
        result = {
            'success': False,
            'refined_fix': None,
            'iteration': 0,
            'all_attempts': [],
            'final_message': ''
        }
        
        # Add initial failed attempt
        result['all_attempts'].append({
            'iteration': 0,
            'code_fix': failed_code_fix,
            'validation': validation_result,
            'feedback': validation_result.get('feedback', '')
        })
        
        # Prepare enriched context with failure feedback
        enriched_analysis = self._enrich_analysis_with_feedback(
            original_ai_analysis,
            validation_result
        )
        
        # Refinement loop
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"🔄 Refinement iteration {iteration}/{self.max_iterations}")
            
            try:
                # Enrich ticket data with test failures (use FULL output if available)
                enriched_ticket_data = original_ticket_data.copy()
                enriched_ticket_data['test_output'] = validation_result.get('test_output_full', validation_result.get('test_output', ''))
                enriched_ticket_data['validation_feedback'] = validation_result.get('feedback', '')
                enriched_ticket_data['previous_attempt'] = iteration  # Track iteration number
                
                # Generate refined fix
                refined_fix = self.code_generator.generate_fix(
                    ticket_data=enriched_ticket_data,
                    ai_analysis=enriched_analysis,
                    rag_results=rag_results,
                    tavily_results=tavily_results,
                    github_url=github_url
                )
                
                if not refined_fix.get('success'):
                    logger.warning(f"   ⚠️ Refinement {iteration} generation failed")
                    result['all_attempts'].append({
                        'iteration': iteration,
                        'code_fix': refined_fix,
                        'validation': None,
                        'feedback': 'Code generation failed'
                    })
                    continue
                
                logger.info(f"   ✅ Refinement {iteration} generated")
                
                # This would be validated again by the orchestrator
                # For now, we return it as the refined fix
                result['success'] = True
                result['refined_fix'] = refined_fix
                result['iteration'] = iteration
                result['final_message'] = f"Successfully refined fix after {iteration} iteration(s)"
                
                result['all_attempts'].append({
                    'iteration': iteration,
                    'code_fix': refined_fix,
                    'validation': None,  # Will be validated by orchestrator
                    'feedback': 'Ready for re-validation'
                })
                
                return result
                
            except Exception as e:
                logger.error(f"   ❌ Refinement {iteration} error: {e}")
                result['all_attempts'].append({
                    'iteration': iteration,
                    'error': str(e),
                    'feedback': f'Refinement failed: {str(e)}'
                })
        
        # Max iterations reached without success
        result['final_message'] = f"Failed to refine fix after {self.max_iterations} attempts"
        logger.warning(f"⚠️ {result['final_message']}")
        
        return result
    
    def _enrich_analysis_with_feedback(
        self,
        original_analysis: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich the AI analysis with validation feedback.
        
        This adds the validation failures and feedback to the analysis
        so the code generator can learn from mistakes.
        """
        enriched = original_analysis.copy()
        
        # Add validation feedback section
        feedback_section = [
            "\n\n## PREVIOUS ATTEMPT FAILED - VALIDATION FEEDBACK\n",
            "The previous code fix failed validation. Please address these issues:\n"
        ]
        
        if validation_result.get('errors'):
            feedback_section.append("\n**Errors:**")
            for error in validation_result['errors']:
                feedback_section.append(f"- {error}")
        
        if validation_result.get('feedback'):
            feedback_section.append(f"\n**Detailed Feedback:**")
            feedback_section.append(validation_result['feedback'])
        
        if validation_result.get('test_output'):
            feedback_section.append(f"\n**Test Output:**")
            feedback_section.append(f"```\n{validation_result['test_output'][-1000:]}\n```")
        
        feedback_section.append("\n**Instructions for Refinement:**")
        feedback_section.append("- Review the errors above carefully")
        feedback_section.append("- Ensure file paths are correct")
        feedback_section.append("- Generate code that will pass all existing tests")
        feedback_section.append("- Be more conservative with changes if needed")
        feedback_section.append("- Double-check syntax and logic")
        feedback_section.append("")
        feedback_section.append("**🚨 CRITICAL - If you see 'ImportError: cannot import name':**")
        feedback_section.append("- You OMITTED a function/class that tests are trying to import")
        feedback_section.append("- The CURRENT FILE CONTENT shows ALL functions/classes in the file")
        feedback_section.append("- Your output MUST include ALL of them, not just the class or function you're fixing")
        feedback_section.append("- Example: If file has InternalAPIConfig class AND call_internal_service() function,")
        feedback_section.append("  include BOTH in your output, even if you're only fixing the class")
        feedback_section.append("")
        feedback_section.append("**🚨 CRITICAL - If you see 'ValueError: Unknown service name' or 'AttributeError':**")
        feedback_section.append("- You MODIFIED a method/function that should have been COPIED EXACTLY")
        feedback_section.append("- Go back to the CURRENT FILE CONTENT provided")
        feedback_section.append("- Copy ALL methods EXACTLY as they appear in the original")
        feedback_section.append("- DO NOT change method logic, DO NOT add/remove services")
        feedback_section.append("- ONLY change the specific variable mentioned in the ticket (e.g., port number)")
        feedback_section.append("")
        feedback_section.append("**For config/api_config.py port fixes:**")
        feedback_section.append("- Change: API_GATEWAY_PORT from 8080 to 8081")
        feedback_section.append("- Update: ALL URL strings to use the new port")
        feedback_section.append("- Copy EXACTLY: get_service_url() method unchanged")
        feedback_section.append("- Copy EXACTLY: call_internal_service() function unchanged")
        feedback_section.append("- Include EVERYTHING from the original file")
        
        # Append to problem analysis
        enriched['problem_analysis'] = (
            original_analysis.get('problem_analysis', '') +
            "\n".join(feedback_section)
        )
        
        return enriched
    
    def analyze_failure_pattern(
        self,
        all_attempts: list
    ) -> Dict[str, Any]:
        """
        Analyze patterns in failed attempts to provide insights.
        
        Args:
            all_attempts: List of all refinement attempts
        
        Returns:
            Dict with analysis insights
        """
        analysis = {
            'total_attempts': len(all_attempts),
            'common_errors': [],
            'recommendation': ''
        }
        
        # Extract common error patterns
        error_counts = {}
        for attempt in all_attempts:
            validation = attempt.get('validation', {})
            for error in validation.get('errors', []):
                error_type = self._classify_error(error)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Sort by frequency
        if error_counts:
            analysis['common_errors'] = sorted(
                error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
        
        # Generate recommendation
        if not error_counts:
            analysis['recommendation'] = "No clear error pattern detected. May need human review."
        elif 'file_not_found' in [e[0] for e in analysis['common_errors']]:
            analysis['recommendation'] = "File path issues detected. Verify repository structure."
        elif 'test_failure' in [e[0] for e in analysis['common_errors']]:
            analysis['recommendation'] = "Tests consistently failing. May need different approach."
        else:
            analysis['recommendation'] = "Multiple error types. Consider manual intervention."
        
        return analysis
    
    def _classify_error(self, error: str) -> str:
        """Classify error into categories."""
        error_lower = error.lower()
        
        if 'file' in error_lower and ('not found' in error_lower or 'does not exist' in error_lower):
            return 'file_not_found'
        elif 'test' in error_lower and 'failed' in error_lower:
            return 'test_failure'
        elif 'syntax' in error_lower or 'parse' in error_lower:
            return 'syntax_error'
        elif 'timeout' in error_lower:
            return 'timeout'
        elif 'compile' in error_lower or 'build' in error_lower:
            return 'compilation_error'
        else:
            return 'other'


# Singleton pattern
_reflection_agent_instance = None

def get_reflection_agent(code_generator=None) -> ReflectionAgent:
    """Get or create the singleton ReflectionAgent instance."""
    global _reflection_agent_instance
    if _reflection_agent_instance is None:
        if code_generator is None:
            from core.code_generator import get_code_generator
            code_generator = get_code_generator()
        _reflection_agent_instance = ReflectionAgent(code_generator)
    return _reflection_agent_instance
