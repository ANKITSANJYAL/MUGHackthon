import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

interface CodeChange {
  file_path: string;
  old_code: string;
  new_code: string;
}

interface ApprovalSession {
  session_id: string;
  ticket_key: string;
  ticket_title: string;
  ticket_description: string;
  github_url: string;
  validation_branch: string;
  code_changes: CodeChange[];
  test_results: string;
  ai_summary: string;
  confidence: number;
  status: string;
  created_at: string;
  expires_at: string;
  pr_url?: string;
  pr_number?: number;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const ApprovalPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  
  const [session, setSession] = useState<ApprovalSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);

  useEffect(() => {
    fetchSession();
  }, [sessionId]);

  const fetchSession = async () => {
    try {
      const response = await fetch(`${API_URL}/api/approval/${sessionId}`);
      const data = await response.json();

      if (data.success) {
        setSession(data.session);
      } else {
        setError(data.error || 'Failed to load approval session');
      }
    } catch (err) {
      setError('Network error: Could not connect to backend');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!confirm('Are you sure you want to approve and merge this fix?')) {
      return;
    }

    setApproving(true);
    try {
      const response = await fetch(
        `${API_URL}/api/approval/${sessionId}/approve`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            approved_by: 'developer@example.com'
          })
        }
      );

      const data = await response.json();

      if (data.success) {
        alert(`✅ Success! PR #${data.pr_number} has been merged.\n\nView PR: ${data.pr_url}`);
        fetchSession(); // Refresh to show updated status
      } else {
        alert(`❌ Failed to merge: ${data.error}`);
      }
    } catch (err) {
      alert('Network error: Could not approve fix');
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    const reason = prompt('Please provide a reason for rejection (so the AI can learn from its mistakes):');
    if (!reason) return;

    setRejecting(true);
    try {
      const response = await fetch(
        `${API_URL}/api/approval/${sessionId}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason })
        }
      );

      const data = await response.json();

      if (data.success) {
        // Show the funny rejection message
        alert('🤖💔 AI: "Okay dumbass, go make the update yourself then!"\n\n(Just kidding... thanks for the feedback. The AI will learn from this.)');
        fetchSession(); // Refresh
      } else {
        alert('Failed to reject fix');
      }
    } catch (err) {
      alert('Network error');
    } finally {
      setRejecting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">Loading approval request...</p>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 p-6">
        <div className="bg-red-900/20 border border-red-500 p-8 rounded-lg max-w-md">
          <h2 className="text-red-400 text-xl font-bold mb-2">⚠️ Error</h2>
          <p className="text-slate-300">{error || 'Session not found or expired'}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded transition-colors"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 overflow-y-auto">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-700 p-6 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white mb-1">
                🤖 Code Fix Approval
              </h1>
              <p className="text-slate-400">
                {session.ticket_key}: {session.ticket_title}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <span
                className={`px-3 py-1 rounded text-sm font-semibold ${
                  session.status === 'PENDING_APPROVAL'
                    ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-500'
                    : session.status === 'APPROVED'
                    ? 'bg-green-900/30 text-green-400 border border-green-500'
                    : 'bg-red-900/30 text-red-400 border border-red-500'
                }`}
              >
                {session.status}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Summary Card */}
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-6">
          <h2 className="text-lg font-bold mb-3 text-white">🧠 AI Analysis Summary</h2>
          <div className="max-h-96 overflow-y-auto">
            <p className="text-slate-300 leading-relaxed mb-4 whitespace-pre-wrap">{session.ai_summary}</p>
          </div>
          <div className="flex items-center space-x-6">
            <div className="flex items-center">
              <span className="text-slate-400 text-sm mr-2">Confidence:</span>
              <div className="flex items-center">
                <div className="w-32 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500"
                    style={{ width: `${session.confidence * 100}%` }}
                  ></div>
                </div>
                <span className="ml-2 text-green-400 font-semibold">
                  {(session.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-slate-400 text-sm mr-2">Branch:</span>
              <code className="bg-slate-800 px-2 py-1 rounded text-cyan-400 text-sm">
                {session.validation_branch}
              </code>
            </div>
          </div>
        </div>

        {/* Code Changes */}
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4 text-white">📝 Code Changes</h2>
          <div className="space-y-4">
            {session.code_changes.map((change, idx) => (
              <div key={idx} className="border border-slate-700 rounded-lg overflow-hidden">
                <div className="bg-slate-800 px-4 py-2 border-b border-slate-700">
                  <code className="text-sm text-cyan-400">{change.file_path}</code>
                </div>
                <div className="grid grid-cols-2 divide-x divide-slate-700">
                  <div className="p-4 bg-red-950/20 max-h-96 overflow-y-auto">
                    <div className="text-xs text-red-400 mb-2 font-semibold">- OLD</div>
                    <pre className="text-xs text-slate-300 overflow-x-auto">
                      <code>{change.old_code || '(no old code)'}</code>
                    </pre>
                  </div>
                  <div className="p-4 bg-green-950/20 max-h-96 overflow-y-auto">
                    <div className="text-xs text-green-400 mb-2 font-semibold">+ NEW</div>
                    <pre className="text-xs text-slate-300 overflow-x-auto">
                      <code>{change.new_code || '(no new code)'}</code>
                    </pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Test Results */}
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4 text-white flex items-center">
            <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
            Test Results
          </h2>
          <div className="bg-slate-950 border border-slate-800 rounded p-4 max-h-96 overflow-y-auto">
            <pre className="text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap">
              {session.test_results || 'No test output available'}
            </pre>
          </div>
        </div>

        {/* Approval Actions */}
        {session.status === 'PENDING_APPROVAL' && (
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-6">
            <h2 className="text-lg font-bold mb-4 text-white">⚡ Take Action</h2>
            <div className="flex space-x-4">
              <button
                onClick={handleApprove}
                disabled={approving}
                className="flex-1 bg-green-600 hover:bg-green-500 disabled:bg-green-800 disabled:cursor-not-allowed text-white font-bold py-4 px-6 rounded-lg transition-colors shadow-lg hover:shadow-green-500/50 flex items-center justify-center"
              >
                {approving ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Merging...
                  </>
                ) : (
                  <>
                    ✅ Approve & Merge to Main
                  </>
                )}
              </button>
              <button
                onClick={handleReject}
                disabled={rejecting}
                className="px-6 py-4 border-2 border-red-500 text-red-400 hover:bg-red-950/30 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors font-semibold"
              >
                {rejecting ? 'Rejecting...' : '❌ Reject'}
              </button>
            </div>
          </div>
        )}

        {session.status === 'APPROVED' && session.pr_url && (
          <div className="bg-green-900/20 border border-green-500 rounded-lg p-6 text-center">
            <p className="text-green-400 text-lg font-semibold mb-2">
              ✅ This fix has been approved and merged!
            </p>
            <a
              href={session.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:text-cyan-300 underline"
            >
              View PR #{session.pr_number} on GitHub →
            </a>
          </div>
        )}

        {session.status === 'REJECTED' && (
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-8 text-center">
            <p className="text-red-400 text-2xl font-bold mb-4">
              ❌ This fix was rejected
            </p>
            <div className="text-6xl mb-4">🤖💔</div>
            <p className="text-slate-300 text-lg italic mb-2">
              "Okay dumbass, go make the update yourself then!"
            </p>
            <p className="text-slate-500 text-sm">
              (Just kidding... AI will learn from your feedback 😅)
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

export default ApprovalPage;
