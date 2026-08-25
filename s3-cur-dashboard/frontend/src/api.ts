import type { CurLoadRequest, CurLoadResponse } from "./types";

// In dev, "/api" is proxied to localhost:8000 (see vite.config.ts). In a
// deployed build, set VITE_API_BASE_URL to the Lambda Function URL at build
// time so the static frontend knows where its backend lives.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const API_KEY = import.meta.env.VITE_API_KEY || "";

export async function loadCur(req: CurLoadRequest): Promise<CurLoadResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) {
    headers["x-api-key"] = API_KEY;
  }

  const res = await fetch(`${API_BASE_URL}/api/cur/load`, {
    method: "POST",
    headers,
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with ${res.status}`);
  }

  return res.json();
}
