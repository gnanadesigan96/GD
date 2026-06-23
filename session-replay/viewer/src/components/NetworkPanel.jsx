import React, { useState } from 'react';

const METHOD_COLORS = {
  GET: '#3b82f6', POST: '#10b981', PUT: '#f59e0b',
  DELETE: '#ef4444', PATCH: '#8b5cf6', default: '#94a3b8',
};

function statusColor(status) {
  if (status >= 500) return '#ef4444';
  if (status >= 400) return '#f59e0b';
  if (status >= 300) return '#3b82f6';
  if (status >= 200) return '#10b981';
  return '#94a3b8';
}

export default function NetworkPanel({ events, sessionStart }) {
  const [selected, setSelected] = useState(null);

  if (events.length === 0) return <Empty message="No network requests captured" />;

  if (selected) {
    const e = selected;
    return (
      <div style={{ padding: 16, fontSize: 12 }}>
        <button onClick={() => setSelected(null)} style={backBtn}>← Back</button>
        <div style={{ marginTop: 12, color: '#e2e8f0', fontWeight: 600, wordBreak: 'break-all' }}>{e.method} {e.url}</div>
        <Section title="Response">
          <pre style={preStyle}>{tryFormat(e.responseBody)}</pre>
        </Section>
        <Section title="Request Body">
          <pre style={preStyle}>{tryFormat(e.requestBody) || '(none)'}</pre>
        </Section>
        {e.requestHeaders && Object.keys(e.requestHeaders).length > 0 && (
          <Section title="Request Headers">
            {Object.entries(e.requestHeaders).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 4 }}>
                <span style={{ color: '#94a3b8' }}>{k}: </span>
                <span style={{ color: '#e2e8f0' }}>{v}</span>
              </div>
            ))}
          </Section>
        )}
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '50px 60px 60px 1fr 60px', gap: 8, padding: '6px 12px', fontSize: 11, color: '#64748b', borderBottom: '1px solid #2d3148', position: 'sticky', top: 0, background: '#0f1117' }}>
        <span>Method</span><span>Status</span><span>Time</span><span>URL</span><span>ms</span>
      </div>
      {events.map((e, i) => (
        <div
          key={i}
          onClick={() => setSelected(e)}
          style={{
            display: 'grid', gridTemplateColumns: '50px 60px 60px 1fr 60px', gap: 8,
            padding: '6px 12px', fontSize: 12, cursor: 'pointer',
            borderBottom: '1px solid #1a1d27',
            background: i % 2 === 0 ? '#0f1117' : '#12151f',
          }}
          onMouseEnter={(el) => (el.currentTarget.style.background = '#1a1d27')}
          onMouseLeave={(el) => (el.currentTarget.style.background = i % 2 === 0 ? '#0f1117' : '#12151f')}
        >
          <span style={{ color: METHOD_COLORS[e.method] || METHOD_COLORS.default, fontWeight: 600 }}>{e.method}</span>
          <span style={{ color: statusColor(e.status) }}>{e.status || 'ERR'}</span>
          <span style={{ color: '#64748b' }}>{relTime(e.timestamp, sessionStart)}</span>
          <span style={{ color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{shortUrl(e.url)}</span>
          <span style={{ color: '#64748b' }}>{e.duration}ms</span>
        </div>
      ))}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>{title}</div>
      {children}
    </div>
  );
}

function Empty({ message }) {
  return <div style={{ padding: 40, textAlign: 'center', color: '#64748b', fontSize: 13 }}>{message}</div>;
}

const backBtn = { background: 'none', border: '1px solid #2d3148', color: '#94a3b8', padding: '4px 10px', borderRadius: 5, cursor: 'pointer', fontSize: 12 };
const preStyle = { background: '#1a1d27', color: '#e2e8f0', padding: 10, borderRadius: 6, fontSize: 11, overflow: 'auto', maxHeight: 300, whiteSpace: 'pre-wrap', wordBreak: 'break-all' };

function tryFormat(str) {
  if (!str) return '';
  try { return JSON.stringify(JSON.parse(str), null, 2); } catch { return str; }
}

function shortUrl(url) {
  try { const u = new URL(url); return u.pathname + u.search; } catch { return url; }
}

function relTime(ts, sessionStart) {
  const diff = ts - sessionStart;
  if (diff < 1000) return `${diff}ms`;
  return `${(diff / 1000).toFixed(1)}s`;
}
