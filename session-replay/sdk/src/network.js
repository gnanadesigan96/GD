import { safeStringify } from './utils';

export function createNetworkInterceptor(push, ignoredUrls, replayEndpoint) {
  interceptFetch(push, ignoredUrls, replayEndpoint);
  interceptXHR(push, ignoredUrls, replayEndpoint);
}

function shouldIgnore(url, ignoredUrls, replayEndpoint) {
  if (url.startsWith(replayEndpoint)) return true;
  return ignoredUrls.some((p) => url.includes(p));
}

function interceptFetch(push, ignoredUrls, replayEndpoint) {
  const originalFetch = window.fetch;
  window.fetch = async function (input, init = {}) {
    const url = typeof input === 'string' ? input : input.url;
    if (shouldIgnore(url, ignoredUrls, replayEndpoint)) {
      return originalFetch.apply(this, arguments);
    }

    const startTime = Date.now();
    const method = (init.method || 'GET').toUpperCase();
    const requestBody = init.body ? safeStringify(init.body) : null;

    try {
      const response = await originalFetch.apply(this, arguments);
      const cloned = response.clone();
      const duration = Date.now() - startTime;

      cloned.text().then((body) => {
        push({
          type: 'network',
          subtype: 'fetch',
          url,
          method,
          status: response.status,
          duration,
          requestBody,
          responseBody: safeStringify(body),
          requestHeaders: init.headers ? Object.fromEntries(new Headers(init.headers).entries()) : {},
          timestamp: startTime,
        });
      }).catch(() => {
        push({ type: 'network', subtype: 'fetch', url, method, status: response.status, duration, timestamp: startTime });
      });

      return response;
    } catch (error) {
      push({
        type: 'network',
        subtype: 'fetch',
        url,
        method,
        status: 0,
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: startTime,
      });
      throw error;
    }
  };
}

function interceptXHR(push, ignoredUrls, replayEndpoint) {
  const OriginalXHR = window.XMLHttpRequest;

  window.XMLHttpRequest = function () {
    const xhr = new OriginalXHR();
    let _url = '';
    let _method = '';
    let _startTime = 0;
    let _requestBody = null;

    const originalOpen = xhr.open.bind(xhr);
    xhr.open = function (method, url, ...rest) {
      _url = url;
      _method = method.toUpperCase();
      return originalOpen(method, url, ...rest);
    };

    const originalSend = xhr.send.bind(xhr);
    xhr.send = function (body) {
      if (shouldIgnore(_url, ignoredUrls, replayEndpoint)) return originalSend(body);
      _startTime = Date.now();
      _requestBody = body ? safeStringify(body) : null;

      xhr.addEventListener('loadend', () => {
        push({
          type: 'network',
          subtype: 'xhr',
          url: _url,
          method: _method,
          status: xhr.status,
          duration: Date.now() - _startTime,
          requestBody: _requestBody,
          responseBody: safeStringify(xhr.responseText),
          timestamp: _startTime,
        });
      });

      return originalSend(body);
    };

    return xhr;
  };
}
