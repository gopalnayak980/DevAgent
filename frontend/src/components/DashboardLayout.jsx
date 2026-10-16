import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

export default function DashboardLayout({
  activeView,
  setActiveView,
  user,
  logout,
  children,
  conversations,
  activeConversationId,
  isConvsLoading,
  onNewChat,
  onSelectConversation,
  // Workspace props
  workspaces,
  activeWorkspaceId,
  isWorkspacesLoading,
  workspacesError,
  onSelectWorkspace,
  isWorkspaceModalOpen,
  onOpenWorkspaceModal,
  onCloseWorkspaceModal,
  onWorkspaceCreated,
}) {
  const activeWorkspace = workspaces?.find((w) => w.id === activeWorkspaceId) || null;

  return (
    <div className="dashboard-layout">
      <Sidebar
        activeView={activeView}
        setActiveView={setActiveView}
        conversations={conversations}
        activeConversationId={activeConversationId}
        isConvsLoading={isConvsLoading}
        onNewChat={onNewChat}
        onSelectConversation={onSelectConversation}
        workspaces={workspaces}
        activeWorkspaceId={activeWorkspaceId}
        isWorkspacesLoading={isWorkspacesLoading}
        workspacesError={workspacesError}
        onSelectWorkspace={onSelectWorkspace}
        isWorkspaceModalOpen={isWorkspaceModalOpen}
        onOpenWorkspaceModal={onOpenWorkspaceModal}
        onCloseWorkspaceModal={onCloseWorkspaceModal}
        onWorkspaceCreated={onWorkspaceCreated}
      />
      <div className="dashboard-main">
        <Topbar
          activeView={activeView}
          user={user}
          logout={logout}
          activeWorkspace={activeWorkspace}
        />
        <div className="dashboard-content">
          {children}
        </div>
      </div>
    </div>
  );
}
