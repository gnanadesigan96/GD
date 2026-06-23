# Session Replay

A self-hosted session replay system (like Pendo/LogRocket) that captures user sessions and plays them back with full dev tools visibility.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Your App                                                   │
│  <script src="sdk.min.js"></script>                         │
│  SessionReplay.init({ endpoint, userId, ... })              │
└──────────────────────┬──────────────────────────────────────┘
                       │ POST /sessions/:id/events (batched)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (Node.js/Express)                                  │
│  Receives event batches → streams to S3                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ S3 objects: sessions/{id}/meta.json
                       │             sessions/{id}/events/chunk_*.json
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Viewer (React)                                             │
│  Session list → rrweb DOM playback + Network/Console/       │
│  Errors/Performance side panel                              │
└─────────────────────────────────────────────────────────────┘
```

## What gets captured

| Category | Detail |
|---|---|
| **DOM** | Full pixel-perfect replay via rrweb (clicks, scrolls, input, navigation) |
| **Network** | All fetch/XHR calls — URL, method, status, duration, request & response body |
| **Console** | log, info, warn, error, debug with timestamps |
| **Errors** | Uncaught exceptions + unhandled promise rejections with stack traces |
| **Performance** | LCP, CLS, FID web vitals + page load breakdown + long tasks |
| **Idle** | Idle periods shown on timeline (default: 30s threshold) |

## Quick start

### 1. Backend setup

```bash
cd backend
cp .env.example .env      # fill in AWS credentials & S3 bucket
npm install
npm start                  # listens on :3001
```

### 2. Viewer setup

```bash
cd viewer
npm install
npm run dev                # opens on :3000
```

### 3. SDK — embed in your app

**Option A: build from source**
```bash
cd sdk
npm install
npm run build              # outputs dist/sdk.min.js
```

Then in your app's HTML (just before `</body>`):
```html
<script src="/path/to/sdk.min.js"></script>
<script>
  SessionReplay.init({
    endpoint: 'https://your-backend.com',  // your backend URL
    userId: currentUser.id,                 // pass logged-in user ID
    maskInputs: true,                       // mask passwords/sensitive fields
    idleTimeout: 30000,                     // 30s before marking idle
  });
</script>
```

**Option B: npm (if your app has a bundler)**
```js
import { init, identify } from '@session-replay/sdk';
init({ endpoint: '...', userId: '...' });

// After login, update the user identity:
identify('user-123', { name: 'John', plan: 'pro' });
```

## SDK config options

| Option | Default | Description |
|---|---|---|
| `endpoint` | required | Your backend API URL |
| `userId` | null | User identifier |
| `flushInterval` | 5000ms | How often to send event batches |
| `idleTimeout` | 30000ms | Inactivity threshold for idle detection |
| `maskInputs` | true | Mask all input values (recommended) |
| `captureNetwork` | true | Toggle network interception |
| `captureConsole` | true | Toggle console capture |
| `captureErrors` | true | Toggle error capture |
| `capturePerformance` | true | Toggle performance metrics |
| `ignoredUrls` | [] | URL patterns to skip in network capture |

## Privacy controls

Add CSS classes to elements you want to hide from recordings:
- `sr-mask` — blurs text content
- `sr-block` — replaces element with a placeholder box

## S3 bucket structure

```
sessions/
  {sessionId}/
    meta.json          ← session metadata (userId, url, viewport, etc.)
    events/
      chunk_000000.json  ← event batch 0
      chunk_000001.json  ← event batch 1
      ...
```
