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

      {/* 2D Efficacy vs Risk Scatter Map */}
      <div style={{ marginTop: "1.5rem", borderTop: "1px solid #e2e8f0", paddingTop: "1.25rem" }}>
        <h4 style={{ margin: "0 0 0.25rem", fontSize: "0.88rem", fontWeight: 600 }}>Efficacy vs. Safety Risk Analysis</h4>
        <p style={{ fontSize: "0.78rem", color: "var(--muted)", marginBottom: "0.75rem" }}>
          Interactive trade-off grid. Higher right = Better glycemic control. Lower down = Lower safety penalty (ideal quadrant is bottom-right).
        </p>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          {/* Scatter Matrix */}
          <div style={{ position: "relative", width: "420px", height: "140px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "6px" }}>
            <span style={{ position: "absolute", bottom: "4px", right: "8px", fontSize: "0.64rem", color: "var(--muted)", fontWeight: 500 }}>High Efficacy →</span>
            <span style={{ position: "absolute", top: "4px", left: "8px", fontSize: "0.64rem", color: "var(--muted)", fontWeight: 500 }}>↑ High Risk Penalty</span>
            
            {/* Center Grid Lines */}
            <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, borderLeft: "1px dashed #cbd5e1" }} />
            <div style={{ position: "absolute", top: "50%", left: 0, right: 0, borderTop: "1px dashed #cbd5e1" }} />

            {selected.map((result, index) => {
              // Normalize metrics to fit coordinate coordinates
              const rawEff = result.score.efficacy_score; // e.g. 0 to 5
              const rawSaf = result.score.safety_score;   // e.g. 0 to 5
              
              const pctX = Math.min(90, Math.max(10, (rawEff / 5) * 100));
              const pctY = Math.min(90, Math.max(10, 100 - (rawSaf / 5) * 100)); // Invert Y so lower = safer (lower penalty)

              return (
                <div 
                  key={`dot-${result.protocol.protocol_id}`}
                  style={{
                    position: "absolute",
                    left: `${pctX}%`,
                    top: `${pctY}%`,
                    width: "12px",
                    height: "12px",
                    background: palette[index % palette.length],
                    borderRadius: "999px",
                    transform: "translate(-50%, -50%)",
                    border: "2px solid #ffffff",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.15)"
                  }}
                  title={`${result.protocol.label} (Eff: ${rawEff.toFixed(2)}, Safety Penalty: ${rawSaf.toFixed(2)})`}
                />
              );
            })}
          </div>

          {/* Quick Stats list */}
          <div style={{ flex: 1, display: "grid", gap: "0.35rem" }}>
            {selected.slice(0, 3).map((result, index) => (
              <div key={`stat-${result.protocol.protocol_id}`} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.76rem" }}>
                <span style={{ color: "var(--fg-0)", fontWeight: 500 }}>
                  {result.protocol.label.slice(0, 28)}...
                </span>
                <span style={{ color: "var(--muted)" }}>
                  Eff: {result.score.efficacy_score.toFixed(2)} | Risk: {result.score.safety_score.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
