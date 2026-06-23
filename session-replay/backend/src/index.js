import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import compression from 'compression';
import { sessionsRouter } from './routes/sessions.js';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: process.env.CORS_ORIGIN || '*' }));
app.use(compression());
app.use(express.json({ limit: '10mb' }));

app.use('/sessions', sessionsRouter);

app.get('/health', (_req, res) => res.json({ ok: true }));

app.listen(PORT, () => console.log(`Session Replay API listening on :${PORT}`));
