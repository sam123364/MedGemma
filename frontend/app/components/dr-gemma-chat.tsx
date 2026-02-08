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

  return (
    <section className="chat-shell">
      <div className="chat-head">
        <h3>Dr. MedGemma Explainability Console</h3>
        <p>Grounded in run artifacts only.</p>
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

      <form onSubmit={submit} className="chat-form">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Why is protocol #1 safer than #2?"
          disabled={pending}
        />
        <button type="submit" disabled={pending}>
          {pending ? "Thinking..." : "Ask"}
        </button>
      </form>
    </section>
  );
}
