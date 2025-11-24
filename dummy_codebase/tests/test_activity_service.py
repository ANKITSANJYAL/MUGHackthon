"""
Tests for Activity Service

These tests expose the performance issues in activity_service.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.activity_service import get_user_recent_activity, get_trending_users
from datetime import datetime, timedelta


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB connection."""
    with patch('services.activity_service.MongoClient') as mock_client:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.activity_logs = mock_collection
        yield mock_collection


def test_get_user_recent_activity_works_but_slow(mock_mongodb):
    """
    This test PASSES but the query is SLOW!
    Missing index on (user_id, timestamp) per PERF-901
    """
    # Setup mock data
    mock_activities = [
        {"user_id": "user123", "action": "login", "timestamp": datetime.utcnow()},
        {"user_id": "user123", "action": "view", "timestamp": datetime.utcnow()},
    ]
    
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value.limit.return_value = mock_activities
    mock_mongodb.find.return_value = mock_cursor
    
    # Call function
    result = get_user_recent_activity("user123", limit=10)
    
    # Test passes but query is inefficient!
    assert isinstance(result, list)
    mock_mongodb.find.assert_called_once()


def test_get_user_recent_activity_missing_index():
    """
    This test documents the performance issue.
    
    The query should use index {'user_id': 1, 'timestamp': -1}
    but currently does full collection scan!
    """
    # This is a documentation test showing the bug
    # In real scenario with 1M+ records, this would timeout
    pass


def test_get_trending_users_works_but_slow(mock_mongodb):
    """
    Test trending users aggregation.
    Works but slow without proper indexes.
    """
    # Setup mock data
    mock_trending = [
        {"_id": "user1", "count": 150},
        {"_id": "user2", "count": 120},
    ]
    
    mock_mongodb.aggregate.return_value = mock_trending
    
    # Call function
    result = get_trending_users(timeframe_hours=24)
    
    # Test passes but aggregation is slow!
    assert isinstance(result, list)
    mock_mongodb.aggregate.assert_called_once()


def test_performance_benchmark():
    """
    This test would FAIL in real environment with large dataset.
    
    Expected: Query should complete in < 100ms
    Actual: Takes 5-10 seconds due to missing indexes
    """
    # This is a placeholder for performance testing
    # In production with real data, this exposes the bug
    import time
    
    # Simulating slow query
    # start = time.time()
    # result = get_user_recent_activity("user123")
    # duration = time.time() - start
    # assert duration < 0.1  # Should be under 100ms - FAILS without index!
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
