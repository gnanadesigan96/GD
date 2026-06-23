import { record } from 'rrweb';
import { generateId } from './utils';
import { createNetworkInterceptor } from './network';
import { createConsoleInterceptor } from './console';
import { createErrorInterceptor } from './errors';
import { createPerformanceMonitor } from './performance';
import { createIdleDetector } from './idle';

let _config = null;
let _sessionId = null;
let _userId = null;
let _stopRecording = null;
let _eventBuffer = [];
let _flushTimer = null;

export function init(config) {
  _config = {
    endpoint: config.endpoint,
    s3Bucket: config.s3Bucket,
    flushInterval: config.flushInterval || 5000,
    idleTimeout: config.idleTimeout || 30000,
    captureNetwork: config.captureNetwork !== false,
    captureConsole: config.captureConsole !== false,
    captureErrors: config.captureErrors !== false,
    capturePerformance: config.capturePerformance !== false,
    maskInputs: config.maskInputs !== false,
    ignoredUrls: config.ignoredUrls || [],
    onSessionStart: config.onSessionStart || null,
  };

  _sessionId = generateId();
  _userId = config.userId || null;

  const sessionMeta = {
    sessionId: _sessionId,
    userId: _userId,
    startTime: Date.now(),
    url: location.href,
    userAgent: navigator.userAgent,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    referrer: document.referrer,
  };

  _post('/sessions', sessionMeta).then(() => {
    if (_config.onSessionStart) _config.onSessionStart(sessionMeta);
  });

  startCapture();
}

export function identify(userId, traits = {}) {
  _userId = userId;
  _pushEvent({ type: 'identify', userId, traits });
}

export function stop() {
  if (_stopRecording) _stopRecording();
  clearInterval(_flushTimer);
  _flush();
}

function startCapture() {
  // DOM recording via rrweb
  _stopRecording = record({
    emit(event) {
      _pushEvent({ type: 'rrweb', data: event });
    },
    maskAllInputs: _config.maskInputs,
    maskTextClass: 'sr-mask',
    blockClass: 'sr-block',
    sampling: {
      mousemove: 50,
      scroll: 150,
      input: 'last',
    },
  });

  if (_config.captureNetwork) {
    createNetworkInterceptor(_pushEvent, _config.ignoredUrls, _config.endpoint);
  }
  if (_config.captureConsole) {
    createConsoleInterceptor(_pushEvent);
  }
  if (_config.captureErrors) {
    createErrorInterceptor(_pushEvent);
  }
  if (_config.capturePerformance) {
    createPerformanceMonitor(_pushEvent);
  }

  createIdleDetector(_config.idleTimeout, (isIdle) => {
    _pushEvent({ type: 'idle', isIdle, timestamp: Date.now() });
  });

  _flushTimer = setInterval(_flush, _config.flushInterval);
  window.addEventListener('beforeunload', _flush);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') _flush();
  });
}

function _pushEvent(event) {
  _eventBuffer.push({ ...event, _ts: Date.now() });
}

async function _flush() {
  if (_eventBuffer.length === 0) return;
  const batch = _eventBuffer.splice(0, _eventBuffer.length);
  await _post(`/sessions/${_sessionId}/events`, { events: batch });
}

async function _post(path, body) {
  try {
    await fetch(`${_config.endpoint}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      keepalive: true,
    });
  } catch (e) {
    // silently fail — don't break the host app
  }
}
