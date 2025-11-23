"""
RAG (Retrieval-Augmented Generation) Module

This module provides database setup and query capabilities for historical bug fix retrieval.
"""

from .query_engine import RAGQueryEngine, format_fix_context

__all__ = ['RAGQueryEngine', 'format_fix_context']
__version__ = '0.1.0'
