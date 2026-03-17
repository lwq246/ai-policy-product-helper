"use client";
import { apiAsk } from "@/lib/api";
import React, { useEffect, useRef } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: { title: string; section?: string }[];
  chunks?: { title: string; section?: string; text: string }[];
};

export default function Chat() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [q, setQ] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = async () => {
    if (!q.trim() || loading) return;
    const my = { role: "user" as const, content: q };
    setMessages((m) => [...m, my]);
    setLoading(true);
    setQ("");

    try {
      const res = await apiAsk(q);
      const ai: Message = {
        role: "assistant",
        content: res.answer,
        citations: res.citations,
        chunks: res.chunks,
      };
      setMessages((m) => [...m, ai]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "⚠️ Error: " + e.message },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="card"
      style={{ display: "flex", flexDirection: "column", height: "500px" }}
    >
      <h2 style={{ marginTop: 0 }}>Chat</h2>

      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "10px",
          backgroundColor: "#f9f9f9",
          borderRadius: "8px",
          marginBottom: "12px",
          border: "1px solid #eee",
        }}
      >
        {messages.length === 0 && (
          <p style={{ textAlign: "center", color: "#999", marginTop: "40px" }}>
            Ask a policy question to get started...
          </p>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              marginBottom: "20px",
              display: "flex",
              flexDirection: "column",
              alignItems: m.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                fontSize: "11px",
                fontWeight: 700,
                color: "#888",
                marginBottom: "4px",
                textTransform: "uppercase",
              }}
            >
              {m.role === "user" ? "You" : "AI Assistant"}
            </div>

            <div
              style={{
                maxWidth: "85%",
                padding: "12px 16px",
                borderRadius: "12px",
                lineHeight: "1.5",
                backgroundColor: m.role === "user" ? "#111" : "#fff",
                color: m.role === "user" ? "#fff" : "#111",
                boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                border: m.role === "assistant" ? "1px solid #eee" : "none",
              }}
            >
              <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>

              {m.citations && m.citations.length > 0 && (
                <div
                  style={{
                    marginTop: "12px",
                    paddingTop: "8px",
                    borderTop: "1px solid #eee",
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "6px",
                  }}
                >
                  {m.citations.map((c, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: "10px",
                        backgroundColor: "#eee",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        color: "#555",
                      }}
                    >
                      📄 {c.title}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {m.chunks && m.chunks.length > 0 && (
              <details style={{ marginTop: "8px", width: "100%" }}>
                <summary
                  style={{
                    fontSize: "12px",
                    color: "#0066cc",
                    cursor: "pointer",
                    fontWeight: 500,
                  }}
                >
                  View supporting data ({m.chunks.length} chunks)
                </summary>
                <div
                  style={{
                    marginTop: "8px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  {m.chunks.map((c, idx) => (
                    <div
                      key={idx}
                      style={{
                        fontSize: "12px",
                        padding: "10px",
                        backgroundColor: "#fff",
                        borderLeft: "3px solid #0066cc",
                        borderRadius: "4px",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                      }}
                    >
                      <div style={{ fontWeight: 600, marginBottom: "4px" }}>
                        {c.title} {c.section ? `> ${c.section}` : ""}
                      </div>
                      <div style={{ color: "#444", fontStyle: "italic" }}>
                        "{c.text}"
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ fontSize: "12px", color: "#888" }}>
            Assistant is typing...
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          placeholder="Ask about returns, shipping, or blenders..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid #ddd",
            outline: "none",
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
        />
        <button
          onClick={send}
          disabled={loading}
          style={{
            padding: "0 20px",
            borderRadius: "8px",
            border: "none",
            background: "#111",
            color: "#fff",
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
