"""
User Activity Query Service

Handles user activity logs and analytics queries.
"""

from typing import List, Dict
from datetime import datetime


def get_user_recent_activity(user_id: str, limit: int = 50) -> List[Dict]:
    """
    Retrieves recent user activity logs.
    
    BUG: This query causes a full collection scan!
    Missing the compound index on (user_id, timestamp) per PERF-901
    
    Args:
        user_id: The user's ID
        limit: Maximum number of activities to return
        
    Returns:
        List of activity log entries
    """
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['user_data']
    
    # BUG: This query is slow - no proper index!
    # Should have compound index: {'user_id': 1, 'timestamp': -1}
    activities = list(db.activity_logs.find(
        {'user_id': user_id}
    ).sort('timestamp', -1).limit(limit))
    
    return activities


def get_trending_users(timeframe_hours: int = 24) -> List[Dict]:
    """
    Gets most active users in the given timeframe.
    
    Args:
        timeframe_hours: Hours to look back
        
    Returns:
        List of user activity summaries
    """
    # BUG: Another slow query without proper indexes
    from pymongo import MongoClient
    import os
    from datetime import timedelta
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['user_data']
    
    cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
    
    # This aggregation is slow without indexes
    pipeline = [
        {'$match': {'timestamp': {'$gte': cutoff_time}}},
        {'$group': {'_id': '$user_id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    
    return list(db.activity_logs.aggregate(pipeline))
