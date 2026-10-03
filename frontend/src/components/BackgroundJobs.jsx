import { useState, useCallback, useEffect, useRef } from "react";
import { Zap, Clock, Play, CheckCircle2, XCircle, Ban, AlertCircle } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const STATUS_CONFIG = {
  pending: { label: "Pending", color: "var(--color-text-secondary)", icon: <Clock size={16} /> },
  running: { label: "Running", color: "var(--color-accent)", icon: <Play size={16} /> },
  completed: { label: "Completed", color: "var(--color-success)", icon: <CheckCircle2 size={16} /> },
  failed: { label: "Failed", color: "var(--color-error)", icon: <XCircle size={16} /> },
  cancelled: { label: "Cancelled", color: "var(--color-text-secondary)", icon: <Ban size={16} /> },
};

export default function BackgroundJobs() {
  const [taskInput, setTaskInput] = useState("");
  const [currentJob, setCurrentJob] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  // Poll for job status when a job is active
  useEffect(() => {
    if (
      currentJob &&
      (currentJob.status === "pending" || currentJob.status === "running")
    ) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/api/jobs/${currentJob.job_id}`);
          if (res.ok) {
            const data = await res.json();
            setCurrentJob(data);
            if (
              data.status === "completed" ||
              data.status === "failed" ||
              data.status === "cancelled"
            ) {
              clearInterval(pollRef.current);
            }
          }
        } catch {
          // Silently continue polling
        }
      }, 2000);

      return () => clearInterval(pollRef.current);
    }
  }, [currentJob?.job_id, currentJob?.status]);

  const submitJob = useCallback(async () => {
    if (!taskInput.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    setCurrentJob(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: taskInput.trim() }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || `Request failed (${res.status})`);
      }

      const data = await res.json();
      setCurrentJob({ job_id: data.job_id, status: data.status });
      setTaskInput("");
    } catch (err) {
      if (err.name === "TypeError" && err.message === "Failed to fetch") {
        setError("Unable to connect to the server.");
      } else {
        setError(err.message || "Something went wrong.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [taskInput, isSubmitting]);

  const cancelJob = useCallback(async () => {
    if (!currentJob) return;
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/jobs/${currentJob.job_id}/cancel`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        setCurrentJob((prev) => ({ ...prev, status: data.status }));
      }
    } catch {
      // Ignore cancel errors
    }
  }, [currentJob]);

  const statusConfig = currentJob ? STATUS_CONFIG[currentJob.status] || {} : {};

  return (
    <div className="bg-panel">
      <div className="bg-panel-header" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <Zap size={24} color="var(--color-accent)" />
        <h3 style={{ margin: 0 }}>Background Agent Task</h3>
      </div>

      <div className="bg-input-group">
        <textarea
          className="bg-textarea"
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          placeholder="Describe a task for the agent to process in the background..."
          rows={3}
          disabled={isSubmitting}
        />
        <button
          className="bg-submit-btn"
          onClick={submitJob}
          disabled={!taskInput.trim() || isSubmitting}
        >
          {isSubmitting ? "Submitting..." : "Start Background Task"}
        </button>
      </div>

      {error && (
        <div className="bg-error" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {currentJob && (
        <div className="bg-job-card">
          <div className="bg-job-header">
            <span className="bg-job-id">Job: {currentJob.job_id.slice(0, 8)}…</span>
            <span className="bg-job-status" style={{ color: statusConfig.color, display: 'flex', alignItems: 'center', gap: '4px' }}>
              {statusConfig.icon} {statusConfig.label}
              {(currentJob.status === "pending" || currentJob.status === "running") && (
                <span className="bg-status-pulse" />
              )}
            </span>
          </div>

          {currentJob.input && (
            <div className="bg-job-input">
              <strong>Task:</strong> {currentJob.input}
            </div>
          )}

          {currentJob.status === "completed" && currentJob.result && (
            <div className="bg-job-result">
              <strong>Result:</strong>
              <div className="bg-result-content">
                {currentJob.result.split("\n").map((line, i) => (
                  <p key={i}>{line || "\u00A0"}</p>
                ))}
              </div>
            </div>
          )}

          {currentJob.status === "failed" && currentJob.error && (
            <div className="bg-job-error">
              <strong>Error:</strong> {currentJob.error}
            </div>
          )}

          {currentJob.status === "pending" && (
            <button className="bg-cancel-btn" onClick={cancelJob}>
              Cancel Job
            </button>
          )}
        </div>
      )}
    </div>
  );
}
