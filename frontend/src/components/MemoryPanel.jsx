import { BrainCircuit, BookOpen } from "lucide-react";

export default function MemoryPanel() {
  return (
    <div className="memory-panel" style={{ padding: '2rem', display: 'flex', justifyContent: 'center' }}>
      <div className="memory-placeholder" style={{ background: 'var(--color-bg-secondary)', padding: '3rem 2rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)', maxWidth: '600px', textAlign: 'center' }}>
        <div className="memory-placeholder-icon" style={{ background: 'var(--color-accent-glow)', width: '64px', height: '64px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', color: 'var(--color-accent)' }}>
          <BrainCircuit size={32} />
        </div>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem', color: 'var(--color-text-primary)' }}>Memory is Active</h3>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem', lineHeight: '1.6' }}>
          The system actively learns and retrieves context from your conversations 
          (Preferences, Facts, Goals, and Context) in the background to improve 
          agent responses.
        </p>
        <div style={{ background: 'var(--color-bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'flex-start', gap: '0.75rem', textAlign: 'left' }}>
          <BookOpen size={20} color="var(--color-accent)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <p className="memory-subtext" style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', margin: 0 }}>
            A dedicated UI for browsing, editing, and managing specific memory nodes 
            has not been exposed yet. This feature will be fully realized in a future phase.
          </p>
        </div>
      </div>
    </div>
  );
}
