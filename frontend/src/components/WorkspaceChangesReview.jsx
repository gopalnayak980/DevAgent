import { useState, useEffect, useCallback, useMemo } from "react";
import {
  GitCommit,
  Check,
  X,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  FileCode,
  Shield,
  Loader2,
  Filter,
} from "lucide-react";

/**
 * Format ISO datetime string nicely.
 */
function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) +
      " " + d.toLocaleDateString([], { month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

/**
 * Parse and render unified diff with line-by-line styling.
 */
function DiffViewer({ diffText, filePath }) {
  if (!diffText || !diffText.trim()) {
    return (
      <div className="wcr-diff-empty">
        <span>No visible differences found.</span>
      </div>
    );
  }

  const lines = diffText.split("\n");

  return (
    <div className="wcr-diff-container">
      <div className="wcr-diff-table">
        {lines.map((line, idx) => {
          let lineType = "context";
          if (line.startsWith("---") || line.startsWith("+++")) {
            lineType = "header";
          } else if (line.startsWith("@@")) {
            lineType = "chunk";
          } else if (line.startsWith("-")) {
            lineType = "deletion";
          } else if (line.startsWith("+")) {
            lineType = "addition";
          }

          return (
            <div key={idx} className={`wcr-diff-row wcr-diff-${lineType}`}>
              <span className="wcr-diff-lineno">{idx + 1}</span>
              <span className="wcr-diff-prefix">
                {lineType === "addition" ? "+" : lineType === "deletion" ? "-" : " "}
              </span>
              <span className="wcr-diff-text">{line}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function WorkspaceChangesReview({
  workspace,
  authFetch,
  onPendingCountChange,
}) {
  const [proposals, setProposals] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedProposalId, setSelectedProposalId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  // Fetch proposals
  const fetchProposals = useCallback(async () => {
    if (!workspace?.id) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/api/workspaces/${workspace.id}/changes`);
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to load proposals (${res.status})`);
      }
      const data = await res.json();
      const list = data.proposals || [];
      setProposals(list);

      // Report pending count
      const pendingCount = list.filter((p) => p.status === "pending").length;
      if (onPendingCountChange) {
        onPendingCountChange(pendingCount);
      }

      // Default select the first proposal if none selected
      setSelectedProposalId((prev) => {
        if (prev && list.some((p) => p.id === prev)) return prev;
        return list.length > 0 ? list[0].id : null;
      });
    } catch (err) {
      setError(err.message || "Failed to load proposals.");
    } finally {
      setIsLoading(false);
    }
  }, [workspace?.id, authFetch, onPendingCountChange]);

  // Load on mount and when workspace changes
  useEffect(() => {
    fetchProposals();
  }, [fetchProposals]);

  // Filtered proposals
  const filteredProposals = useMemo(() => {
    if (statusFilter === "all") return proposals;
    return proposals.filter((p) => p.status === statusFilter);
  }, [proposals, statusFilter]);

  // Selected proposal
  const selectedProposal = useMemo(() => {
    return proposals.find((p) => p.id === selectedProposalId) || null;
  }, [proposals, selectedProposalId]);

  // Handle Approve
  const handleApprove = async (proposalId) => {
    if (!workspace?.id || actionLoading) return;
    setActionLoading(true);
    setActionMessage(null);
    try {
      const res = await authFetch(
        `/api/workspaces/${workspace.id}/changes/${proposalId}/approve`,
        { method: "POST" }
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to approve proposal (${res.status})`);
      }
      const updated = await res.json();
      setActionMessage({
        type: "success",
        text: `Proposal approved and applied to ${updated.file_path}!`,
      });
      // Refresh list
      await fetchProposals();
    } catch (err) {
      setActionMessage({
        type: "error",
        text: err.message || "Failed to approve proposal.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Reject
  const handleReject = async (proposalId) => {
    if (!workspace?.id || actionLoading) return;
    setActionLoading(true);
    setActionMessage(null);
    try {
      const res = await authFetch(
        `/api/workspaces/${workspace.id}/changes/${proposalId}/reject`,
        { method: "POST" }
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to reject proposal (${res.status})`);
      }
      const updated = await res.json();
      setActionMessage({
        type: "info",
        text: `Proposal for ${updated.file_path} rejected. File unchanged.`,
      });
      // Refresh list
      await fetchProposals();
    } catch (err) {
      setActionMessage({
        type: "error",
        text: err.message || "Failed to reject proposal.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "pending":
        return <span className="wcr-badge pending">Pending Review</span>;
      case "applied":
        return <span className="wcr-badge applied">Applied</span>;
      case "rejected":
        return <span className="wcr-badge rejected">Rejected</span>;
      case "failed":
        return <span className="wcr-badge failed">Failed / Stale</span>;
      default:
        return <span className="wcr-badge">{status}</span>;
    }
  };

  return (
    <div className="workspace-changes-review">
      <div className="wcr-split-layout">
        {/* Left Side: Proposal List */}
        <div className="wcr-list-pane">
          <div className="wcr-list-header">
            <div className="wcr-title-row">
              <span className="wcr-list-title">Proposed Changes</span>
              <span className="wcr-count-pill">{proposals.length}</span>
            </div>
            <button
              className="wcr-btn-icon"
              onClick={fetchProposals}
              disabled={isLoading}
              title="Refresh proposals"
            >
              <RefreshCw size={13} className={isLoading ? "wcr-spin" : ""} />
            </button>
          </div>

          {/* Filter Bar */}
          <div className="wcr-filter-bar">
            {["all", "pending", "applied", "rejected"].map((st) => (
              <button
                key={st}
                className={`wcr-filter-btn ${statusFilter === st ? "active" : ""}`}
                onClick={() => setStatusFilter(st)}
              >
                {st.charAt(0).toUpperCase() + st.slice(1)}
              </button>
            ))}
          </div>

          {/* Proposals List */}
          <div className="wcr-list-body">
            {isLoading && proposals.length === 0 ? (
              <div className="wcr-state-box">
                <Loader2 size={16} className="wcr-spin" />
                <span>Loading proposals...</span>
              </div>
            ) : error ? (
              <div className="wcr-state-box error">
                <AlertCircle size={16} />
                <span>{error}</span>
                <button className="wcr-retry-btn" onClick={fetchProposals}>
                  Retry
                </button>
              </div>
            ) : filteredProposals.length === 0 ? (
              <div className="wcr-state-box empty">
                <span>No {statusFilter !== "all" ? statusFilter : ""} proposals found.</span>
              </div>
            ) : (
              filteredProposals.map((p) => {
                const isSelected = selectedProposalId === p.id;
                return (
                  <button
                    key={p.id}
                    className={`wcr-item-card ${isSelected ? "active" : ""}`}
                    onClick={() => {
                      setSelectedProposalId(p.id);
                      setActionMessage(null);
                    }}
                  >
                    <div className="wcr-item-top">
                      <FileCode size={14} className="wcr-item-icon" />
                      <span className="wcr-item-path" title={p.file_path}>
                        {p.file_path}
                      </span>
                    </div>
                    <div className="wcr-item-meta">
                      {getStatusBadge(p.status)}
                      <span className="wcr-item-time">{formatDate(p.created_at)}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Diff & Approval Actions */}
        <div className="wcr-diff-pane">
          {selectedProposal ? (
            <div className="wcr-diff-content">
              {/* Header */}
              <div className="wcr-diff-header">
                <div className="wcr-diff-header-left">
                  <div className="wcr-diff-file-title">
                    <FileCode size={16} />
                    <span className="wcr-diff-filename">{selectedProposal.file_path}</span>
                    {getStatusBadge(selectedProposal.status)}
                  </div>
                  <div className="wcr-diff-submeta">
                    <span>Created: {formatDate(selectedProposal.created_at)}</span>
                    {selectedProposal.applied_at && (
                      <span> • Applied: {formatDate(selectedProposal.applied_at)}</span>
                    )}
                    {selectedProposal.rejected_at && (
                      <span> • Rejected: {formatDate(selectedProposal.rejected_at)}</span>
                    )}
                  </div>
                </div>

                {/* Action Buttons for Pending Proposals */}
                {selectedProposal.status === "pending" && (
                  <div className="wcr-diff-actions">
                    <button
                      className="wcr-btn-reject"
                      onClick={() => handleReject(selectedProposal.id)}
                      disabled={actionLoading}
                    >
                      <X size={14} />
                      <span>Reject</span>
                    </button>
                    <button
                      className="wcr-btn-approve"
                      onClick={() => handleApprove(selectedProposal.id)}
                      disabled={actionLoading}
                    >
                      {actionLoading ? (
                        <Loader2 size={14} className="wcr-spin" />
                      ) : (
                        <Check size={14} />
                      )}
                      <span>Approve & Apply</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Action Banner (Success or Error) */}
              {actionMessage && (
                <div className={`wcr-action-banner ${actionMessage.type}`}>
                  {actionMessage.type === "success" ? (
                    <CheckCircle2 size={15} />
                  ) : (
                    <AlertCircle size={15} />
                  )}
                  <span>{actionMessage.text}</span>
                </div>
              )}

              {/* Diff Viewer Body */}
              <div className="wcr-diff-body">
                <DiffViewer
                  diffText={selectedProposal.diff}
                  filePath={selectedProposal.file_path}
                />
              </div>

              {/* Security & Hash Info Footer */}
              <div className="wcr-diff-footer">
                <div className="wcr-hash-tag">
                  <span className="wcr-hash-label">Orig SHA-256:</span>
                  <code title={selectedProposal.original_content_hash}>
                    {selectedProposal.original_content_hash.substring(0, 12)}…
                  </code>
                </div>
                <div className="wcr-hash-tag">
                  <span className="wcr-hash-label">Prop SHA-256:</span>
                  <code title={selectedProposal.proposed_content_hash}>
                    {selectedProposal.proposed_content_hash.substring(0, 12)}…
                  </code>
                </div>
                <div className="wcr-security-pill">
                  <Shield size={12} />
                  <span>Stale-hash protected & atomic write</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="wcr-placeholder">
              <div className="wcr-placeholder-icon">
                <GitCommit size={40} />
              </div>
              <h4 className="wcr-placeholder-title">Select a Proposal to Review</h4>
              <p className="wcr-placeholder-desc">
                Review proposed file modifications, inspect exact unified diffs, and approve
                or reject changes with complete safety.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
