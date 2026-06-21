"use client";

import { FormEvent, useState } from "react";

import { explainRun } from "@/lib/api";

type Props = {
  runId: string;
};

type Message = {
  role: "user" | "assistant";
  text: string;
};

export function DrGemmaChat({ runId }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "I can explain protocol ranking decisions using only this run's artifacts.",
    },
  ]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }

    const asked = question.trim();
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", text: asked }]);
    setPending(true);
    setError(null);

    try {
      const response = await explainRun(runId, asked);
      const suffix = response.grounded_source_ids.length
        ? `\n\nGrounded sources: ${response.grounded_source_ids.join(", ")}`
        : "";
      setMessages((prev) => [...prev, { role: "assistant", text: `${response.answer}${suffix}` }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setPending(false);
    }
  };

  const submitPrompt = async (text: string) => {
    if (pending) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setPending(true);
    setError(null);

    try {
      const response = await explainRun(runId, text);
      const suffix = response.grounded_source_ids.length
        ? `\n\nGrounded sources: ${response.grounded_source_ids.join(", ")}`
        : "";
      setMessages((prev) => [...prev, { role: "assistant", text: `${response.answer}${suffix}` }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <button 
        className="chat-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle chat assistant"
      >
        {isOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        )}
      </button>

      {/* Floating Chat Panel */}
      {isOpen && (
        <section className="chat-overlay-panel">
          <div className="chat-overlay-head">
            <div>
              <h3>Dr. MedGemma</h3>
              <p>Explainability Console</p>
            </div>
            <button className="chat-close-btn" onClick={() => setIsOpen(false)}>×</button>
          </div>

          <div className="chat-log" role="log" aria-live="polite">
            {messages.map((message, index) => (
              <article key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
                <span>{message.role === "assistant" ? "Dr. Gemma" : "You"}</span>
                <p>{message.text}</p>
              </article>
            ))}
          </div>

          {error ? <p className="chat-error">{error}</p> : null}

          {/* Quick Prompts Container */}
          <div className="chat-presets" style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", padding: "0.5rem 1rem", background: "#f8fafc", borderTop: "1px solid var(--border)" }}>
            <button type="button" onClick={() => submitPrompt("Why was the top recommendation selected?")} style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "14px", padding: "0.25rem 0.5rem", fontSize: "0.72rem", cursor: "pointer", color: "var(--fg-1)", fontWeight: 500 }}>
              Why #1?
            </button>
            <button type="button" onClick={() => submitPrompt("What are the key safety considerations for this twin?")} style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "14px", padding: "0.25rem 0.5rem", fontSize: "0.72rem", cursor: "pointer", color: "var(--fg-1)", fontWeight: 500 }}>
              Safety Check
            </button>
            <button type="button" onClick={() => submitPrompt("Is there any risk of Metformin lactic acidosis here?")} style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "14px", padding: "0.25rem 0.5rem", fontSize: "0.72rem", cursor: "pointer", color: "var(--fg-1)", fontWeight: 500 }}>
              Renal Risks
            </button>
          </div>

          <form onSubmit={submit} className="chat-form">
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Why is protocol #1 safer than #2?"
              disabled={pending}
            />
            <button type="submit" disabled={pending}>
              {pending ? "..." : "Ask"}
            </button>
          </form>
        </section>
      )}
    </>
  );
}
