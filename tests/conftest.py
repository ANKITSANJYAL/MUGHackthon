"""
Test configuration and fixtures for H-KFX
"""

import pytest
import os
import sys
from pathlib import Path

# Add src to path for all tests
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_ticket_data():
    """Sample ticket data for testing"""
    return {
        'ticket_number': 'TEST-100',
        'title': 'NullPointerException in authentication service',
        'description': '''
            Stack trace:
            File "auth_service.py", line 45, in validate_token
            TypeError: 'NoneType' object is not subscriptable
            
            Repository: https://github.com/test/myapp.git
        '''
    }


@pytest.fixture
def sample_rag_document():
    """Sample RAG document structure"""
    return {
        'source_id': 'JIRA-4501',
        'ticket_summary': 'Fixed token generation missing org prefix',
        'project_module': 'user_auth',
        'internal_context': 'Added organization prefix to security hash...',
        'fix_type': 'Logic',
        'gold_patch_snippet': 'hash_key = f"org_{org_id}_{user_token}"'
    }


@pytest.fixture
def mock_mongodb_connection(monkeypatch):
    """Mock MongoDB connection for testing"""
    class MockCollection:
        def insert_many(self, docs):
            return type('obj', (object,), {'inserted_ids': list(range(len(docs)))})
        
        def aggregate(self, pipeline):
            return []
        
        def find(self, query):
            return []
    
    class MockDB:
        def __getitem__(self, collection_name):
            return MockCollection()
    
    class MockClient:
        def __getitem__(self, db_name):
            return MockDB()
        
        def close(self):
            pass
        
        @property
        def admin(self):
            return type('obj', (object,), {
                'command': lambda self, cmd: {'ok': 1}
            })()
    
    return MockClient()


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI client for testing"""
    class MockMessage:
        content = "Test AI response"
    
    class MockChoice:
        message = MockMessage()
    
    class MockResponse:
        choices = [MockChoice()]
    
    class MockCompletions:
        def create(self, **kwargs):
            return MockResponse()
    
    class MockChat:
        completions = MockCompletions()
    
    class MockOpenAI:
        chat = MockChat()
    
    return MockOpenAI()


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables"""
    test_env = {
        'MONGODB_URI': 'mongodb://localhost:27017/test',
        'MONGODB_DB_NAME': 'test_db',
        'MONGODB_COLLECTION_NAME': 'test_collection',
        'OPENAI_API_KEY': 'test-key-123',
        'OPENAI_MODEL': 'gpt-4o-mini',
        'JIRA_BASE': 'https://test.atlassian.net',
        'JIRA_EMAIL': 'test@example.com',
        'JIRA_API_TOKEN': 'test-token',
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
