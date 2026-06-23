import React from 'react';

const METRIC_INFO = {
  LCP:        { label: 'Largest Contentful Paint', unit: 'ms', good: 2500, poor: 4000, color: '#3b82f6' },
  CLS:        { label: 'Cumulative Layout Shift',  unit: '',   good: 0.1,  poor: 0.25, color: '#f59e0b' },
  FID:        { label: 'First Input Delay',         unit: 'ms', good: 100,  poor: 300,  color: '#10b981' },
  longtask:   { label: 'Long Task',                unit: 'ms', good: 0,    poor: 0,    color: '#ef4444' },
  navigation: { label: 'Page Load',                unit: '',   good: 0,    poor: 0,    color: '#8b5cf6' },
};

function rating(subtype, value) {
  const info = METRIC_INFO[subtype];
  if (!info || info.good === 0) return null;
  if (value <= info.good) return { label: 'Good', color: '#10b981' };
  if (value <= info.poor) return { label: 'Needs Improvement', color: '#f59e0b' };
  return { label: 'Poor', color: '#ef4444' };
}

export default function PerformancePanel({ events }) {
  if (events.length === 0) return <Empty />;

  const webVitals = events.filter((e) => ['LCP', 'CLS', 'FID'].includes(e.subtype));
  const navigation = events.find((e) => e.subtype === 'navigation');
  const longtasks = events.filter((e) => e.subtype === 'longtask');

  return (
    <div style={{ padding: 16 }}>
      {webVitals.length > 0 && (
        <Section title="Web Vitals">
          {webVitals.map((e, i) => {
            const info = METRIC_INFO[e.subtype];
            const r = rating(e.subtype, e.value);
            return (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #1a1d27' }}>
                <div>
                  <div style={{ fontSize: 13, color: '#e2e8f0' }}>{info?.label || e.subtype}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: 18, fontWeight: 700, color: info?.color || '#94a3b8' }}>
                    {e.value.toFixed(e.subtype === 'CLS' ? 3 : 0)}{info?.unit}
                  </span>
                  {r && <span style={{ marginLeft: 8, fontSize: 11, color: r.color }}>{r.label}</span>}
                </div>
              </div>
            );
          })}
        </Section>
      )}

      {navigation && (
        <Section title="Page Load Breakdown">
          {[
            { label: 'DNS Lookup',     value: navigation.dns,          color: '#3b82f6' },
            { label: 'TCP Connect',    value: navigation.tcp,          color: '#10b981' },
            { label: 'Time to First Byte', value: navigation.ttfb,    color: '#f59e0b' },
            { label: 'DOM Interactive', value: navigation.domInteractive, color: '#8b5cf6' },
            { label: 'DOM Complete',   value: navigation.domComplete,  color: '#a78bfa' },
            { label: 'Transfer Size',  value: `${(navigation.transferSize / 1024).toFixed(1)} KB`, color: '#64748b', raw: true },
          ].map(({ label, value, color, raw }) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1a1d27', fontSize: 13 }}>
              <span style={{ color: '#94a3b8' }}>{label}</span>
              <span style={{ color, fontWeight: 600 }}>{raw ? value : `${Math.round(value)}ms`}</span>
            </div>
          ))}
        </Section>
      )}

      {longtasks.length > 0 && (
        <Section title={`Long Tasks (${longtasks.length})`}>
          {longtasks.map((e, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', fontSize: 12, borderBottom: '1px solid #1a1d27' }}>
              <span style={{ color: '#64748b' }}>Task #{i + 1}</span>
              <span style={{ color: '#ef4444', fontWeight: 600 }}>{Math.round(e.value)}ms</span>
            </div>
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{title}</div>
      {children}
    </div>
  );
}

function Empty() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#64748b', fontSize: 13 }}>No performance data captured</div>;
}
