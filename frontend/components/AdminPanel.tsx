"use client";
import { apiIngest, apiMetrics } from "@/lib/api";
import React from "react";

export default function AdminPanel() {
  const [metrics, setMetrics] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);
  const [status, setStatus] = React.useState<string | null>(null);

  const refresh = async () => {
    try {
      const m = await apiMetrics();
      setMetrics(m);
    } catch (e) {
      console.error("Failed to fetch metrics");
    }
  };

  const ingest = async () => {
    setBusy(true);
    setStatus(null);
    try {
      const res = await apiIngest();
      setStatus(
        `✅ Successfully indexed ${res.indexed_chunks} chunks from ${res.indexed_docs} documents.`,
      );
      await refresh();
    } catch (e) {
      setStatus("❌ Ingestion failed. Check backend logs.");
    } finally {
      setBusy(false);
    }
  };

  React.useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>System Admin</h2>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <button
          onClick={ingest}
          disabled={busy}
          style={{
            padding: "10px 16px",
            borderRadius: "8px",
            border: "none",
            background: busy ? "#ccc" : "#0066cc",
            color: "#fff",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {busy ? "⚙️ Processing..." : "📥 Ingest Sample Docs"}
        </button>
        <button
          onClick={refresh}
          style={{
            padding: "10px 16px",
            borderRadius: "8px",
            border: "1px solid #ddd",
            background: "#fff",
            cursor: "pointer",
          }}
        >
          🔄 Refresh Metrics
        </button>
      </div>

      {status && (
        <div
          style={{
            padding: "10px",
            borderRadius: "6px",
            backgroundColor: status.includes("✅") ? "#e6fffa" : "#fff5f5",
            color: status.includes("✅") ? "#234e52" : "#c53030",
            marginBottom: "16px",
            fontSize: "14px",
            border: "1px solid",
          }}
        >
          {status}
        </div>
      )}

      {metrics && (
        <details>
          <summary
            style={{ cursor: "pointer", fontSize: "14px", color: "#666" }}
          >
            View System Metrics
          </summary>
          <div
            className="code"
            style={{
              marginTop: "8px",
              backgroundColor: "#f4f4f4",
              padding: "12px",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          >
            <pre style={{ margin: 0 }}>{JSON.stringify(metrics, null, 2)}</pre>
          </div>
        </details>
      )}
    </div>
  );
}
