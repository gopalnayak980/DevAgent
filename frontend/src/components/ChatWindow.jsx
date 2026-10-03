import { useEffect, useRef } from "react";
import Message from "./Message.jsx";

import { Code, Terminal, Server, Shield, Lightbulb } from "lucide-react";

const SUGGESTIONS = [
  { title: "Build a REST API", desc: "with Node.js and Express", icon: <Server size={24} /> },
  { title: "Debug this error", desc: "Help me fix a React issue", icon: <Terminal size={24} /> },
  { title: "Explain concepts", desc: "Like Java inheritance", icon: <Lightbulb size={24} /> },
  { title: "Review my code", desc: "Check for best practices", icon: <Shield size={24} /> },
];

export default function ChatWindow({ messages, isLoading, error, onHintClick, onApprovalAction }) {
  const bottomRef = useRef(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, error]);

  const isEmpty = messages.length === 0 && !isLoading;

  return (
    <div className="chat-window">
      {isEmpty ? (
        <div className="welcome">
          <div className="welcome-icon">🤖</div>
          <h2>Welcome to DevAgent</h2>
          <p>
            Your AI software engineering assistant. Ask me about coding,
            debugging, architecture, or best practices.
          </p>
          <div className="welcome-hints" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '2rem', width: '100%', maxWidth: '800px' }}>
            {SUGGESTIONS.map((suggestion, idx) => (
              <button
                key={idx}
                className="welcome-hint-card"
                onClick={() => onHintClick(suggestion.title)}
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', padding: '1rem', background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', cursor: 'pointer', transition: 'all 0.2s', textAlign: 'left', gap: '0.5rem' }}
                onMouseOver={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                onMouseOut={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; e.currentTarget.style.transform = 'translateY(0)' }}
              >
                <div style={{ color: 'var(--color-accent)' }}>{suggestion.icon}</div>
                <div style={{ fontWeight: '600', color: 'var(--color-text-primary)' }}>{suggestion.title}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>{suggestion.desc}</div>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="messages">
          {messages.map((msg, index) => (
            <Message 
              key={index} 
              role={msg.role} 
              content={msg.content} 
              requiresApproval={msg.requiresApproval} 
              approval={msg.approval} 
              onApprovalAction={onApprovalAction} 
            />
          ))}

          {isLoading && (
            <div className="message message--ai">
              <div className="message-avatar">D</div>
              <div className="message-content">
                <div className="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="error-banner">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                <path d="M8 4.5V9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <circle cx="8" cy="11.5" r="0.75" fill="currentColor" />
              </svg>
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
