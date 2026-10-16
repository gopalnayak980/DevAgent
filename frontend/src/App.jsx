import { useState, useCallback, useEffect } from "react";
import "./dashboard.css";
import DashboardLayout from "./components/DashboardLayout.jsx";
import DashboardHome from "./components/DashboardHome.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import ChatInput from "./components/ChatInput.jsx";
import BackgroundJobs from "./components/BackgroundJobs.jsx";
import Observability from "./components/Observability.jsx";
import ApprovalsPanel from "./components/ApprovalsPanel.jsx";
import MemoryPanel from "./components/MemoryPanel.jsx";
import AuthPage from "./components/AuthPage.jsx";
import WorkspaceFileExplorer from "./components/WorkspaceFileExplorer.jsx";
import { FolderOpen, MessageSquare, FileCode, Columns } from "lucide-react";
import { useAuth } from "./contexts/AuthContext.jsx";

export default function App() {
  const { user, isLoading: isAuthLoading, authFetch, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [activeView, setActiveView] = useState("home");

  // Conversation state
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [isConvsLoading, setIsConvsLoading] = useState(false);

  // Workspace state
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null);
  const [isWorkspacesLoading, setIsWorkspacesLoading] = useState(false);
  const [workspacesError, setWorkspacesError] = useState(null);
  const [isWorkspaceModalOpen, setIsWorkspaceModalOpen] = useState(false);
  const [chatWorkspaceMode, setChatWorkspaceMode] = useState("split");

  // Fetch conversation list from backend
  const fetchConversations = useCallback(async () => {
    if (!user) return;
    setIsConvsLoading(true);
    try {
      const res = await authFetch("/api/conversations");
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setIsConvsLoading(false);
    }
  }, [user, authFetch]);

  // Load conversations when the user is authenticated
  useEffect(() => {
    if (user) {
      fetchConversations();
    }
  }, [user, fetchConversations]);

  // Fetch workspace list from backend
  const fetchWorkspaces = useCallback(async () => {
    if (!user) return;
    setIsWorkspacesLoading(true);
    setWorkspacesError(null);
    try {
      const res = await authFetch("/api/workspaces");
      if (res.ok) {
        const data = await res.json();
        setWorkspaces(data.workspaces || []);
      } else if (res.status === 401) {
        setWorkspacesError("Session expired. Please log in again.");
      } else {
        setWorkspacesError("Failed to load workspaces.");
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
      setWorkspacesError("Unable to connect to the server.");
    } finally {
      setIsWorkspacesLoading(false);
    }
  }, [user, authFetch]);

  // Load workspaces when the user is authenticated
  useEffect(() => {
    if (user) {
      fetchWorkspaces();
    }
  }, [user, fetchWorkspaces]);

  const handleWorkspaceCreated = useCallback((newWorkspace) => {
    setWorkspaces((prev) => [newWorkspace, ...prev]);
    setActiveWorkspaceId(newWorkspace.id);
    setActiveView("chat");
  }, []);

  const handleSelectWorkspace = useCallback((wsId) => {
    setActiveWorkspaceId((prev) => (prev === wsId ? null : wsId));
    setActiveView("chat");
  }, []);

  // Load messages for a selected conversation
  const loadConversation = useCallback(
    async (convId) => {
      setActiveConversationId(convId);
      setActiveView("chat");
      setChatError(null);
      setMessages([]);
      setIsChatLoading(true);
      try {
        const res = await authFetch(`/api/conversations/${convId}/messages`);
        if (res.ok) {
          const data = await res.json();
          // Map backend message shape to frontend shape
          setMessages(
            data.map((m) => ({ role: m.role, content: m.content, id: m.id }))
          );
        } else {
          setChatError("Failed to load conversation messages.");
        }
      } catch (err) {
        setChatError("Failed to load conversation messages.");
      } finally {
        setIsChatLoading(false);
      }
    },
    [authFetch]
  );

  // New Chat — clear state, don't create backend conversation yet
  const handleNewChat = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    setChatError(null);
    setActiveView("chat");
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isChatLoading) return;

      const userMessage = { role: "user", content: text.trim() };
      setMessages((prev) => [...prev, userMessage]);
      setChatError(null);
      setIsChatLoading(true);

      try {
        const body = { message: text.trim() };
        // If we have an active conversation, send it so the backend continues it
        if (activeConversationId) {
          body.conversation_id = activeConversationId;
        }

        const response = await authFetch(`/api/chat`, {
          method: "POST",
          body: JSON.stringify(body),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(
            errorData?.detail || `Request failed with status ${response.status}`
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
          approval: data.approval,
        };
        setMessages((prev) => [...prev, aiMessage]);

        // Save the active conversation_id returned by the backend
        if (data.conversation_id) {
          const isNewConversation = !activeConversationId;
          setActiveConversationId(data.conversation_id);

          // Refresh conversation list when a brand-new conversation is created
          if (isNewConversation) {
            await fetchConversations();
          }
        }
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
    [isChatLoading, activeConversationId, authFetch, fetchConversations]
  );

  const handleApprovalAction = useCallback(
    async (approvalId, action) => {
      setIsChatLoading(true);
      try {
        const response = await authFetch(
          `/api/approvals/${approvalId}/${action}`,
          { method: "POST" }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => null);
          throw new Error(
            errorData?.detail || `Request failed with status ${response.status}`
          );
        }

        const data = await response.json();
        const resultMessage = {
          role: "assistant",
          content: `Approval ${action}d: ${data.message}`,
        };
        setMessages((prev) => {
          const updatedMessages = prev.map((msg) =>
            msg.approval?.id === approvalId
              ? { ...msg, requiresApproval: false }
              : msg
          );
          return [...updatedMessages, resultMessage];
        });
      } catch (err) {
        setChatError(err.message || "Approval action failed. Please try again.");
      } finally {
        setIsChatLoading(false);
      }
    },
    [authFetch]
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
      case "chat": {
        const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) || null;
        return (
          <div className="chat-view">
            {activeWorkspace && (
              <div className="chat-workspace-header">
                <div className="chat-ws-title">
                  <FolderOpen size={15} />
                  <span>
                    Workspace: <strong>{activeWorkspace.name}</strong>
                  </span>
                </div>
                <div className="chat-ws-mode-tabs" role="tablist" aria-label="Workspace view modes">
                  <button
                    className={`chat-ws-tab-btn ${chatWorkspaceMode === "chat" ? "active" : ""}`}
                    onClick={() => setChatWorkspaceMode("chat")}
                    title="Full Chat view"
                    role="tab"
                    aria-selected={chatWorkspaceMode === "chat"}
                  >
                    <MessageSquare size={13} />
                    <span>Chat</span>
                  </button>
                  <button
                    className={`chat-ws-tab-btn ${chatWorkspaceMode === "files" ? "active" : ""}`}
                    onClick={() => setChatWorkspaceMode("files")}
                    title="Full Files & Code view"
                    role="tab"
                    aria-selected={chatWorkspaceMode === "files"}
                  >
                    <FileCode size={13} />
                    <span>Files & Code</span>
                  </button>
                  <button
                    className={`chat-ws-tab-btn ${chatWorkspaceMode === "split" ? "active" : ""}`}
                    onClick={() => setChatWorkspaceMode("split")}
                    title="Side-by-side Split view"
                    role="tab"
                    aria-selected={chatWorkspaceMode === "split"}
                  >
                    <Columns size={13} />
                    <span>Split View</span>
                  </button>
                </div>
              </div>
            )}

            <div className={`chat-workspace-body ${activeWorkspace ? `mode-${chatWorkspaceMode}` : ""}`}>
              {(chatWorkspaceMode === "chat" || chatWorkspaceMode === "split" || !activeWorkspace) && (
                <div className="chat-main-column">
                  <ChatWindow
                    messages={messages}
                    isLoading={isChatLoading}
                    error={chatError}
                    onHintClick={handleHintClick}
                    onApprovalAction={handleApprovalAction}
                    activeWorkspace={activeWorkspace}
                  />
                  <ChatInput onSend={sendMessage} isLoading={isChatLoading} />
                </div>
              )}

              {activeWorkspace && (chatWorkspaceMode === "files" || chatWorkspaceMode === "split") && (
                <div className="chat-explorer-column">
                  <WorkspaceFileExplorer workspace={activeWorkspace} authFetch={authFetch} />
                </div>
              )}
            </div>
          </div>
        );
      }
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

  if (isAuthLoading) {
    return (
      <div
        style={{
          display: "flex",
          height: "100vh",
          justifyContent: "center",
          alignItems: "center",
          color: "var(--text-primary)",
        }}
      >
        Loading...
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <DashboardLayout
      activeView={activeView}
      setActiveView={setActiveView}
      user={user}
      logout={logout}
      conversations={conversations}
      activeConversationId={activeConversationId}
      isConvsLoading={isConvsLoading}
      onNewChat={handleNewChat}
      onSelectConversation={loadConversation}
      workspaces={workspaces}
      activeWorkspaceId={activeWorkspaceId}
      isWorkspacesLoading={isWorkspacesLoading}
      workspacesError={workspacesError}
      onSelectWorkspace={handleSelectWorkspace}
      isWorkspaceModalOpen={isWorkspaceModalOpen}
      onOpenWorkspaceModal={() => setIsWorkspaceModalOpen(true)}
      onCloseWorkspaceModal={() => setIsWorkspaceModalOpen(false)}
      onWorkspaceCreated={handleWorkspaceCreated}
    >
      {renderActiveView()}
    </DashboardLayout>
  );
}
