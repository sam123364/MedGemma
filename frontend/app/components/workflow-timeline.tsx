"use client";

import { RunEvent } from "@/lib/types";

type Props = {
  events: RunEvent[];
};

export function WorkflowTimeline({ events }: Props) {
  const filtered = events.filter((event) => event.eventType !== "message");

  return (
    <section className="timeline-shell">
      <h3>Agentic Workflow Timeline</h3>
      <ol>
        {filtered.map((event) => (
          <li key={`${event.id}-${event.eventType}`}>
            <span className="dot" />
            <div>
              <p>{event.eventType}</p>
              <code>{JSON.stringify(event.payload)}</code>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
