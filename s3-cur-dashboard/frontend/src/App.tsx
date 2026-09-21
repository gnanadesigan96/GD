import { useState } from "react";
import { loadCur } from "./api";
import { CurForm } from "./components/CurForm";
import { Dashboard } from "./components/Dashboard";
import type { CurLoadRequest, CurLoadResponse } from "./types";

export default function App() {
  // Deliberately in-memory only -- nothing is persisted to localStorage or a
  // backend store, so refreshing the page wipes the loaded report.
  const [data, setData] = useState<CurLoadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(req: CurLoadRequest) {
    setLoading(true);
    setElapsedSeconds(0);
    setError(null);
    try {
      // A real CUR export can take minutes, not seconds -- loadCur polls
      // in the background rather than a single blocking request, so this
      // callback is how the UI knows how long it's been running.
      const result = await loadCur(req, setElapsedSeconds);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>S3 CUR Dashboard</h1>
        <p className="subtitle">Reads one month of Cost &amp; Usage Report data directly from S3. Nothing is stored.</p>
      </header>

      <CurForm onSubmit={handleSubmit} loading={loading} elapsedSeconds={elapsedSeconds} />

      {error && <div className="error">{error}</div>}
      {data && <Dashboard data={data} />}
    </div>
  );
}
