import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const InlineCode = ({ children, ...props }) => {
  return (
    <code 
      className="inline-code" 
      style={{ 
        background: 'var(--color-bg-tertiary)', 
        padding: '0.2em 0.4em', 
        borderRadius: '4px', 
        fontSize: '0.85em', 
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', 
        color: 'var(--color-text-primary)' 
      }} 
      {...props}
    >
      {children}
    </code>
  );
};

const FencedCodeBlock = ({ children, ...props }) => {
  const codeElement = Array.isArray(children) ? children[0] : children;
  
  if (!codeElement || !codeElement.props) {
    return <pre {...props}>{children}</pre>;
  }

  const className = codeElement.props.className || '';
  const match = /language-(\w+)/.exec(className);
  const language = match ? match[1] : 'text';
  const displayLanguage = match ? match[1] : 'Code';
  const codeString = String(codeElement.props.children).replace(/\n$/, '');

  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-wrapper" style={{ position: 'relative', margin: '1rem 0', borderRadius: '8px', overflow: 'hidden', border: '1px solid #333', background: '#1e1e1e', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' }}>
      <div className="code-block-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 1rem', background: '#252526', borderBottom: '1px solid #333' }}>
        <span className="code-language" style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#a3a3a3', fontWeight: '600' }}>{displayLanguage}</span>
        <button onClick={handleCopy} className="btn-copy" style={{ background: 'transparent', border: 'none', color: '#a3a3a3', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', padding: 0 }}>
          {copied ? <><Check size={14} color="#4ade80" /> <span style={{ color: '#4ade80' }}>Copied</span></> : <><Copy size={14} /> Copy</>}
        </button>
      </div>
      <div style={{ fontSize: '0.875rem', lineHeight: '1.5' }}>
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={language}
          PreTag="div"
          showLineNumbers={true}
          wrapLines={true}
          wrapLongLines={false}
          customStyle={{
            margin: 0,
            padding: '1rem 0',
            background: '#1e1e1e',
            border: 'none',
            overflowX: 'auto',
          }}
          lineNumberStyle={{
            minWidth: '3em',
            paddingRight: '1em',
            color: '#858585',
            textAlign: 'right',
          }}
        >
          {codeString}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};

export default function Message({ role, content, requiresApproval, approval, onApprovalAction, agent, intent, duration }) {
  const isUser = role === "user";

  return (
    <div className={`message message--${isUser ? "user" : "ai"}`}>
      <div className="message-avatar">{isUser ? "U" : "D"}</div>
      <div className="message-content" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {!isUser && (agent || intent || duration) && (
          <div className="message-meta" style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
            {agent && <span><strong>Agent:</strong> {agent}</span>}
            {intent && <span><strong>Intent:</strong> {intent}</span>}
            {duration && <span><strong>Duration:</strong> {duration}s</span>}
          </div>
        )}
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code: InlineCode,
            pre: FencedCodeBlock
          }}
        >
          {content}
        </ReactMarkdown>
        {requiresApproval && approval && (
          <div className="approval-card" style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', background: 'var(--color-bg-tertiary)' }}>
            <h4 style={{ marginBottom: '0.5rem', color: 'var(--color-error)' }}>⚠️ Approval Required</h4>
            <p><strong>Action:</strong> {approval.description}</p>
            <p><strong>Status:</strong> {approval.status}</p>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button 
                onClick={() => onApprovalAction(approval.id, 'approve')}
                style={{ padding: '0.5rem 1rem', background: 'var(--color-success)', color: '#000', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 'bold' }}
              >
                Approve
              </button>
              <button 
                onClick={() => onApprovalAction(approval.id, 'reject')}
                style={{ padding: '0.5rem 1rem', background: 'var(--color-error)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 'bold' }}
              >
                Reject
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
