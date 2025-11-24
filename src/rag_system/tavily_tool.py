"""
MCP-style Tool Wrapper for Tavily AI Search

Provides external knowledge retrieval for API changes, deprecations, and library updates.
This wrapper encapsulates Tavily operations as a tool that can be called by the agent.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class TavilyTool:
    """
    MCP-compatible tool wrapper for Tavily AI Search.
    
    This tool allows the orchestrator to query external real-time knowledge
    (API docs, library changes, deprecations) using AI-optimized web search.
    """
    
    def __init__(self):
        """Initialize Tavily tool."""
        load_dotenv()
        self.api_key = os.getenv('TAVILY_API_KEY')
        self.client = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of Tavily client."""
        if not self._initialized:
            try:
                if not self.api_key:
                    logger.warning("⚠️ TAVILY_API_KEY not set - Tavily tool will use mock mode")
                    self.client = None  # Mock mode
                else:
                    from tavily import TavilyClient
                    self.client = TavilyClient(api_key=self.api_key)
                    logger.info("✅ Tavily Tool initialized successfully with real API")
                
                self._initialized = True
            except Exception as e:
                logger.error(f"❌ Tavily Tool initialization failed: {e}")
                logger.warning("⚠️ Falling back to mock mode")
                self.client = None
    
    def search_external_knowledge(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced"
    ) -> Dict[str, Any]:
        """
        Search external knowledge for API changes, deprecations, documentation.
        
        Args:
            query: Search query (e.g., "Flask 3.0 breaking changes response cookies")
            max_results: Maximum number of results
            search_depth: "basic" or "advanced"
        
        Returns:
            Dict with:
                - success: bool
                - results: List of relevant web results
                - summary: Human-readable summary
                - error: Error message if failed
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"🌐 Tavily Tool: Searching for '{query[:50]}...'")
            
            if self.client is None:
                # Mock response when API not available
                logger.warning("⚠️ Using mock Tavily response (API not configured)")
                return self._mock_search_response(query)
            
            # Real Tavily API search
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_domains=["stackoverflow.com", "github.com", "docs.python.org", "medium.com"],
                exclude_domains=["pinterest.com", "facebook.com", "twitter.com"]
            )
            
            # Format results
            results = []
            for idx, result in enumerate(response.get('results', []), 1):
                results.append({
                    'rank': idx,
                    'title': result.get('title', 'No title'),
                    'url': result.get('url', ''),
                    'content': result.get('content', ''),
                    'score': result.get('score', 0.0),
                    'published_date': result.get('published_date', 'Unknown')
                })
            
            logger.info(f"✅ Tavily Tool: Found {len(results)} real results")
            return {
                'success': True,
                'results': results,
                'summary': f"Found {len(results)} external resources",
                'count': len(results),
                'query': query
            }
            
        except Exception as e:
            error_msg = f"Tavily search failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'results': [],
                'summary': error_msg,
                'error': str(e),
                'count': 0
            }
    
    def _mock_search_response(self, query: str) -> Dict[str, Any]:
        """
        Generate mock response for testing (until Tavily is integrated).
        
        This allows the pipeline to work without Tavily API key during development.
        """
        mock_results = [
            {
                'rank': 1,
                'title': f'Documentation: {query}',
                'url': 'https://docs.example.com/api-changes',
                'content': f'Mock result for query: {query}. This would contain real API documentation and changelog information from Tavily AI search.',
                'score': 0.95,
                'published_date': '2024-11-20'
            },
            {
                'rank': 2,
                'title': f'Stack Overflow: Solutions for {query}',
                'url': 'https://stackoverflow.com/questions/mock',
                'content': 'Community discussions and solutions related to this issue from Stack Overflow.',
                'score': 0.88,
                'published_date': '2024-11-15'
            }
        ]
        
        summary = (
            f"[MOCK] Found {len(mock_results)} external resources. "
            f"Top result: Documentation with score 0.95. "
            f"(Enable with TAVILY_API_KEY for real results)"
        )
        
        return {
            'success': True,
            'results': mock_results,
            'summary': summary,
            'count': len(mock_results),
            'mock': True  # Flag to indicate this is mock data
        }
    
    def format_for_llm_context(self, results: List[Dict]) -> str:
        """
        Format Tavily results into a string suitable for LLM context.
        
        Args:
            results: List of Tavily search results
        
        Returns:
            Formatted string for LLM prompt
        """
        if not results:
            return "No relevant external documentation found."
        
        context_parts = ["=== EXTERNAL KNOWLEDGE: Web Search Results ===\n"]
        
        for result in results:
            context_parts.append(
                f"\n--- Result #{result['rank']}: {result['title']} ---\n"
                f"Source: {result['url']}\n"
                f"Content: {result['content'][:500]}...\n"
                f"Relevance Score: {result['score']}\n"
            )
            
            if result.get('published_date'):
                context_parts.append(f"Date: {result['published_date']}\n")
        
        return "\n".join(context_parts)
    
    def close(self):
        """Close connections."""
        logger.info("🔌 Tavily Tool connections closed")


# Singleton instance for easy import
_tavily_tool_instance = None

def get_tavily_tool() -> TavilyTool:
    """Get or create the global Tavily tool instance."""
    global _tavily_tool_instance
    if _tavily_tool_instance is None:
        _tavily_tool_instance = TavilyTool()
    return _tavily_tool_instance
