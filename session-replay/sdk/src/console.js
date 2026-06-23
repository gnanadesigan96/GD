import { safeStringify } from './utils';

const LEVELS = ['log', 'info', 'warn', 'error', 'debug'];

export function createConsoleInterceptor(push) {
  LEVELS.forEach((level) => {
    const original = console[level].bind(console);
    console[level] = function (...args) {
      push({
        type: 'console',
        level,
        args: args.map((a) => safeStringify(a)),
        timestamp: Date.now(),
      });
      original(...args);
    };
  });
}
