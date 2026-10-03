import { useState, useEffect, useCallback } from "react";
import { Activity, RefreshCw } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function Observability() {
  const [stats, setStats] = useState(null);
  const [traces, setTraces] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, tracesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/observability/stats`),
        fetch(`${API_BASE_URL}/api/observability/traces`),
      ]);

      if (!statsRes.ok || !tracesRes.ok) {
        throw new Error("Failed to fetch observability data.");
      }

      const statsData = await statsRes.json();
      const tracesData = await tracesRes.json();

      setStats(statsData);
      setTraces(tracesData.traces || []);
    } catch (err) {
      setError(err.message || "Failed to load observability data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const statusColor = (status) => {
    switch (status) {
      case "completed": return "var(--color-success)";
      case "failed": return "var(--color-error)";
      case "running": return "var(--color-accent)";
      default: return "var(--color-text-secondary)";
    }
  };

  const formatDuration = (ms) => {
    if (ms == null) return "—";
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatTime = (isoStr) => {
    if (!isoStr) return "—";
    const d = new Date(isoStr);
    return d.toLocaleString();
  };

  return (
    <div className="obs-panel">
      <div className="obs-header" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <Activity size={24} color="var(--color-accent)" />
        <h3 style={{ margin: 0, flex: 1 }}>Observability</h3>
        <button
          className="obs-refresh-btn"
          onClick={fetchData}
          disabled={loading}
          title="Refresh data"
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {error && (
        <div className="obs-error">⚠️ {error}</div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="obs-stats-grid">
          <div className="obs-stat-card">
            <div className="obs-stat-value">{stats.total_executions}</div>
            <div className="obs-stat-label">Total Executions</div>
          </div>
          <div className="obs-stat-card obs-stat-success">
            <div className="obs-stat-value">{stats.successful_executions}</div>
            <div className="obs-stat-label">Successful</div>
          </div>
          <div className="obs-stat-card obs-stat-failed">
            <div className="obs-stat-value">{stats.failed_executions}</div>
            <div className="obs-stat-label">Failed</div>
          </div>
          <div className="obs-stat-card">
            <div className="obs-stat-value">
              {formatDuration(stats.average_duration_ms)}
            </div>
            <div className="obs-stat-label">Avg Duration</div>
          </div>
          <div className="obs-stat-card">
            <div className="obs-stat-value">{stats.total_llm_calls}</div>
            <div className="obs-stat-label">LLM Calls</div>
          </div>
          <div className="obs-stat-card">
            <div className="obs-stat-value">{stats.total_tool_calls}</div>
            <div className="obs-stat-label">Tool Calls</div>
          </div>
        </div>
      )}

      {/* Recent Traces */}
      <div className="obs-traces-section">
        <h4 className="obs-traces-title">Recent Traces</h4>
        {traces.length === 0 && !loading && (
          <div className="obs-empty">No execution traces recorded yet.</div>
        )}
        <div className="obs-traces-list">
          {traces.map((trace) => (
            <div key={trace.id} className="obs-trace-card">
              <div className="obs-trace-header">
                <span className="obs-trace-id" title={trace.id}>
                  {trace.id.substring(0, 8)}…
                </span>
                <span
                  className="obs-trace-status"
                  style={{ color: statusColor(trace.status) }}
                >
                  <span className="obs-status-dot" style={{ background: statusColor(trace.status) }}></span>
                  {trace.status}
                </span>
              </div>
              <div className="obs-trace-details">
                <div className="obs-trace-field">
                  <span className="obs-field-label">Agent</span>
                  <span className="obs-field-value">{trace.agent_name || "—"}</span>
                </div>
                <div className="obs-trace-field">
                  <span className="obs-field-label">Intent</span>
                  <span className="obs-field-value">{trace.task_type || "—"}</span>
                </div>
                <div className="obs-trace-field">
                  <span className="obs-field-label">Complexity</span>
                  <span className="obs-field-value">{trace.complexity || "—"}</span>
                </div>
                <div className="obs-trace-field">
                  <span className="obs-field-label">Duration</span>
                  <span className="obs-field-value">{formatDuration(trace.duration_ms)}</span>
                </div>
                <div className="obs-trace-field">
                  <span className="obs-field-label">LLM Calls</span>
                  <span className="obs-field-value">{trace.llm_call_count}</span>
                </div>
                <div className="obs-trace-field">
                  <span className="obs-field-label">Tools</span>
                  <span className="obs-field-value">
                    {trace.tools_used && trace.tools_used.length > 0
                      ? trace.tools_used.join(", ")
                      : "—"}
                  </span>
                </div>
              </div>
              {trace.error_message && (
                <div className="obs-trace-error">⚠️ {trace.error_message}</div>
              )}
              <div className="obs-trace-time">{formatTime(trace.created_at)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
