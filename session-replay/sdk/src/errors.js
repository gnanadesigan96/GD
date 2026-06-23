export function createErrorInterceptor(push) {
  window.addEventListener('error', (event) => {
    push({
      type: 'error',
      subtype: 'uncaught',
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack || null,
      timestamp: Date.now(),
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    push({
      type: 'error',
      subtype: 'unhandledrejection',
      message: String(event.reason?.message || event.reason),
      stack: event.reason?.stack || null,
      timestamp: Date.now(),
    });
  });
}
