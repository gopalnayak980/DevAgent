import { useState, useRef, useCallback, useEffect } from "react";
import { SendHorizontal } from "lucide-react";

export default function ChatInput({ onSend, isLoading }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  }, [text]);

  const handleSend = useCallback(() => {
    if (!text.trim() || isLoading) return;
    onSend(text);
    setText("");
    // Reset textarea height after sending
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [text, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e) => {
      // Enter to send, Shift+Enter for new line
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper" style={{ padding: '0.5rem 1rem', borderRadius: '1.5rem', boxShadow: 'var(--shadow-md)', background: 'var(--color-bg-secondary)' }}>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask DevAgent to build, debug, explain or analyze..."
          rows={1}
          disabled={isLoading}
          style={{ minHeight: '24px' }}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={!text.trim() || isLoading}
          aria-label="Send message"
          style={{ borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginLeft: '0.5rem', background: (!text.trim() || isLoading) ? 'var(--color-bg-tertiary)' : 'var(--color-accent)' }}
        >
          <SendHorizontal size={18} color={(!text.trim() || isLoading) ? 'var(--color-text-secondary)' : '#fff'} style={{ marginLeft: '-2px' }} />
        </button>
      </div>
    </div>
  );
}
