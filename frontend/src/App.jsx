import { useState, useCallback } from "react";
import "./dashboard.css";
import DashboardLayout from "./components/DashboardLayout.jsx";
import DashboardHome from "./components/DashboardHome.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import ChatInput from "./components/ChatInput.jsx";
import BackgroundJobs from "./components/BackgroundJobs.jsx";
import Observability from "./components/Observability.jsx";
import ApprovalsPanel from "./components/ApprovalsPanel.jsx";
import MemoryPanel from "./components/MemoryPanel.jsx";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [activeView, setActiveView] = useState("home"); // "home" | "chat" | "jobs" | "approvals" | "memory" | "observability" | "settings"

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isChatLoading) return;

      const userMessage = { role: "user", content: text.trim() };
      setMessages((prev) => [...prev, userMessage]);
      setChatError(null);
      setIsChatLoading(true);

      try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text.trim() }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(
            errorData?.detail ||
              `Request failed with status ${response.status}`
          );
        }

        const data = await response.json();

        if (!data.response) {
          throw new Error("Received an empty response from the server.");
        }

        const aiMessage = { 
          role: "assistant", 
          content: data.response,
          requiresApproval: data.requires_approval,
          approval: data.approval
        };
        setMessages((prev) => [...prev, aiMessage]);
      } catch (err) {
        if (err.name === "TypeError" && err.message === "Failed to fetch") {
          setChatError(
            "Unable to connect to the server. Please make sure the backend is running."
          );
        } else {
          setChatError(err.message || "Something went wrong. Please try again.");
        }
      } finally {
        setIsChatLoading(false);
      }
    },
    [isChatLoading]
  );

  const handleApprovalAction = useCallback(
    async (approvalId, action) => {
      setIsChatLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/api/approvals/${approvalId}/${action}`, {
          method: "POST",
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(
            errorData?.detail ||
              `Request failed with status ${response.status}`
          );
        }

        const data = await response.json();
        
        const resultMessage = { role: "assistant", content: `Approval ${action}d: ${data.message}` };
        setMessages((prev) => {
           const updatedMessages = prev.map(msg => 
             msg.approval?.id === approvalId ? { ...msg, requiresApproval: false } : msg
           );
           return [...updatedMessages, resultMessage];
        });

      } catch (err) {
        setChatError(err.message || "Approval action failed. Please try again.");
      } finally {
        setIsChatLoading(false);
      }
    },
    []
  );

  const handleHintClick = useCallback(
    (text) => {
      sendMessage(text);
    },
    [sendMessage]
  );

  const renderActiveView = () => {
    switch (activeView) {
      case "home":
        return <DashboardHome setActiveView={setActiveView} />;
      case "chat":
        return (
          <div className="chat-view">
            <ChatWindow
              messages={messages}
              isLoading={isChatLoading}
              error={chatError}
              onHintClick={handleHintClick}
              onApprovalAction={handleApprovalAction}
            />
            <ChatInput onSend={sendMessage} isLoading={isChatLoading} />
          </div>
        );
      case "jobs":
        return <BackgroundJobs />;
      case "approvals":
        return <ApprovalsPanel />;
      case "memory":
        return <MemoryPanel />;
      case "observability":
        return <Observability />;
      case "settings":
        return (
          <div className="settings-panel">
            <h3>Settings</h3>
            <p>Settings configuration will be available in a future update.</p>
          </div>
        );
      default:
        return <DashboardHome setActiveView={setActiveView} />;
    }
  };

  return (
    <DashboardLayout activeView={activeView} setActiveView={setActiveView}>
      {renderActiveView()}
    </DashboardLayout>
  );
}
