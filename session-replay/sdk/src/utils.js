export function generateId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
}

export function safeStringify(value, maxLen = 2000) {
  try {
    const s = typeof value === 'string' ? value : JSON.stringify(value);
    return s.length > maxLen ? s.slice(0, maxLen) + '…' : s;
  } catch {
    return String(value);
  }
}
