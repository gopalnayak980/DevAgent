import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

export default function DashboardLayout({ activeView, setActiveView, user, logout, children }) {
  return (
    <div className="dashboard-layout">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      <div className="dashboard-main">
        <Topbar activeView={activeView} user={user} logout={logout} />
        <div className="dashboard-content">
          {children}
        </div>
      </div>
    </div>
  );
}
