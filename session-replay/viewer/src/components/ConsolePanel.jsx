import React from 'react';

const LEVEL_STYLES = {
  log:   { color: '#e2e8f0', bg: 'transparent' },
  info:  { color: '#3b82f6', bg: '#1e2d4a' },
  warn:  { color: '#f59e0b', bg: '#2a1f0a' },
  error: { color: '#ef4444', bg: '#2a0f0f' },
  debug: { color: '#8b5cf6', bg: '#1a1527' },
};

export default function ConsolePanel({ events, sessionStart }) {
  if (events.length === 0) return <Empty />;

  return (
    <div style={{ fontFamily: 'monospace' }}>
      {events.map((e, i) => {
        const style = LEVEL_STYLES[e.level] || LEVEL_STYLES.log;
        return (
          <div
            key={i}
            style={{
              padding: '5px 12px', fontSize: 12, background: style.bg,
              borderBottom: '1px solid #1a1d27', display: 'flex', gap: 10, alignItems: 'flex-start',
            }}
          >
            <span style={{ color: '#64748b', minWidth: 42, fontSize: 11 }}>{relTime(e.timestamp, sessionStart)}</span>
            <span style={{ color: style.color, minWidth: 44, fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{e.level}</span>
            <span style={{ color: style.color, wordBreak: 'break-all' }}>{(e.args || []).join(' ')}</span>
          </div>
        );
      })}
    </div>
  );
}

function Empty() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#64748b', fontSize: 13 }}>No console output captured</div>;
}

function relTime(ts, sessionStart) {
  const diff = ts - sessionStart;
  if (diff < 1000) return `${diff}ms`;
  return `${(diff / 1000).toFixed(1)}s`;
}
