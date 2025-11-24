"""
RAG Query Engine with Vector Semantic Search

Provides semantic search over historical fixes using MongoDB Atlas Vector Search.
"""

import os
from typing import List, Dict, Optional
from pymongo import MongoClient
from dotenv import load_dotenv
from openai import OpenAI


class RAGQueryEngine:
    """Query engine for vector-based semantic search over historical fixes."""
    
    def __init__(self):
        """Initialize connections."""
        load_dotenv()
        
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'JIAE_Knowledge_Base')
        self.collection_name = os.getenv('MONGODB_COLLECTION_NAME', 'PastFixes')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        
        self.openai_client = OpenAI(api_key=openai_key)
        self.embedding_model = "text-embedding-3-small"
    
    def generate_query_embedding(self, query_text: str) -> List[float]:
        """Generate embedding for search query."""
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=query_text
        )
        return response.data[0].embedding
    
    def semantic_search(
        self, 
        query: str, 
        limit: int = 3,
        module_filter: Optional[str] = None,
        fix_type_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Perform semantic vector search on historical fixes.
        
        Args:
            query: Natural language query describing the bug
            limit: Maximum number of results
            module_filter: Optional filter by project_module
            fix_type_filter: Optional filter by fix_type
            
        Returns:
            List of relevant fix documents with similarity scores
        """
        # Generate query embedding
        query_vector = self.generate_query_embedding(query)
        
        # Build vector search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 50,
                    "limit": limit
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "source_id": 1,
                    "ticket_summary": 1,
                    "project_module": 1,
                    "internal_context": 1,
                    "fix_type": 1,
                    "gold_patch_snippet": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        # Add filters if specified
        if module_filter or fix_type_filter:
            filter_stage = {"$match": {}}
            if module_filter:
                filter_stage["$match"]["project_module"] = module_filter
            if fix_type_filter:
                filter_stage["$match"]["fix_type"] = fix_type_filter
            pipeline.insert(1, filter_stage)
        
        results = list(self.collection.aggregate(pipeline))
        return results
    
    def keyword_search(
        self, 
        keywords: List[str], 
        module: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Perform keyword-based search (fallback when vector search unavailable).
        
        Args:
            keywords: List of keywords to search
            module: Optional module filter
            limit: Maximum results
            
        Returns:
            List of matching documents
        """
        query = {}
        
        if module:
            query["project_module"] = module
        
        if keywords:
            query["$or"] = [
                {"ticket_summary": {"$regex": "|".join(keywords), "$options": "i"}},
                {"internal_context": {"$regex": "|".join(keywords), "$options": "i"}}
            ]
        
        results = list(self.collection.find(
            query,
            {"_id": 0}
        ).limit(limit))
        
        return results
    
    def get_by_module(self, module: str, limit: int = 5) -> List[Dict]:
        """Get all fixes for a specific module."""
        return list(self.collection.find(
            {"project_module": module},
            {"_id": 0}
        ).limit(limit))
    
    def get_by_fix_type(self, fix_type: str, limit: int = 5) -> List[Dict]:
        """Get all fixes of a specific type."""
        return list(self.collection.find(
            {"fix_type": fix_type},
            {"_id": 0}
        ).limit(limit))
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()


def format_rag_context(results: List[Dict]) -> str:
    """
    Format RAG results into context for LLM.
    
    Args:
        results: List of fix documents from semantic search
        
    Returns:
        Formatted context string
    """
    if not results:
        return "No relevant historical fixes found in RAG database."
    
    context_parts = ["=== RELEVANT HISTORICAL FIXES FROM INTERNAL RAG ===\n"]
    
    for i, doc in enumerate(results, 1):
        score = doc.get('score', 0)
        context_parts.append(f"\n--- Fix #{i} (Similarity: {score:.3f}) ---")
        context_parts.append(f"Source: {doc['source_id']}")
        context_parts.append(f"Module: {doc['project_module']}")
        context_parts.append(f"Type: {doc['fix_type']}")
        context_parts.append(f"Summary: {doc['ticket_summary']}")
        context_parts.append(f"\nContext:\n{doc['internal_context']}")
        context_parts.append(f"\nReference Code:\n{doc['gold_patch_snippet']}")
        context_parts.append("-" * 60)
    
    return "\n".join(context_parts)


# Demo usage
if __name__ == "__main__":
    rag = RAGQueryEngine()
    
    print("🔍 Testing RAG Query Engine\n")
    print("=" * 80)
    
    # Test 1: Semantic search for auth issue
    print("\n1️⃣  Semantic Search: Token authentication failing for multi-tenant users")
    print("-" * 80)
    query = "Users from different organizations getting wrong authentication results, token hashing issue"
    results = rag.semantic_search(query, limit=2, module_filter="user_auth")
    print(format_rag_context(results))
    
    # Test 2: Semantic search for performance issue
    print("\n2️⃣  Semantic Search: Slow database queries on user activity")
    print("-" * 80)
    query = "Query taking too long to get user recent activity, timeout on database"
    results = rag.semantic_search(query, limit=2, module_filter="db_query_optimization")
    print(format_rag_context(results))
    
    # Test 3: Semantic search for config issue
    print("\n3️⃣  Semantic Search: Internal API calls timing out")
    print("-" * 80)
    query = "Service to service communication failing with timeout, connection refused"
    results = rag.semantic_search(query, limit=2, module_filter="api_gateway")
    print(format_rag_context(results))
    
    rag.close()
    print("\n✅ RAG query tests complete")
