"use client";

import { ProtocolResult } from "@/lib/types";

type Props = {
  results: ProtocolResult[];
};

const palette = ["#22d3ee", "#7dd3fc", "#34d399", "#fbbf24", "#fb7185", "#a3e635"];

export function LiveTrialChart({ results }: Props) {
  const selected = results.slice(0, 5);

  if (selected.length === 0) {
    return (
      <div className="chart-shell empty">
        <p>No trajectories yet. Start a run to stream protocol divergence.</p>
      </div>
    );
  }

  const allPoints = selected.flatMap((item) => item.trajectory.map((state) => state.hba1c_est));
  const yMin = Math.min(...allPoints) - 0.2;
  const yMax = Math.max(...allPoints) + 0.2;

  const toPath = (result: ProtocolResult, width: number, height: number) => {
    const len = result.trajectory.length || 1;
    return result.trajectory
      .map((state, index) => {
        const x = (index / (len - 1 || 1)) * width;
        const yScale = (state.hba1c_est - yMin) / (yMax - yMin || 1);
        const y = height - yScale * height;
        return `${x},${y}`;
      })
      .join(" ");
  };

  return (
    <div className="chart-shell">
      <div className="chart-head">
        <h3>180-Day HbA1c Divergence</h3>
        <p>Top protocols from agentic shortlist with safety-aware ranking.</p>
      </div>
      <svg viewBox="0 0 920 340" role="img" aria-label="Protocol trajectory chart">
        <defs>
          <linearGradient id="gridFade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(148,163,184,0.25)" />
            <stop offset="100%" stopColor="rgba(148,163,184,0.02)" />
          </linearGradient>
        </defs>

        {[0, 1, 2, 3, 4].map((row) => (
          <line
            key={row}
            x1={0}
            y1={row * 80 + 10}
            x2={920}
            y2={row * 80 + 10}
            stroke="url(#gridFade)"
            strokeWidth={1}
          />
        ))}

        {selected.map((result, index) => (
          <polyline
            key={result.protocol.protocol_id}
            points={toPath(result, 920, 320)}
            fill="none"
            stroke={palette[index % palette.length]}
            strokeWidth={index === 0 ? 4 : 2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
      </svg>
      <div className="chart-legend">
        {selected.map((result, index) => (
          <div key={result.protocol.protocol_id} className="legend-item">
            <span style={{ backgroundColor: palette[index % palette.length] }} />
            <p>
              {result.protocol.label}
              {result.score.disqualified ? " (blocked)" : ""}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
