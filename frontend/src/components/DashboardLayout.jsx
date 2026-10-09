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
}) {
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
      />
      <div className="dashboard-main">
        <Topbar activeView={activeView} user={user} logout={logout} />
        <div className="dashboard-content">
          {children}
        </div>
      </div>
    </div>
  );
}
