import { Router } from 'express';
import { putObject, getObject, listObjects } from '../s3.js';

export const sessionsRouter = Router();

// POST /sessions — create session metadata
sessionsRouter.post('/', async (req, res) => {
  try {
    const meta = {
      ...req.body,
      createdAt: Date.now(),
      eventChunks: 0,
    };
    await putObject(`sessions/${meta.sessionId}/meta.json`, meta);
    res.json({ ok: true, sessionId: meta.sessionId });
  } catch (err) {
    console.error('POST /sessions', err);
    res.status(500).json({ error: err.message });
  }
});

// POST /sessions/:id/events — append event batch
sessionsRouter.post('/:id/events', async (req, res) => {
  try {
    const { id } = req.params;
    const { events } = req.body;

    // Read current chunk count from meta
    let meta;
    try {
      meta = await getObject(`sessions/${id}/meta.json`);
    } catch {
      meta = { sessionId: id, eventChunks: 0 };
    }

    const chunkIndex = meta.eventChunks;
    await putObject(
      `sessions/${id}/events/chunk_${String(chunkIndex).padStart(6, '0')}.json`,
      { events, chunkIndex, savedAt: Date.now() }
    );

    meta.eventChunks = chunkIndex + 1;
    meta.lastEventAt = Date.now();
    await putObject(`sessions/${id}/meta.json`, meta);

    res.json({ ok: true, chunkIndex });
  } catch (err) {
    console.error('POST /sessions/:id/events', err);
    res.status(500).json({ error: err.message });
  }
});

// GET /sessions — list all sessions with metadata
sessionsRouter.get('/', async (req, res) => {
  try {
    const keys = await listObjects('sessions/');
    const metaKeys = keys.filter((k) => k.endsWith('/meta.json'));

    const sessions = await Promise.all(
      metaKeys.map(async (key) => {
        try {
          return await getObject(key);
        } catch {
          return null;
        }
      })
    );

    const sorted = sessions
      .filter(Boolean)
      .sort((a, b) => b.createdAt - a.createdAt);

    res.json({ sessions: sorted });
  } catch (err) {
    console.error('GET /sessions', err);
    res.status(500).json({ error: err.message });
  }
});

// GET /sessions/:id — get session meta + all events merged
sessionsRouter.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const meta = await getObject(`sessions/${id}/meta.json`);

    const chunkKeys = await listObjects(`sessions/${id}/events/`);
    chunkKeys.sort();

    const allEvents = [];
    for (const key of chunkKeys) {
      const chunk = await getObject(key);
      allEvents.push(...chunk.events);
    }

    allEvents.sort((a, b) => (a._ts || 0) - (b._ts || 0));

    res.json({ meta, events: allEvents });
  } catch (err) {
    console.error('GET /sessions/:id', err);
    res.status(500).json({ error: err.message });
  }
});
