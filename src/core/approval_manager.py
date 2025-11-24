"""
Approval Session Manager

Manages pending approval sessions for validated fixes.
Stores session data in MongoDB with TTL (24 hours).
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from pymongo import MongoClient
import os

logger = logging.getLogger(__name__)


class ApprovalManager:
    """Manages approval sessions for validated fixes."""
    
    def __init__(self):
        """Initialize with MongoDB connection."""
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not set in environment")
        
        self.client = MongoClient(mongodb_uri)
        self.db = self.client['h_kfx']
        self.sessions = self.db['approval_sessions']
        
        # Create indexes
        self._create_indexes()
        logger.info("✅ Approval Manager initialized")
    
    def _create_indexes(self):
        """Create necessary indexes."""
        try:
            # TTL index for auto-expiration
            self.sessions.create_index(
                "expires_at",
                expireAfterSeconds=0,
                background=True
            )
            
            # Unique index on session_id
            self.sessions.create_index(
                "session_id",
                unique=True,
                background=True
            )
            
            # Index on ticket_key for lookups
            self.sessions.create_index("ticket_key", background=True)
            self.sessions.create_index("status", background=True)
            
        except Exception as e:
            logger.warning(f"Failed to create indexes (may already exist): {e}")
    
    def create_session(
        self,
        ticket_key: str,
        ticket_title: str,
        ticket_description: str,
        orchestration_result: Dict[str, Any],
        github_url: str
    ) -> str:
        """
        Create a new approval session.
        
        Args:
            ticket_key: Jira ticket key
            ticket_title: Ticket title
            ticket_description: Ticket description
            orchestration_result: Complete orchestration result
            github_url: GitHub repository URL
        
        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid.uuid4())
        
        validation_result = orchestration_result.get('phase_6_validation', {})
        code_generation = orchestration_result.get('phase_5_code_generation', {})
        ai_analysis = orchestration_result.get('phase_1_analysis', {})
        rag_data = orchestration_result.get('phase_2_rag', {})
        tavily_data = orchestration_result.get('phase_3_tavily', {})
        
        session_doc = {
            'session_id': session_id,
            'ticket_key': ticket_key,
            'ticket_title': ticket_title,
            'ticket_description': ticket_description,
            'github_url': github_url,
            'validation_branch': validation_result.get('validation_branch'),
            'repo_path': validation_result.get('repo_path'),
            'code_changes': code_generation.get('code_changes', []),
            'test_results': validation_result.get('test_output', ''),
            'ai_analysis': ai_analysis,
            'ai_summary': ai_analysis.get('problem_summary', 'N/A'),
            'rag_results': rag_data.get('results', []),
            'tavily_results': tavily_data.get('results', []),
            'confidence': code_generation.get('confidence', 0.0),
            'status': 'PENDING_APPROVAL',
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=24),
            'approved_by': None,
            'approved_at': None,
            'pr_url': None,
            'pr_number': None
        }
        
        try:
            self.sessions.insert_one(session_doc)
            logger.info(f"✅ Created approval session: {session_id} for {ticket_key}")
            return session_id
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve approval session by ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session document or None if not found
        """
        try:
            session = self.sessions.find_one({'session_id': session_id})
            if session:
                session.pop('_id', None)  # Remove MongoDB ID
            return session
        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None
    
    def approve_session(
        self,
        session_id: str,
        approved_by: str = "developer",
        pr_url: str = None,
        pr_number: int = None
    ) -> bool:
        """
        Mark session as approved.
        
        Args:
            session_id: Session identifier
            approved_by: User who approved
            pr_url: GitHub PR URL
            pr_number: GitHub PR number
        
        Returns:
            True if updated successfully
        """
        try:
            update_data = {
                'status': 'APPROVED',
                'approved_by': approved_by,
                'approved_at': datetime.utcnow()
            }
            
            if pr_url:
                update_data['pr_url'] = pr_url
            if pr_number:
                update_data['pr_number'] = pr_number
            
            result = self.sessions.update_one(
                {'session_id': session_id, 'status': 'PENDING_APPROVAL'},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Session {session_id} approved by {approved_by}")
                return True
            else:
                logger.warning(f"⚠️ Session {session_id} not found or already processed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to approve session {session_id}: {e}")
            return False
    
    def reject_session(
        self,
        session_id: str,
        reason: str,
        rejected_by: str = "developer"
    ) -> bool:
        """
        Mark session as rejected.
        
        Args:
            session_id: Session identifier
            reason: Rejection reason
            rejected_by: User who rejected
        
        Returns:
            True if updated successfully
        """
        try:
            result = self.sessions.update_one(
                {'session_id': session_id, 'status': 'PENDING_APPROVAL'},
                {
                    '$set': {
                        'status': 'REJECTED',
                        'rejection_reason': reason,
                        'rejected_by': rejected_by,
                        'rejected_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Session {session_id} rejected by {rejected_by}")
                return True
            else:
                logger.warning(f"⚠️ Session {session_id} not found or already processed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to reject session {session_id}: {e}")
            return False
    
    def get_pending_sessions(self, ticket_key: str = None) -> list:
        """Get all pending approval sessions, optionally filtered by ticket."""
        query = {'status': 'PENDING_APPROVAL'}
        if ticket_key:
            query['ticket_key'] = ticket_key
        
        try:
            sessions = list(self.sessions.find(query))
            for session in sessions:
                session.pop('_id', None)
            return sessions
        except Exception as e:
            logger.error(f"❌ Failed to get pending sessions: {e}")
            return []
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("🔌 Approval Manager closed")


# Singleton instance
_approval_manager_instance = None

def get_approval_manager() -> ApprovalManager:
    """Get or create the global ApprovalManager instance."""
    global _approval_manager_instance
    if _approval_manager_instance is None:
        _approval_manager_instance = ApprovalManager()
    return _approval_manager_instance
