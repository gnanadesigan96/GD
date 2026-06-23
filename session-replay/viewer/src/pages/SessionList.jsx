import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow, format } from 'date-fns';

export default function SessionList() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/sessions')
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []))
      .finally(() => setLoading(false));
  }, []);

  const filtered = sessions.filter((s) => {
    const q = search.toLowerCase();
    return (
      !q ||
      (s.userId || '').toLowerCase().includes(q) ||
      (s.sessionId || '').toLowerCase().includes(q) ||
      (s.url || '').toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#a78bfa' }}>Session Replay</h1>
        <span style={{ fontSize: 13, color: '#64748b' }}>{filtered.length} sessions</span>
      </div>

      <input
        type="text"
        placeholder="Search by user ID, session ID, or URL…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          width: '100%', padding: '10px 14px', marginBottom: 20,
          background: '#1a1d27', border: '1px solid #2d3148', borderRadius: 8,
          color: '#e2e8f0', fontSize: 14, outline: 'none',
        }}
      />

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>Loading sessions…</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>No sessions found</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((s) => (
            <SessionRow key={s.sessionId} session={s} onClick={() => navigate(`/session/${s.sessionId}`)} />
          ))}
        </div>
      )}
    </div>
  );
}

function SessionRow({ session: s, onClick }) {
  const duration = s.lastEventAt ? Math.round((s.lastEventAt - s.createdAt) / 1000) : null;

  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 160px 100px 80px 80px',
        alignItems: 'center',
        gap: 12,
        padding: '14px 18px',
        background: '#1a1d27',
        border: '1px solid #2d3148',
        borderRadius: 8,
        cursor: 'pointer',
        transition: 'border-color 0.15s',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#a78bfa')}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#2d3148')}
    >
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0', marginBottom: 3 }}>
          {s.userId || <span style={{ color: '#64748b' }}>Anonymous</span>}
        </div>
        <div style={{ fontSize: 12, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {s.url}
        </div>
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8' }}>
        {s.createdAt ? formatDistanceToNow(new Date(s.createdAt), { addSuffix: true }) : '—'}
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
        {duration != null ? `${duration}s` : '—'}
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
        {s.eventChunks ?? 0} chunks
      </div>
      <div>
        <span style={{
          display: 'inline-block', padding: '3px 8px', borderRadius: 4,
          fontSize: 11, background: '#1e3a2f', color: '#4ade80',
        }}>
          recorded
        </span>
      </div>
    </div>
  );
}
