import type { CurLoadRequest, CurLoadResponse } from "./types";

export async function loadCur(req: CurLoadRequest): Promise<CurLoadResponse> {
  const res = await fetch("/api/cur/load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with ${res.status}`);
  }

  return res.json();
}
