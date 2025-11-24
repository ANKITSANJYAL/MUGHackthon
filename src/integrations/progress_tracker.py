"""
Real-time Progress Tracker for Orchestrator Pipeline

Broadcasts pipeline progress to frontend via Server-Sent Events (SSE).
Tracks which phase the orchestrator is currently executing.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List
from flask import Blueprint, Response, stream_with_context, jsonify
from queue import Queue, Empty
import threading

logger = logging.getLogger(__name__)

# Global progress tracker instance
_progress_tracker = None

class ProgressTracker:
    """Tracks and broadcasts orchestrator pipeline progress."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.active_tickets: Dict[str, Dict[str, Any]] = {}
        self.subscribers: List[Queue] = []
        self.lock = threading.Lock()
        logger.info("✅ ProgressTracker initialized")
    
    def start_ticket(self, ticket_key: str, ticket_data: Dict[str, Any]) -> None:
        """
        Mark ticket processing as started.
        
        Args:
            ticket_key: Jira ticket key (e.g., "PROJ-123")
            ticket_data: Initial ticket data
        """
        with self.lock:
            self.active_tickets[ticket_key] = {
                'ticket_key': ticket_key,
                'status': 'STARTED',
                'current_phase': 0,
                'phases': [
                    {'id': 1, 'name': 'AI Analysis', 'status': 'pending'},
                    {'id': 2, 'name': 'RAG Search', 'status': 'pending'},
                    {'id': 3, 'name': 'Tavily Search', 'status': 'pending'},
                    {'id': 4, 'name': 'Code Generation', 'status': 'pending'},
                    {'id': 5, 'name': 'Code Validation', 'status': 'pending'},
                    {'id': 6, 'name': 'Reflection', 'status': 'pending'},
                    {'id': 7, 'name': 'Jira Update', 'status': 'pending'},
                ],
                'started_at': time.time(),
                'updated_at': time.time(),
                **ticket_data
            }
        
        self._broadcast({
            'event': 'ticket_started',
            'ticket_key': ticket_key,
            'data': self.active_tickets[ticket_key]
        })
        
        logger.info(f"📊 Tracking started for {ticket_key}")
    
    def update_phase(self, ticket_key: str, phase_id: int, status: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the status of a specific phase.
        
        Args:
            ticket_key: Jira ticket key
            phase_id: Phase number (1-7)
            status: 'active', 'completed', 'error'
            data: Additional phase data
        """
        with self.lock:
            if ticket_key not in self.active_tickets:
                logger.warning(f"⚠️ Ticket {ticket_key} not found in tracker")
                return
            
            ticket = self.active_tickets[ticket_key]
            
            # Update phase status
            for phase in ticket['phases']:
                if phase['id'] == phase_id:
                    phase['status'] = status
                    if data:
                        phase['data'] = data
                    break
            
            # Update current phase
            if status == 'active':
                ticket['current_phase'] = phase_id
            
            ticket['updated_at'] = time.time()
        
        self._broadcast({
            'event': 'phase_update',
            'ticket_key': ticket_key,
            'phase_id': phase_id,
            'status': status,
            'data': data or {}
        })
        
        logger.info(f"📊 {ticket_key} - Phase {phase_id} -> {status}")
    
    def complete_ticket(self, ticket_key: str, result: Dict[str, Any]) -> None:
        """
        Mark ticket processing as complete.
        
        Args:
            ticket_key: Jira ticket key
            result: Final orchestration result
        """
        with self.lock:
            if ticket_key not in self.active_tickets:
                logger.warning(f"⚠️ Ticket {ticket_key} not found in tracker")
                return
            
            ticket = self.active_tickets[ticket_key]
            ticket['status'] = 'COMPLETED'
            ticket['current_phase'] = 7
            ticket['result'] = result
            ticket['completed_at'] = time.time()
        
        self._broadcast({
            'event': 'ticket_completed',
            'ticket_key': ticket_key,
            'result': result
        })
        
        logger.info(f"✅ Tracking completed for {ticket_key}")
    
    def error_ticket(self, ticket_key: str, error: str, phase_id: Optional[int] = None) -> None:
        """
        Mark ticket processing as errored.
        
        Args:
            ticket_key: Jira ticket key
            error: Error message
            phase_id: Phase where error occurred (optional)
        """
        with self.lock:
            if ticket_key not in self.active_tickets:
                logger.warning(f"⚠️ Ticket {ticket_key} not found in tracker")
                return
            
            ticket = self.active_tickets[ticket_key]
            ticket['status'] = 'ERROR'
            ticket['error'] = error
            
            if phase_id:
                for phase in ticket['phases']:
                    if phase['id'] == phase_id:
                        phase['status'] = 'error'
                        break
        
        self._broadcast({
            'event': 'ticket_error',
            'ticket_key': ticket_key,
            'error': error,
            'phase_id': phase_id
        })
        
        logger.error(f"❌ Error tracking {ticket_key}: {error}")
    
    def get_ticket_status(self, ticket_key: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a ticket.
        
        Args:
            ticket_key: Jira ticket key
        
        Returns:
            Ticket status dict or None if not found
        """
        with self.lock:
            return self.active_tickets.get(ticket_key)
    
    def subscribe(self) -> Queue:
        """
        Subscribe to progress updates.
        
        Returns:
            Queue that will receive progress events
        """
        queue = Queue(maxsize=100)
        with self.lock:
            self.subscribers.append(queue)
        logger.info(f"📡 New subscriber added (total: {len(self.subscribers)})")
        return queue
    
    def unsubscribe(self, queue: Queue) -> None:
        """
        Unsubscribe from progress updates.
        
        Args:
            queue: Queue to remove from subscribers
        """
        with self.lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)
        logger.info(f"📡 Subscriber removed (remaining: {len(self.subscribers)})")
    
    def _broadcast(self, event: Dict[str, Any]) -> None:
        """
        Broadcast event to all subscribers.
        
        Args:
            event: Event data to broadcast
        """
        dead_queues = []
        
        for queue in self.subscribers:
            try:
                queue.put_nowait(event)
            except:
                dead_queues.append(queue)
        
        # Clean up dead queues
        if dead_queues:
            with self.lock:
                for queue in dead_queues:
                    if queue in self.subscribers:
                        self.subscribers.remove(queue)
            logger.info(f"🧹 Cleaned up {len(dead_queues)} dead subscribers")


# Blueprint for SSE endpoints
progress_bp = Blueprint('progress', __name__, url_prefix='/api/progress')


@progress_bp.route('/stream')
def stream():
    """
    Server-Sent Events endpoint for real-time progress updates.
    
    Frontend connects to this endpoint to receive live pipeline updates.
    """
    tracker = get_progress_tracker()
    queue = tracker.subscribe()
    
    def generate():
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'event': 'connected'})}\n\n"
            
            # Send current active tickets
            with tracker.lock:
                active_tickets = dict(tracker.active_tickets)
            
            if active_tickets:
                yield f"data: {json.dumps({'event': 'initial_state', 'tickets': active_tickets})}\n\n"
            
            # Stream updates
            while True:
                try:
                    event = queue.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except Empty:
                    # Send keepalive every 30 seconds
                    yield f"data: {json.dumps({'event': 'keepalive'})}\n\n"
        except GeneratorExit:
            tracker.unsubscribe(queue)
            logger.info("📡 Client disconnected from SSE stream")
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@progress_bp.route('/status/<ticket_key>')
def get_status(ticket_key: str):
    """
    Get current status of a specific ticket.
    
    Args:
        ticket_key: Jira ticket key
    
    Returns:
        JSON with ticket status
    """
    tracker = get_progress_tracker()
    status = tracker.get_ticket_status(ticket_key)
    
    if status:
        return jsonify({'success': True, 'status': status})
    else:
        return jsonify({'success': False, 'error': 'Ticket not found'}), 404


@progress_bp.route('/health')
def health():
    """Health check endpoint."""
    tracker = get_progress_tracker()
    return jsonify({
        'status': 'healthy',
        'active_tickets': len(tracker.active_tickets),
        'subscribers': len(tracker.subscribers)
    })


def get_progress_tracker() -> ProgressTracker:
    """Get or create the global progress tracker instance."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker
