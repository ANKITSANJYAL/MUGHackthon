"""
RAG Query Utilities

This module provides functions to query the historical fixes database
and retrieve relevant context for bug fixing.
"""

import os
from typing import List, Dict, Optional
from pymongo import MongoClient
from dotenv import load_dotenv


class RAGQueryEngine:
    """Query engine for retrieving relevant historical fixes."""
    
    def __init__(self):
        """Initialize connection to RAG database."""
        load_dotenv()
        
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'jiae_rag')
        self.collection_name = os.getenv('MONGODB_COLLECTION_NAME', 'historical_fixes')
        
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
    
    def search_by_tags(self, tags: List[str], limit: int = 5) -> List[Dict]:
        """
        Search for historical fixes matching any of the provided tags.
        
        Args:
            tags: List of tags to search for
            limit: Maximum number of results to return
            
        Returns:
            List of matching ticket documents
        """
        query = {"tags": {"$in": tags}}
        results = list(self.collection.find(
            query,
            {"_id": 0}
        ).limit(limit))
        
        return results
    
    def search_by_component(self, component: str, limit: int = 5) -> List[Dict]:
        """
        Search for historical fixes in a specific component.
        
        Args:
            component: Component name (e.g., 'authentication', 'database')
            limit: Maximum number of results to return
            
        Returns:
            List of matching ticket documents
        """
        query = {"component": component}
        results = list(self.collection.find(
            query,
            {"_id": 0}
        ).sort("severity", -1).limit(limit))
        
        return results
    
    def search_by_keywords(self, keywords: List[str], limit: int = 5) -> List[Dict]:
        """
        Search for historical fixes using text search on multiple fields.
        
        Args:
            keywords: List of keywords to search for
            limit: Maximum number of results to return
            
        Returns:
            List of matching ticket documents
        """
        # Build regex query for multiple fields
        regex_queries = []
        for keyword in keywords:
            regex_queries.append({
                "$or": [
                    {"title": {"$regex": keyword, "$options": "i"}},
                    {"description": {"$regex": keyword, "$options": "i"}},
                    {"root_cause": {"$regex": keyword, "$options": "i"}},
                    {"solution": {"$regex": keyword, "$options": "i"}}
                ]
            })
        
        query = {"$or": regex_queries} if regex_queries else {}
        results = list(self.collection.find(
            query,
            {"_id": 0}
        ).limit(limit))
        
        return results
    
    def search_by_severity(self, severity: str, limit: int = 10) -> List[Dict]:
        """
        Search for historical fixes by severity level.
        
        Args:
            severity: Severity level ('critical', 'high', 'medium', 'low')
            limit: Maximum number of results to return
            
        Returns:
            List of matching ticket documents
        """
        query = {"severity": severity}
        results = list(self.collection.find(
            query,
            {"_id": 0}
        ).limit(limit))
        
        return results
    
    def get_similar_fixes(self, ticket_description: str, component: Optional[str] = None, 
                         limit: int = 3) -> List[Dict]:
        """
        Find similar historical fixes based on ticket description.
        This is a simplified version - in production, you'd use vector embeddings.
        
        Args:
            ticket_description: Description of the current bug
            component: Optional component filter
            limit: Maximum number of results to return
            
        Returns:
            List of similar ticket documents with relevance scores
        """
        # Extract potential keywords from description
        keywords = [word.lower() for word in ticket_description.split() 
                   if len(word) > 4][:5]  # Take first 5 significant words
        
        # Build query
        base_query = {
            "$or": [
                {"title": {"$regex": "|".join(keywords), "$options": "i"}},
                {"description": {"$regex": "|".join(keywords), "$options": "i"}},
                {"tags": {"$in": keywords}}
            ]
        }
        
        # Add component filter if provided
        if component:
            base_query["component"] = component
        
        results = list(self.collection.find(
            base_query,
            {"_id": 0}
        ).limit(limit))
        
        return results
    
    def get_all_components(self) -> List[str]:
        """Get list of all unique components in the database."""
        return self.collection.distinct("component")
    
    def get_all_tags(self) -> List[str]:
        """Get list of all unique tags in the database."""
        return self.collection.distinct("tags")
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        return {
            "total_tickets": self.collection.count_documents({}),
            "components": len(self.collection.distinct("component")),
            "unique_tags": len(self.collection.distinct("tags")),
            "severity_breakdown": self._get_severity_breakdown()
        }
    
    def _get_severity_breakdown(self) -> Dict[str, int]:
        """Get count of tickets by severity."""
        pipeline = [
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
        ]
        results = list(self.collection.aggregate(pipeline))
        return {item['_id']: item['count'] for item in results}
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()


def format_fix_context(tickets: List[Dict]) -> str:
    """
    Format retrieved tickets into a readable context for the LLM.
    
    Args:
        tickets: List of ticket documents
        
    Returns:
        Formatted string containing relevant fix context
    """
    if not tickets:
        return "No relevant historical fixes found."
    
    context_parts = ["=== RELEVANT HISTORICAL FIXES ===\n"]
    
    for i, ticket in enumerate(tickets, 1):
        context_parts.append(f"\n--- Fix #{i}: {ticket['ticket_id']} ---")
        context_parts.append(f"Title: {ticket['title']}")
        context_parts.append(f"Component: {ticket['component']}")
        context_parts.append(f"Severity: {ticket['severity']}")
        context_parts.append(f"Root Cause: {ticket['root_cause']}")
        context_parts.append(f"Solution: {ticket['solution']}")
        
        # Add code change if available
        if 'code_change' in ticket:
            change = ticket['code_change']
            context_parts.append(f"\nCode Change in {change['file']}:")
            context_parts.append(f"  BEFORE: {change['before']}")
            context_parts.append(f"  AFTER:  {change['after']}")
        
        context_parts.append(f"Tags: {', '.join(ticket['tags'])}")
        context_parts.append(f"Resolution Time: {ticket['resolution_time_hours']} hours")
    
    return "\n".join(context_parts)


# Example usage
if __name__ == "__main__":
    rag = RAGQueryEngine()
    
    print("🔍 Testing RAG Query Engine\n")
    
    # Test 1: Search by tags
    print("Test 1: Authentication issues")
    results = rag.search_by_tags(["authentication", "jwt"], limit=2)
    print(format_fix_context(results))
    
    # Test 2: Search by component
    print("\n\nTest 2: Database issues")
    results = rag.search_by_component("database", limit=2)
    for r in results:
        print(f"  • {r['ticket_id']}: {r['title']}")
    
    # Test 3: Get stats
    print("\n\nTest 3: Database statistics")
    stats = rag.get_stats()
    print(f"  Total tickets: {stats['total_tickets']}")
    print(f"  Components: {stats['components']}")
    print(f"  Severity breakdown: {stats['severity_breakdown']}")
    
    rag.close()
    print("\n✅ Tests complete")
