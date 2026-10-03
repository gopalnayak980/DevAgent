import { useState, useEffect, useCallback } from "react";
import { Shield, RefreshCw } from "lucide-react";
import { useAuth } from "../contexts/AuthContext.jsx";

export default function ApprovalsPanel() {
  const { authFetch } = useAuth();
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await authFetch(`/api/approvals`);
      if (!response.ok) {
        throw new Error("Failed to fetch approvals.");
      }
      const data = await response.json();
      setApprovals(data.approvals || []);
    } catch (err) {
      setError(err.message || "An error occurred while loading approvals.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleAction = async (approvalId, action) => {
    setActionLoading(approvalId);
    try {
      const response = await authFetch(`/api/approvals/${approvalId}/${action}`, {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Failed to ${action} request.`);
      }
      
      // Refresh list
      await fetchApprovals();
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status) => {
    let className = "approval-badge ";
    switch (status) {
      case "pending": className += "badge-warning"; break;
      case "approved": className += "badge-success"; break;
      case "rejected": className += "badge-error"; break;
      case "cancelled": className += "badge-default"; break;
      default: className += "badge-default";
    }
    return <span className={className}>{status}</span>;
  };

  return (
    <div className="approvals-panel">
      <div className="approvals-header">
        <div className="approvals-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Shield size={24} color="var(--color-accent)" />
          <h3>Approval Requests</h3>
        </div>
        <button
          className="btn-refresh"
          onClick={fetchApprovals}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {error && <div className="panel-error">⚠️ {error}</div>}

      <div className="approvals-list-container">
        {approvals.length === 0 && !loading ? (
          <div className="panel-empty">No approval requests found.</div>
        ) : (
          <div className="approvals-list">
            {approvals.map((approval) => (
              <div key={approval.id} className="approval-card">
                <div className="approval-card-header">
                  <span className="approval-id">ID: {approval.id.substring(0, 8)}...</span>
                  {getStatusBadge(approval.status)}
                </div>
                <div className="approval-content">
                  <h4>{approval.action_type}</h4>
                  <p>{approval.description}</p>
                  <div className="approval-meta">
                    Created: {new Date(approval.created_at).toLocaleString()}
                    {approval.resolved_at && ` • Resolved: ${new Date(approval.resolved_at).toLocaleString()}`}
                  </div>
                </div>
                {approval.status === "pending" && (
                  <div className="approval-actions">
                    <button
                      className="btn-approve"
                      disabled={actionLoading === approval.id}
                      onClick={() => handleAction(approval.id, "approve")}
                    >
                      {actionLoading === approval.id ? "Processing..." : "Approve"}
                    </button>
                    <button
                      className="btn-reject"
                      disabled={actionLoading === approval.id}
                      onClick={() => handleAction(approval.id, "reject")}
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
