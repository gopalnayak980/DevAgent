import { Home, MessageSquare, Zap, ShieldCheck, BrainCircuit, Activity, Settings } from "lucide-react";

export default function Sidebar({ activeView, setActiveView }) {
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
            className={`sidebar-nav-btn ${activeView === item.id ? "active" : ""}`}
            onClick={() => setActiveView(item.id)}
            title={item.label}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            <span className="sidebar-nav-label">{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
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
