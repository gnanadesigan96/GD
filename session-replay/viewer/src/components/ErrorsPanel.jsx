import React, { useState } from 'react';

export default function ErrorsPanel({ events, sessionStart }) {
  const [expanded, setExpanded] = useState(null);

  if (events.length === 0) return <Empty />;

  return (
    <div>
      {events.map((e, i) => (
        <div
          key={i}
          style={{ borderBottom: '1px solid #2d3148', padding: '10px 14px', cursor: 'pointer' }}
          onClick={() => setExpanded(expanded === i ? null : i)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 11, color: '#64748b' }}>{relTime(e.timestamp, sessionStart)}</span>
            <span style={{
              fontSize: 11, padding: '2px 6px', borderRadius: 4,
              background: e.subtype === 'unhandledrejection' ? '#2a1527' : '#2a0f0f',
              color: e.subtype === 'unhandledrejection' ? '#c084fc' : '#ef4444',
            }}>
              {e.subtype}
            </span>
            <span style={{ fontSize: 13, color: '#fca5a5', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {e.message}
            </span>
          </div>

          {e.filename && (
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 3, marginLeft: 0 }}>
              {e.filename}:{e.lineno}:{e.colno}
            </div>
          )}

          {expanded === i && e.stack && (
            <pre style={{
              marginTop: 8, fontSize: 11, color: '#94a3b8', background: '#1a1d27',
              padding: 10, borderRadius: 6, overflow: 'auto', whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}>
              {e.stack}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

function Empty() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#10b981', fontSize: 13 }}>No errors — all clear</div>;
}

function relTime(ts, sessionStart) {
  const diff = ts - sessionStart;
  if (diff < 1000) return `${diff}ms`;
  return `${(diff / 1000).toFixed(1)}s`;
}
