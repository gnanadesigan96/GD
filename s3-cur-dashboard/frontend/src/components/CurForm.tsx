import { FormEvent, useState } from "react";
import type { CurLoadRequest } from "../types";

interface CurFormProps {
  onSubmit: (req: CurLoadRequest) => void;
  loading: boolean;
  elapsedSeconds: number;
}

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function CurForm({ onSubmit, loading, elapsedSeconds }: CurFormProps) {
  const [roleArn, setRoleArn] = useState("");
  const [externalId, setExternalId] = useState("");
  const [s3Uri, setS3Uri] = useState("");
  const [month, setMonth] = useState(currentMonth());
  const [region, setRegion] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ role_arn: roleArn, external_id: externalId, s3_uri: s3Uri, month, region: region || undefined });
  }

  return (
    <form className="cur-form" onSubmit={handleSubmit}>
      <label>
        Role ARN
        <input
          value={roleArn}
          onChange={(e) => setRoleArn(e.target.value)}
          placeholder="arn:aws:iam::123456789012:role/CurReaderRole"
          required
        />
      </label>
      <label>
        External ID
        <input value={externalId} onChange={(e) => setExternalId(e.target.value)} required />
      </label>
      <label>
        S3 bucket or URI
        <input
          value={s3Uri}
          onChange={(e) => setS3Uri(e.target.value)}
          placeholder="my-cur-bucket or s3://my-cur-bucket/cur-reports/my-report"
          required
        />
      </label>
      <label>
        Month
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} required />
      </label>
      <label>
        Region <span className="field-optional">(optional — auto-detected if left blank)</span>
        <input
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          placeholder="e.g. eu-west-1 -- set this if a load fails with a DuckDB HTTP 400"
        />
      </label>
      <button type="submit" disabled={loading}>
        {loading ? `Loading... (${elapsedSeconds}s -- large reports can take several minutes)` : "Load report"}
      </button>
    </form>
  );
}
