import { useState, useEffect, useCallback } from "react";
import { X, FolderOpen, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext.jsx";

export default function WorkspaceModal({ isOpen, onClose, onCreated }) {
  const { authFetch } = useAuth();
  const [name, setName] = useState("");
  const [rootPath, setRootPath] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setName("");
      setRootPath("");
      setError(null);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e) => {
      if (e.key === "Escape" && !isSubmitting) onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, isSubmitting, onClose]);

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();

      const trimmedName = name.trim();
      const trimmedPath = rootPath.trim();

      if (!trimmedName) {
        setError("Workspace name is required.");
        return;
      }
      if (!trimmedPath) {
        setError("Project path is required.");
        return;
      }
      if (isSubmitting) return;

      setError(null);
      setIsSubmitting(true);

      try {
        const res = await authFetch("/api/workspaces", {
          method: "POST",
          body: JSON.stringify({ name: trimmedName, root_path: trimmedPath }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => null);
          if (res.status === 409) {
            throw new Error(
              `A workspace named "${trimmedName}" already exists.`
            );
          } else if (res.status === 400) {
            throw new Error(
              data?.detail ||
                "Invalid workspace path. Path traversal is not allowed."
            );
          } else if (res.status === 401) {
            throw new Error("Your session has expired. Please log in again.");
          } else {
            throw new Error(
              data?.detail || `Request failed (${res.status}).`
            );
          }
        }

        const workspace = await res.json();
        onCreated(workspace);
        onClose();
      } catch (err) {
        if (err.name === "TypeError" && err.message === "Failed to fetch") {
          setError("Unable to connect to the server.");
        } else {
          setError(err.message || "Something went wrong. Please try again.");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [name, rootPath, isSubmitting, authFetch, onCreated, onClose]
  );

  if (!isOpen) return null;

  return (
    <div
      className="ws-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSubmitting) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="ws-modal-title"
    >
      <div className="ws-modal">
        {/* Header */}
        <div className="ws-modal-header">
          <div className="ws-modal-title-row">
            <FolderOpen size={20} style={{ color: "var(--color-accent)" }} />
            <h3 id="ws-modal-title" className="ws-modal-title">
              New Workspace
            </h3>
          </div>
          <button
            className="ws-modal-close"
            onClick={onClose}
            disabled={isSubmitting}
            title="Close"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="ws-modal-form" noValidate>
          <div className="ws-form-field">
            <label htmlFor="ws-name" className="ws-form-label">
              Workspace Name
            </label>
            <input
              id="ws-name"
              type="text"
              className="ws-form-input"
              placeholder='e.g. "My React Project"'
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (error) setError(null);
              }}
              disabled={isSubmitting}
              autoFocus
              maxLength={120}
              autoComplete="off"
            />
          </div>

          <div className="ws-form-field">
            <label htmlFor="ws-path" className="ws-form-label">
              Project Path
              <span className="ws-form-hint">
                Relative path within the workspace root
              </span>
            </label>
            <input
              id="ws-path"
              type="text"
              className="ws-form-input"
              placeholder='e.g. "projects/my-react-project"'
              value={rootPath}
              onChange={(e) => {
                setRootPath(e.target.value);
                if (error) setError(null);
              }}
              disabled={isSubmitting}
              maxLength={500}
              autoComplete="off"
            />
          </div>

          {error && (
            <div className="ws-modal-error" role="alert">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          <div className="ws-modal-actions">
            <button
              type="button"
              className="ws-btn-cancel"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ws-btn-create"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={14} className="ws-spinner" />
                  Creating…
                </>
              ) : (
                "Create Workspace"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
