import { ChatExplainResponse, PatientTwinInput, RunArtifact, RunEvent, RunStartResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function createRun(patient: PatientTwinInput, targetCount = 10): Promise<RunStartResponse> {
  const response = await fetch(`${API_BASE}/api/v1/runs?target_count=${targetCount}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(patient),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Run creation failed: ${response.status} ${errText}`);
  }

  return (await response.json()) as RunStartResponse;
}

export async function fetchRunResult(runId: string): Promise<RunArtifact | null> {
  const response = await fetch(`${API_BASE}/api/v1/runs/${runId}/result`, {
    method: "GET",
    cache: "no-store",
  });

  if (response.status === 202) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Failed to fetch run result: ${response.status}`);
  }

  return (await response.json()) as RunArtifact;
}

export function streamRunEvents(
  runId: string,
  onEvent: (event: RunEvent) => void,
  onError: (message: string) => void,
): EventSource {
  const source = new EventSource(`${API_BASE}/api/v1/runs/${runId}/events`);

  source.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data) as Record<string, unknown>;
      onEvent({
        id: Number(event.lastEventId || 0),
        eventType: "message",
        payload,
      });
    } catch {
      onError("Unable to parse stream event payload.");
    }
  };

  const typedEvents = [
    "run.started",
    "protocols.generated",
    "coarse.progress",
    "shortlist.ready",
    "highfidelity.progress",
    "critic.done",
    "run.completed",
    "run.failed",
  ];

  typedEvents.forEach((name) => {
    source.addEventListener(name, (event) => {
      const msg = event as MessageEvent;
      try {
        const payload = JSON.parse(msg.data) as Record<string, unknown>;
        onEvent({
          id: Number(msg.lastEventId || 0),
          eventType: name,
          payload,
          timestamp: payload.timestamp as string | undefined,
        });
      } catch {
        onError(`Unable to parse event ${name}.`);
      }
    });
  });

  source.onerror = () => {
    onError("Event stream disconnected.");
  };

  return source;
}

export async function explainRun(runId: string, question: string): Promise<ChatExplainResponse> {
  const response = await fetch(`${API_BASE}/api/v1/chat/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      run_id: runId,
      question,
    }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Explain call failed: ${response.status} ${message}`);
  }

  return (await response.json()) as ChatExplainResponse;
}
