const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'];

export function createIdleDetector(timeoutMs, onChange) {
  let isIdle = false;
  let timer = null;

  function reset() {
    if (isIdle) {
      isIdle = false;
      onChange(false);
    }
    clearTimeout(timer);
    timer = setTimeout(() => {
      isIdle = true;
      onChange(true);
    }, timeoutMs);
  }

  ACTIVITY_EVENTS.forEach((event) => {
    window.addEventListener(event, reset, { passive: true, capture: true });
  });

  reset();
}
