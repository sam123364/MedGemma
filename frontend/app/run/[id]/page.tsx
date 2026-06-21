"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { BlackBoxWarning } from "@/components/black-box-warning";
import { DrGemmaChat } from "@/components/dr-gemma-chat";
import { LiveTrialChart } from "@/components/live-trial-chart";
import { PopulationMap } from "@/components/population-map";
import { ProtocolTable } from "@/components/protocol-table";
import { WorkflowTimeline } from "@/components/workflow-timeline";
import { fetchPopulationMap, fetchRunResult, streamRunEvents } from "@/lib/api";
import { PopulationMapArtifact, RunArtifact, RunEvent } from "@/lib/types";

type BlackBoxWarningItem = {
  protocolId: string;
  label: string;
  warning: string;
  code?: string | null;
};

export default function RunPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [events, setEvents] = useState<RunEvent[]>([]);
  const [result, setResult] = useState<RunArtifact | null>(null);
  const [populationMap, setPopulationMap] = useState<PopulationMapArtifact | null>(null);
  const [statusText, setStatusText] = useState("Initializing stream...");
  const [error, setError] = useState<string | null>(null);
  const [eventWarnings, setEventWarnings] = useState<BlackBoxWarningItem[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;

    let cancelled = false;

    const source = streamRunEvents(
      runId,
      (event) => {
        if (cancelled) return;
        setEvents((prev) => [...prev, event]);
        setStatusText(event.eventType);

        if (event.eventType === "run.failed") {
          setError(String(event.payload.error ?? "Run failed."));
          source.close();
        }

        if (event.eventType === "critic.done") {
          const rawWarnings = event.payload.black_box_warnings;
          if (Array.isArray(rawWarnings)) {
            const parsed: BlackBoxWarningItem[] = [];
            rawWarnings.forEach((item) => {
              if (!item || typeof item !== "object") {
                return;
              }
              const row = item as Record<string, unknown>;
              if (
                typeof row.protocol_id !== "string" ||
                typeof row.label !== "string" ||
                typeof row.warning !== "string"
              ) {
                return;
              }
              parsed.push({
                protocolId: row.protocol_id,
                label: row.label,
                warning: row.warning,
                code: typeof row.code === "string" ? row.code : null,
              });
            });
            setEventWarnings(parsed);
          }
        }

        if (event.eventType === "run.completed") {
          source.close();
          void loadResult();
          void loadPopulationMap();
        }
      },
      (message) => {
        if (!cancelled) {
          setStatusText(message);
        }
      },
    );

    eventSourceRef.current = source;

    const poll = setInterval(() => {
      void loadResult();
      void loadPopulationMap();
    }, 2000);

    async function loadResult() {
      try {
        const artifact = await fetchRunResult(runId);
        if (artifact && !cancelled) {
          setResult(artifact);
          setStatusText(`Run ${artifact.status}`);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load run result.");
        }
      }
    }

    async function loadPopulationMap() {
      try {
        const map = await fetchPopulationMap(runId);
        if (map && !cancelled) {
          setPopulationMap(map);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load population map.");
        }
      }
    }

    void loadResult();
    void loadPopulationMap();

    return () => {
      cancelled = true;
      clearInterval(poll);
      source.close();
    };
  }, [runId]);

  const topProtocol = useMemo(() => result?.results?.[0], [result]);
  const resultWarnings = useMemo<BlackBoxWarningItem[]>(
    () =>
      (result?.results ?? [])
        .filter((item) => typeof item.black_box_warning === "string" && item.black_box_warning.length > 0)
        .map((item) => ({
          protocolId: item.protocol.protocol_id,
          label: item.protocol.label,
          warning: item.black_box_warning as string,
          code: item.black_box_code ?? null,
        })),
    [result],
  );
  const warnings = resultWarnings.length > 0 ? resultWarnings : eventWarnings;

  const progressPercentage = useMemo(() => {
    switch (statusText) {
      case "init_run":
      case "run.started":
        return 10;
      case "retrieve_evidence":
        return 30;
      case "generate_protocols":
      case "protocols.generated":
        return 50;
      case "run_simulation":
      case "coarse.progress":
      case "highfidelity.progress":
        return 70;
      case "evaluate_safety":
        return 85;
      case "score_and_rank":
      case "critic.done":
        return 95;
      case "Run completed":
      case "completed":
        return 100;
      default:
        return 5;
    }
  }, [statusText]);

  return (
    <main className="run-root">
      <header className="run-header">
        <div>
          <p className="eyebrow">Run ID</p>
          <h1>{runId}</h1>
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginTop: "0.4rem" }}>
            <p className="status-pill">Workflow Status: {statusText}</p>
            {progressPercentage < 100 && (
              <div style={{ width: "160px", height: "8px", background: "#e2e8f0", borderRadius: "99px", overflow: "hidden", position: "relative" }}>
                <div style={{ width: `${progressPercentage}%`, height: "100%", background: "var(--accent-a)", transition: "width 0.4s ease" }} />
              </div>
            )}
          </div>
        </div>
        <Link className="ghost-link" href="/">
          New patient run
        </Link>
      </header>

      {error ? <p className="error-banner">{error}</p> : null}

      <div className="run-grid-full">
        <LiveTrialChart results={result?.results ?? []} />
      </div>

      <BlackBoxWarning warnings={warnings} />

      <section className="recommendation-shell">
        <h2>Final Recommendation</h2>
        <p>{result?.final_recommendation ?? "Recommendation pending..."}</p>
        {topProtocol ? (
          <article className="top-card">
            <h3>{topProtocol.protocol.label}</h3>
            <p>{topProtocol.explanation}</p>
            <small>Score: {topProtocol.score.total_score.toFixed(3)}</small>
          </article>
        ) : null}
      </section>

      <ProtocolTable results={result?.results ?? []} />

      <PopulationMap artifact={populationMap ?? result?.population_map ?? null} />

      <DrGemmaChat runId={runId} />

      <footer className="run-footer">
        <p>
          {result?.disclaimer ??
            "Research prototype only. This app provides simulation output and does not provide medical advice."}
        </p>
      </footer>
    </main>
  );
}
