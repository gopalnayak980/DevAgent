import { useTheme } from "../contexts/ThemeContext.jsx";
import { Moon, Sun } from "lucide-react";

export default function Topbar({ activeView }) {
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
        <div className="topbar-user">
          <div className="user-avatar">U</div>
          <span className="user-name">Developer</span>
        </div>
      </div>
    </header>
  );
}
