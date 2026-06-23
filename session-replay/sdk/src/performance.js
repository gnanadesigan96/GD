export function createPerformanceMonitor(push) {
  // Navigation timing (page load)
  window.addEventListener('load', () => {
    setTimeout(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      if (nav) {
        push({
          type: 'performance',
          subtype: 'navigation',
          dns: nav.domainLookupEnd - nav.domainLookupStart,
          tcp: nav.connectEnd - nav.connectStart,
          ttfb: nav.responseStart - nav.requestStart,
          domInteractive: nav.domInteractive,
          domComplete: nav.domComplete,
          loadEvent: nav.loadEventEnd - nav.loadEventStart,
          transferSize: nav.transferSize,
          timestamp: Date.now(),
        });
      }
    }, 0);
  });

  // Web Vitals via PerformanceObserver
  observeMetric('largest-contentful-paint', (entries) => {
    const lcp = entries[entries.length - 1];
    push({ type: 'performance', subtype: 'LCP', value: lcp.startTime, timestamp: Date.now() });
  });

  observeMetric('layout-shift', (entries) => {
    let cls = 0;
    entries.forEach((e) => { if (!e.hadRecentInput) cls += e.value; });
    if (cls > 0) push({ type: 'performance', subtype: 'CLS', value: cls, timestamp: Date.now() });
  });

  observeMetric('first-input', (entries) => {
    const fid = entries[0];
    push({ type: 'performance', subtype: 'FID', value: fid.processingStart - fid.startTime, timestamp: Date.now() });
  });

  observeMetric('longtask', (entries) => {
    entries.forEach((e) => {
      push({ type: 'performance', subtype: 'longtask', value: e.duration, timestamp: Date.now() });
    });
  });
}

function observeMetric(type, cb) {
  try {
    new PerformanceObserver((list) => cb(list.getEntries())).observe({ type, buffered: true });
  } catch (_) {
    // browser may not support this metric
  }
}
