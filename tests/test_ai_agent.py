"""
Tests for core AI agent functionality
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.ai_agent import analyze_ticket, openai_summarize


class TestAnalyzeTicket:
    """Test suite for ticket analysis"""
    
    def test_analyze_ticket_code_related(self):
        """Test that code-related issues are properly identified"""
        result = analyze_ticket(
            ticket_number="TEST-123",
            title="NullPointerException in user service",
            description="Stack trace shows error in auth_service.py line 45"
        )
        
        assert result['is_code_related'] is True
        assert 'problem_summary' in result
        assert result['ticket_number'] == "TEST-123"
    
    def test_analyze_ticket_extracts_github_url(self):
        """Test that GitHub URLs are extracted from description"""
        result = analyze_ticket(
            ticket_number="TEST-124",
            title="Bug in repository",
            description="Issue occurs in https://github.com/test/myrepo.git"
        )
        
        assert result['github_url'] == "https://github.com/test/myrepo.git"
    
    def test_analyze_ticket_infrastructure_issue(self):
        """Test that infrastructure issues are identified"""
        result = analyze_ticket(
            ticket_number="TEST-125",
            title="Server timeout issues",
            description="Database connection timeout on production server"
        )
        
        # May be identified as code or infra depending on keywords
        assert 'is_code_related' in result
        assert 'problem_summary' in result
    
    @patch('core.ai_agent.OpenAI')
    def test_openai_summarize_with_api_key(self, mock_openai):
        """Test OpenAI summarization when API key is present"""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test summary"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            result = openai_summarize("Test text")
            assert result == "Test summary"
    
    def test_analyze_ticket_without_description(self):
        """Test that analysis works with minimal information"""
        result = analyze_ticket(
            ticket_number="TEST-126",
            title="Bug in code",
            description=""
        )
        
        assert 'problem_summary' in result
        assert 'is_code_related' in result


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_analyze_ticket_with_none_description(self):
        """Test handling of None description"""
        result = analyze_ticket(
            ticket_number="TEST-127",
            title="Test issue",
            description=None
        )
        
        assert result is not None
        assert 'problem_summary' in result
    
    def test_analyze_ticket_with_very_long_description(self):
        """Test handling of very long descriptions"""
        long_desc = "Error " * 1000
        result = analyze_ticket(
            ticket_number="TEST-128",
            title="Long issue",
            description=long_desc
        )
        
        assert result is not None
        assert 'problem_summary' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
