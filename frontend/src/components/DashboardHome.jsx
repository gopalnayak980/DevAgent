import { useState, useEffect, useCallback } from "react";
import { Activity, CheckCircle, XCircle, Clock, ShieldAlert, ChevronRight } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function DashboardHome({ setActiveView }) {
  const [stats, setStats] = useState(null);
  const [recentJobs, setRecentJobs] = useState([]);
  const [recentApprovals, setRecentApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOverviewData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch observability stats, recent jobs, and approvals concurrently
      const [statsRes, jobsRes, approvalsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/observability/stats`),
        fetch(`${API_BASE_URL}/api/jobs`),
        fetch(`${API_BASE_URL}/api/approvals`),
      ]);

      if (!statsRes.ok || !jobsRes.ok || !approvalsRes.ok) {
        throw new Error("Failed to fetch dashboard data.");
      }

      const statsData = await statsRes.json();
      const jobsData = await jobsRes.json();
      const approvalsData = await approvalsRes.json();

      setStats(statsData);
      setRecentJobs(jobsData.jobs ? jobsData.jobs.slice(0, 3) : []);
      setRecentApprovals(approvalsData.approvals ? approvalsData.approvals.slice(0, 3) : []);
    } catch (err) {
      setError(err.message || "Failed to load overview data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverviewData();
  }, [fetchOverviewData]);

  const formatDuration = (ms) => {
    if (ms == null) return "—";
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getStatusClass = (status) => {
    if (!status) return "";
    switch (status.toLowerCase()) {
      case "completed":
      case "approved":
        return "status-success";
      case "failed":
      case "rejected":
        return "status-error";
      case "running":
      case "pending":
        return "status-warning";
      default:
        return "status-default";
    }
  };

  if (loading) {
    return (
      <div className="dashboard-home">
        <div className="dashboard-summary-grid">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="summary-card skeleton" style={{ height: '120px', background: 'var(--color-bg-secondary)', opacity: 0.5, animation: 'pulse 2s infinite' }}></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="dashboard-error">⚠️ {error}</div>;
  }

  const pendingApprovalsCount = recentApprovals.filter(a => a.status === "pending").length;

  return (
    <div className="dashboard-home">
      <div className="dashboard-summary-grid">
        <div className="summary-card" onClick={() => setActiveView("observability")}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)' }}>
            <div className="summary-label">Total Executions</div>
            <Activity size={20} color="var(--color-text-secondary)" />
          </div>
          <div className="summary-value">{stats?.total_executions || 0}</div>
        </div>
        <div className="summary-card success" onClick={() => setActiveView("observability")}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)' }}>
            <div className="summary-label">Successful</div>
            <CheckCircle size={20} color="var(--color-success)" />
          </div>
          <div className="summary-value">{stats?.successful_executions || 0}</div>
        </div>
        <div className="summary-card error" onClick={() => setActiveView("observability")}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)' }}>
            <div className="summary-label">Failed</div>
            <XCircle size={20} color="var(--color-error)" />
          </div>
          <div className="summary-value">{stats?.failed_executions || 0}</div>
        </div>
        <div className="summary-card" onClick={() => setActiveView("observability")}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)' }}>
            <div className="summary-label">Avg Duration</div>
            <Clock size={20} color="var(--color-text-secondary)" />
          </div>
          <div className="summary-value">{formatDuration(stats?.average_duration_ms)}</div>
        </div>
        <div className="summary-card warning" onClick={() => setActiveView("approvals")}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)' }}>
            <div className="summary-label">Pending Approvals</div>
            <ShieldAlert size={20} color="#fbbf24" />
          </div>
          <div className="summary-value">{pendingApprovalsCount}</div>
        </div>
      </div>

      <div className="dashboard-recent-grid">
        <div className="recent-section">
          <div className="recent-header">
            <h3>Recent Jobs</h3>
            <button className="btn-link" onClick={() => setActiveView("jobs")}>View All</button>
          </div>
          {recentJobs.length === 0 ? (
            <div className="recent-empty">No background jobs found.</div>
          ) : (
            <ul className="recent-list">
              {recentJobs.map(job => (
                <li key={job.id} className="recent-item">
                  <div className="recent-item-main">
                    <span className="recent-item-title">{job.input.substring(0, 40)}{job.input.length > 40 ? "..." : ""}</span>
                    <span className={`recent-item-status ${getStatusClass(job.status)}`}>{job.status}</span>
                  </div>
                  <div className="recent-item-meta">
                    {new Date(job.created_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="recent-section">
          <div className="recent-header">
            <h3>Recent Approvals</h3>
            <button className="btn-link" onClick={() => setActiveView("approvals")}>View All</button>
          </div>
          {recentApprovals.length === 0 ? (
            <div className="recent-empty">No approval requests found.</div>
          ) : (
            <ul className="recent-list">
              {recentApprovals.map(approval => (
                <li key={approval.id} className="recent-item">
                  <div className="recent-item-main">
                    <span className="recent-item-title">{approval.description.substring(0, 40)}{approval.description.length > 40 ? "..." : ""}</span>
                    <span className={`recent-item-status ${getStatusClass(approval.status)}`}>{approval.status}</span>
                  </div>
                  <div className="recent-item-meta">
                    {new Date(approval.created_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
