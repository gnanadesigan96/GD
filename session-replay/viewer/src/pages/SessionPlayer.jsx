import React, { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import rrwebPlayer from 'rrweb-player';
import 'rrweb-player/dist/style.css';
import NetworkPanel from '../components/NetworkPanel';
import ConsolePanel from '../components/ConsolePanel';
import ErrorsPanel from '../components/ErrorsPanel';
import PerformancePanel from '../components/PerformancePanel';

const TABS = ['Network', 'Console', 'Errors', 'Performance'];

export default function SessionPlayer() {
  const { id } = useParams();
  const navigate = useNavigate();
  const playerContainerRef = useRef(null);
  const playerRef = useRef(null);

  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Network');
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    fetch(`/sessions/${id}`)
      .then((r) => r.json())
      .then(setSession)
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!session || !playerContainerRef.current) return;

    const rrwebEvents = session.events
      .filter((e) => e.type === 'rrweb')
      .map((e) => e.data);

    if (rrwebEvents.length < 2) return;

    playerRef.current = new rrwebPlayer({
      target: playerContainerRef.current,
      props: {
        events: rrwebEvents,
        width: playerContainerRef.current.offsetWidth,
        height: 500,
        autoPlay: false,
        showController: true,
        speedOption: [1, 2, 4, 8],
      },
    });

    playerRef.current.$on('ui-update-current-time', ({ payload }) => {
      setCurrentTime(payload);
    });

    return () => {
      if (playerRef.current) {
        playerRef.current.$destroy();
        playerRef.current = null;
      }
    };
  }, [session]);

  if (loading) return <Loader />;
  if (!session) return <div style={{ padding: 40, color: '#ef4444' }}>Session not found</div>;

  const { meta, events } = session;
  const networkEvents = events.filter((e) => e.type === 'network');
  const consoleEvents = events.filter((e) => e.type === 'console');
  const errorEvents = events.filter((e) => e.type === 'error');
  const perfEvents = events.filter((e) => e.type === 'performance');

  const sessionStart = meta.createdAt || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#0f1117' }}>
      {/* Header */}
      <div style={{ padding: '12px 20px', borderBottom: '1px solid #2d3148', display: 'flex', alignItems: 'center', gap: 16 }}>
        <button
          onClick={() => navigate('/')}
          style={{ background: 'none', border: '1px solid #2d3148', color: '#94a3b8', padding: '4px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}
        >
          ← Back
        </button>
        <div>
          <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{meta.userId || 'Anonymous'}</span>
          <span style={{ color: '#64748b', marginLeft: 12, fontSize: 13 }}>{meta.url}</span>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 16, fontSize: 12, color: '#64748b' }}>
          <span><b style={{ color: '#f59e0b' }}>{networkEvents.length}</b> requests</span>
          <span><b style={{ color: '#ef4444' }}>{errorEvents.length}</b> errors</span>
          <span><b style={{ color: '#94a3b8' }}>{consoleEvents.length}</b> logs</span>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Player */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderRight: '1px solid #2d3148' }}>
          <div ref={playerContainerRef} style={{ width: '100%' }} />
          <IdleTimeline events={events} sessionStart={sessionStart} currentTime={currentTime} />
        </div>

        {/* Side Panel */}
        <div style={{ width: 480, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', borderBottom: '1px solid #2d3148' }}>
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  flex: 1, padding: '10px 4px', fontSize: 12, fontWeight: 600,
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: activeTab === tab ? '#a78bfa' : '#64748b',
                  borderBottom: activeTab === tab ? '2px solid #a78bfa' : '2px solid transparent',
                  transition: 'color 0.15s',
                }}
              >
                {tab}
                {tab === 'Errors' && errorEvents.length > 0 && (
                  <span style={{ marginLeft: 4, background: '#ef4444', color: '#fff', borderRadius: 10, padding: '1px 5px', fontSize: 10 }}>
                    {errorEvents.length}
                  </span>
                )}
              </button>
            ))}
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            {activeTab === 'Network' && <NetworkPanel events={networkEvents} sessionStart={sessionStart} />}
            {activeTab === 'Console' && <ConsolePanel events={consoleEvents} sessionStart={sessionStart} />}
            {activeTab === 'Errors' && <ErrorsPanel events={errorEvents} sessionStart={sessionStart} />}
            {activeTab === 'Performance' && <PerformancePanel events={perfEvents} sessionStart={sessionStart} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function IdleTimeline({ events, sessionStart }) {
  const idleEvents = events.filter((e) => e.type === 'idle');
  if (idleEvents.length === 0) return null;

  const lastEvent = events[events.length - 1];
  const totalDuration = lastEvent ? (lastEvent._ts - sessionStart) : 1;

  return (
    <div style={{ padding: '8px 12px', borderTop: '1px solid #2d3148' }}>
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>Idle periods</div>
      <div style={{ position: 'relative', height: 8, background: '#1a1d27', borderRadius: 4, overflow: 'hidden' }}>
        {idleEvents.map((e, i) => {
          if (!e.isIdle) return null;
          const nextActive = idleEvents.find((x, j) => j > i && !x.isIdle);
          const start = ((e._ts - sessionStart) / totalDuration) * 100;
          const end = nextActive ? ((nextActive._ts - sessionStart) / totalDuration) * 100 : 100;
          return (
            <div
              key={i}
              title="Idle period"
              style={{
                position: 'absolute', top: 0, height: '100%',
                left: `${start}%`, width: `${end - start}%`,
                background: '#7c3aed', opacity: 0.6, borderRadius: 2,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

function Loader() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#64748b' }}>
      Loading session…
    </div>
  );
}
