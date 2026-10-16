import { FolderOpen, FolderCheck, Plus, Loader2, AlertCircle } from "lucide-react";
import WorkspaceModal from "./WorkspaceModal.jsx";

export default function WorkspaceSection({
  workspaces,
  activeWorkspaceId,
  isWorkspacesLoading,
  workspacesError,
  onSelectWorkspace,
  isModalOpen,
  onOpenModal,
  onCloseModal,
  onWorkspaceCreated,
}) {
  return (
    <div className="ws-section">
      {/* Section header */}
      <div className="ws-section-header">
        <span className="ws-section-title">Workspaces</span>
        <button
          className="ws-add-btn"
          onClick={onOpenModal}
          title="New Workspace"
          aria-label="Create new workspace"
          id="new-workspace-btn"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Loading */}
      {isWorkspacesLoading && (
        <div className="ws-loading">
          <Loader2 size={14} className="ws-spinner" />
          <span>Loading…</span>
        </div>
      )}

      {/* API Error */}
      {!isWorkspacesLoading && workspacesError && (
        <div className="ws-error-inline" role="alert">
          <AlertCircle size={13} />
          <span>{workspacesError}</span>
        </div>
      )}

      {/* Empty state */}
      {!isWorkspacesLoading && !workspacesError && workspaces.length === 0 && (
        <div className="ws-empty">
          <span>No workspaces yet.</span>
          <button className="ws-empty-cta" onClick={onOpenModal}>
            Create one →
          </button>
        </div>
      )}

      {/* Workspace list */}
      {!isWorkspacesLoading && !workspacesError && workspaces.length > 0 && (
        <ul className="ws-list" role="listbox" aria-label="Workspaces">
          {workspaces.map((ws) => {
            const isActive = ws.id === activeWorkspaceId;
            return (
              <li key={ws.id} role="option" aria-selected={isActive}>
                <button
                  className={`ws-item-btn${isActive ? " active" : ""}`}
                  onClick={() => onSelectWorkspace(ws.id)}
                  title={ws.name}
                >
                  <span className="ws-item-icon">
                    {isActive ? (
                      <FolderCheck size={14} />
                    ) : (
                      <FolderOpen size={14} />
                    )}
                  </span>
                  <span className="ws-item-label">{ws.name}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {/* Create Workspace Modal */}
      <WorkspaceModal
        isOpen={isModalOpen}
        onClose={onCloseModal}
        onCreated={onWorkspaceCreated}
      />
    </div>
  );
}
