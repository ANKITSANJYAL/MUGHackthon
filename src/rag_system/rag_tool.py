"""
MCP-style Tool Wrapper for MongoDB RAG

Provides a clean interface for the orchestrator to query internal knowledge.
This wrapper encapsulates RAG operations as a tool that can be called by the agent.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

from .query_rag import RAGQueryEngine

logger = logging.getLogger(__name__)


class RAGTool:
    """
    MCP-compatible tool wrapper for MongoDB Atlas Vector RAG.
    
    This tool allows the orchestrator to query internal organizational knowledge
    (past fixes, resolutions) using semantic search over vector embeddings.
    """
    
    def __init__(self):
        """Initialize RAG tool with query engine."""
        load_dotenv()
        self.engine = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of RAG engine."""
        if not self._initialized:
            try:
                self.engine = RAGQueryEngine()
                self._initialized = True
                logger.info("✅ RAG Tool initialized successfully")
            except Exception as e:
                logger.error(f"❌ RAG Tool initialization failed: {e}")
                raise
    
    def search_internal_knowledge(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Search internal knowledge base for similar past fixes.
        
        Args:
            query: Natural language description of the bug/issue
            limit: Maximum number of results to return
            filters: Optional filters (module, fix_type)
        
        Returns:
            Dict with:
                - success: bool
                - results: List of relevant past fixes
                - summary: Human-readable summary
                - error: Error message if failed
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"🔍 RAG Tool: Searching for '{query[:50]}...'")
            
            # Extract filters
            module_filter = filters.get('module') if filters else None
            fix_type_filter = filters.get('fix_type') if filters else None
            
            # Perform semantic search
            results = self.engine.semantic_search(
                query=query,
                limit=limit,
                module_filter=module_filter,
                fix_type_filter=fix_type_filter
            )
            
            if not results:
                logger.warning("⚠️ No similar past fixes found")
                return {
                    'success': True,
                    'results': [],
                    'summary': 'No similar past fixes found in internal knowledge base.',
                    'count': 0
                }
            
            # Format results for agent consumption
            formatted_results = []
            for idx, result in enumerate(results, 1):
                formatted_results.append({
                    'rank': idx,
                    'source_id': result.get('source_id'),
                    'summary': result.get('ticket_summary'),
                    'module': result.get('project_module'),
                    'context': result.get('internal_context'),
                    'fix_type': result.get('fix_type'),
                    'code_snippet': result.get('gold_patch_snippet'),
                    'relevance_score': round(result.get('score', 0), 3)
                })
            
            # Generate summary
            top_result = formatted_results[0]
            summary = (
                f"Found {len(formatted_results)} similar past fix(es). "
                f"Most relevant: {top_result['source_id']} - {top_result['summary']} "
                f"(score: {top_result['relevance_score']})"
            )
            
            logger.info(f"✅ RAG Tool: Found {len(results)} relevant results")
            
            return {
                'success': True,
                'results': formatted_results,
                'summary': summary,
                'count': len(formatted_results)
            }
            
        except Exception as e:
            error_msg = f"RAG search failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'results': [],
                'summary': error_msg,
                'error': str(e),
                'count': 0
            }
    
    def get_fix_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific past fix by its source ID.
        
        Args:
            source_id: The ticket/fix ID (e.g., 'JIRA-4501')
        
        Returns:
            Dict with fix details or None if not found
        """
        self._ensure_initialized()
        
        try:
            result = self.engine.collection.find_one(
                {'source_id': source_id},
                {'_id': 0}
            )
            
            if result:
                # Remove embedding from response (too large)
                result.pop('embedding', None)
                logger.info(f"✅ Retrieved fix: {source_id}")
            else:
                logger.warning(f"⚠️ Fix not found: {source_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve fix {source_id}: {e}")
            return None
    
    def format_for_llm_context(self, results: List[Dict]) -> str:
        """
        Format RAG results into a string suitable for LLM context.
        
        Args:
            results: List of RAG search results
        
        Returns:
            Formatted string for LLM prompt
        """
        if not results:
            return "No relevant past fixes found in internal knowledge base."
        
        context_parts = ["=== INTERNAL KNOWLEDGE: Past Similar Fixes ===\n"]
        
        for result in results:
            context_parts.append(
                f"\n--- Fix #{result['rank']}: {result['source_id']} ---\n"
                f"Summary: {result['summary']}\n"
                f"Module: {result['module']}\n"
                f"Type: {result['fix_type']}\n"
                f"Context: {result['context']}\n"
            )
            
            if result.get('code_snippet'):
                context_parts.append(f"Code Example:\n```\n{result['code_snippet']}\n```\n")
            
            context_parts.append(f"Relevance Score: {result['relevance_score']}\n")
        
        return "\n".join(context_parts)
    
    def close(self):
        """Close database connections."""
        if self.engine and self.engine.client:
            self.engine.client.close()
            logger.info("🔌 RAG Tool connections closed")


# Singleton instance for easy import
_rag_tool_instance = None

def get_rag_tool() -> RAGTool:
    """Get or create the global RAG tool instance."""
    global _rag_tool_instance
    if _rag_tool_instance is None:
        _rag_tool_instance = RAGTool()
    return _rag_tool_instance
