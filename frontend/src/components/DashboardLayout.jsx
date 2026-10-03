import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

export default function DashboardLayout({ activeView, setActiveView, children }) {
  return (
    <div className="dashboard-layout">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      <div className="dashboard-main">
        <Topbar activeView={activeView} />
        <div className="dashboard-content">
          {children}
        </div>
      </div>
    </div>
  );
}
