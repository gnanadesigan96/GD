import type { CurJobStartedResponse, CurJobStatusResponse, CurLoadRequest, CurLoadResponse } from "./types";

// Same-origin in both dev (proxied to localhost:8000, see vite.config.ts)
// and production (CloudFront's /api/* behavior forwards to API Gateway).
// A long-running call bypassing this via a Lambda Function URL was tried
// and abandoned -- see deploy/deploy_backend.sh's history -- once the load
// became an async job, both calls here (start + poll) are fast enough to
// stay well within API Gateway's timeout, so there's no need for a second
// origin at all.
const API_KEY = import.meta.env.VITE_API_KEY || "";

// Polls fast at first (quick loads get quick feedback), then backs off --
// a Flatiron-scale load can take minutes, and polling every 2s for all of
// that is wasted API Gateway/DynamoDB/Lambda-invocation cost for zero
// benefit (the elapsed-seconds counter is the only thing that'd notice).
const POLL_BACKOFF_SCHEDULE: { afterSeconds: number; intervalMs: number }[] = [
  { afterSeconds: 0, intervalMs: 2000 },
  { afterSeconds: 20, intervalMs: 5000 },
  { afterSeconds: 60, intervalMs: 10000 },
];

function pollIntervalFor(elapsedSeconds: number): number {
  let interval = POLL_BACKOFF_SCHEDULE[0].intervalMs;
  for (const step of POLL_BACKOFF_SCHEDULE) {
    if (elapsedSeconds >= step.afterSeconds) interval = step.intervalMs;
  }
  return interval;
}

function authHeaders(): Record<string, string> {
  return API_KEY ? { "x-api-key": API_KEY } : {};
}

async function parseErrorOrThrow(res: Response): Promise<never> {
  const body = await res.json().catch(() => ({}));
  throw new Error(body.detail || `Request failed with ${res.status}`);
}

async function startCurLoad(req: CurLoadRequest): Promise<CurJobStartedResponse> {
  const res = await fetch("/api/cur/load", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(req),
  });
  if (!res.ok) return parseErrorOrThrow(res);
  return res.json();
}

async function getCurJob(jobId: string): Promise<CurJobStatusResponse> {
  const res = await fetch(`/api/cur/job/${jobId}`, { headers: authHeaders() });
  if (!res.ok) return parseErrorOrThrow(res);
  return res.json();
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Starts the load and polls until it's done. A real CUR export can take
 * anywhere from seconds to several minutes -- this is why the backend
 * moved to a start-job/poll-status pattern instead of one blocking
 * request, since API Gateway's 30-second timeout can't be raised.
 *
 * onTick (optional) is called after every poll with how many seconds
 * have elapsed, so the caller can show live progress.
 */
export async function loadCur(req: CurLoadRequest, onTick?: (elapsedSeconds: number) => void): Promise<CurLoadResponse> {
  const { job_id } = await startCurLoad(req);
  const startedAt = Date.now();

  for (;;) {
    const elapsedSeconds = Math.round((Date.now() - startedAt) / 1000);
    await sleep(pollIntervalFor(elapsedSeconds));
    const status = await getCurJob(job_id);
    onTick?.(Math.round((Date.now() - startedAt) / 1000));

    if (status.status === "done" && status.result) {
      return status.result;
    }
    if (status.status === "error") {
      throw new Error(status.error || "Failed to load report");
    }
    // status === "pending" -- keep polling
  }
}
