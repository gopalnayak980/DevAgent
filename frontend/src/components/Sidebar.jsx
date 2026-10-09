import { Home, MessageSquare, Zap, ShieldCheck, BrainCircuit, Activity, Settings, Plus, MessageCircle } from "lucide-react";

export default function Sidebar({
  activeView,
  setActiveView,
  conversations = [],
  activeConversationId,
  isConvsLoading,
  onNewChat,
  onSelectConversation,
}) {
  const navItems = [
    { id: "home", label: "Dashboard", icon: <Home size={20} /> },
    { id: "chat", label: "Chat", icon: <MessageSquare size={20} /> },
    { id: "jobs", label: "Background Jobs", icon: <Zap size={20} /> },
    { id: "approvals", label: "Approvals", icon: <ShieldCheck size={20} /> },
    { id: "memory", label: "Memory", icon: <BrainCircuit size={20} /> },
    { id: "observability", label: "Observability", icon: <Activity size={20} /> },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">D</div>
        <div className="sidebar-brand">
          <h2>DevAgent</h2>
          <span>AI Assistant</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`sidebar-nav-btn ${activeView === item.id && item.id !== "chat" ? "active" : ""} ${activeView === "chat" && item.id === "chat" && !activeConversationId ? "active" : ""}`}
            onClick={() => setActiveView(item.id)}
            title={item.label}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            <span className="sidebar-nav-label">{item.label}</span>
          </button>
        ))}

        {/* Conversation History — only shown when there are conversations or loading */}
        {(conversations.length > 0 || isConvsLoading) && (
          <div className="conv-history-section">
            <div className="conv-history-header">
              <span className="conv-history-title">Recent Chats</span>
            </div>

            {isConvsLoading ? (
              <div className="conv-history-loading">Loading…</div>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  className={`conv-history-btn ${activeConversationId === conv.id ? "active" : ""}`}
                  onClick={() => onSelectConversation(conv.id)}
                  title={conv.title}
                >
                  <span className="conv-history-icon">
                    <MessageCircle size={14} />
                  </span>
                  <span className="conv-history-label">
                    {conv.title || "New Conversation"}
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        {/* New Chat button */}
        <button
          id="new-chat-btn"
          className="new-chat-btn"
          onClick={onNewChat}
          title="New Chat"
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>
        <button
          className="sidebar-nav-btn"
          onClick={() => setActiveView("settings")}
          title="Settings"
        >
          <span className="sidebar-nav-icon"><Settings size={20} /></span>
          <span className="sidebar-nav-label">Settings</span>
        </button>
      </div>
    </aside>
  );
}
