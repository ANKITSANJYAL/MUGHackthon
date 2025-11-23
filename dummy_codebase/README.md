"""
Dummy Codebase - Simulating a real production application

This codebase contains intentional bugs that will be fixed by the JIAE agent
using RAG context from historical fixes.

## Structure:
- services/: Business logic services with bugs
- config/: Configuration files with incorrect settings
- tests/: Test files that expose the bugs

## Known Issues (for demo):
1. auth_service.py - Missing organization prefix in token hashing
2. activity_service.py - Missing database indexes causing slow queries  
3. api_config.py - Using wrong port (8080 instead of 8081) per AD-204
"""
