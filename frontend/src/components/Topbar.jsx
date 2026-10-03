import { useTheme } from "../contexts/ThemeContext.jsx";
import { Moon, Sun, LogOut } from "lucide-react";

export default function Topbar({ activeView, user, logout }) {
  const { theme, toggleTheme } = useTheme();
  const getViewTitle = () => {
    switch (activeView) {
      case "home": return "Dashboard Overview";
      case "chat": return "AI Chat";
      case "jobs": return "Background Jobs";
      case "approvals": return "Approval Requests";
      case "memory": return "Persistent Memory";
      case "observability": return "Observability Traces";
      case "settings": return "Settings";
      default: return "Dashboard";
    }
  };

  return (
    <header className="topbar">
      <h2 className="topbar-title">{getViewTitle()}</h2>
      <div className="topbar-actions" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-lg)' }}>
        <button 
          onClick={toggleTheme} 
          className="btn-icon" 
          title="Toggle Theme"
          style={{ background: 'transparent', border: 'none', color: 'var(--color-text-secondary)', cursor: 'pointer' }}
        >
          {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
        </button>
        <div className="topbar-user" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div className="user-avatar">{user?.name ? user.name[0].toUpperCase() : 'U'}</div>
          <span className="user-name">{user?.name || "Developer"}</span>
        </div>
        {logout && (
          <button 
            onClick={logout} 
            className="btn-icon" 
            title="Logout"
            style={{ background: 'transparent', border: 'none', color: 'var(--color-text-secondary)', cursor: 'pointer' }}
          >
            <LogOut size={20} />
          </button>
        )}
      </div>
    </header>
  );
}
