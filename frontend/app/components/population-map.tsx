"use client";

import { CSSProperties, Fragment } from "react";

import { PopulationMapArtifact } from "@/lib/types";

type Props = {
  artifact: PopulationMapArtifact | null;
};

const PROTOCOL_COLORS = ["#22d3ee", "#34d399", "#fbbf24", "#fb7185", "#60a5fa", "#f97316", "#14b8a6", "#a78bfa"];

function tone(margin: number): string {
  if (margin >= 0.2) return "high";
  if (margin >= 0.1) return "medium";
  return "low";
}

function uniqSorted(values: number[], digits = 1): number[] {
  return Array.from(new Set(values.map((value) => Number(value.toFixed(digits))))).sort((a, b) => a - b);
}

function cellAxisKey(hba1c: number, egfr: number): string {
  return `${hba1c.toFixed(1)}|${egfr.toFixed(1)}`;
}

export function PopulationMap({ artifact }: Props) {
  if (!artifact || artifact.cells.length === 0) {
    return (
      <section className="population-map-shell">
        <h3>Recommendation Stability Across Patient Variants</h3>
        <p>No population map yet. It appears after ranking completes.</p>
      </section>
    );
  }

  const ageAxis = uniqSorted(artifact.axes.age ?? artifact.cells.map((cell) => cell.age), 0);
  const egfrAxis = uniqSorted(artifact.axes.egfr ?? artifact.cells.map((cell) => cell.egfr), 1);
  const hba1cAxis = uniqSorted(artifact.axes.hba1c ?? artifact.cells.map((cell) => cell.hba1c), 1);

  const groupedByAge = new Map<number, Map<string, (typeof artifact.cells)[number]>>();
  for (const age of ageAxis) {
    groupedByAge.set(age, new Map());
  }

  for (const cell of artifact.cells) {
    const age = Number(cell.age.toFixed(0));
    const bucket = groupedByAge.get(age) ?? new Map<string, (typeof artifact.cells)[number]>();
    const key = cellAxisKey(cell.hba1c, cell.egfr);
    const existing = bucket.get(key);
    if (!existing || cell.confidence_margin > existing.confidence_margin) {
      bucket.set(key, cell);
    }
    groupedByAge.set(age, bucket);
  }

  const protocolCounts = new Map<string, number>();
  for (const age of ageAxis) {
    const bucket = groupedByAge.get(age);
    if (!bucket) continue;
    for (const cell of bucket.values()) {
      const key = cell.top_protocol_label;
      protocolCounts.set(key, (protocolCounts.get(key) ?? 0) + 1);
    }
  }

  const winners = Array.from(protocolCounts.entries()).sort((a, b) => b[1] - a[1]);
  const protocolColors = new Map<string, string>();
  winners.forEach(([label], index) => {
    protocolColors.set(label, PROTOCOL_COLORS[index % PROTOCOL_COLORS.length]);
  });

  let renderedCells = 0;
  let blockedCells = 0;
  for (const age of ageAxis) {
    const bucket = groupedByAge.get(age);
    if (!bucket) continue;
    renderedCells += bucket.size;
    for (const cell of bucket.values()) {
      if (cell.disqualified_count > 0) blockedCells += 1;
    }
  }

  return (
    <section className="population-map-shell">
      <div className="population-map-head">
        <h3>Recommendation Stability Across Patient Variants</h3>
        <p>27 synthetic neighbors (age x eGFR x HbA1c) show where the top protocol shifts.</p>
      </div>

      <div className="population-map-meta">
        <span>Rendered variants: {renderedCells}/27</span>
        <span>Age bins: {ageAxis.join(" / ")}</span>
        <span>eGFR bins: {egfrAxis.join(" / ")}</span>
        <span>HbA1c bins: {hba1cAxis.join(" / ")}</span>
        <span>Cells with safety blocks: {blockedCells}</span>
      </div>

      <div className="population-map-legend">
        {winners.slice(0, 6).map(([label, count]) => (
          <span key={label}>
            <i style={{ backgroundColor: protocolColors.get(label) ?? "#22d3ee" }} aria-hidden />
            {label}: {count}/{renderedCells || 1}
          </span>
        ))}
      </div>

      <div className="population-map-grid">
        {ageAxis.map((age) => {
          const ageMap = groupedByAge.get(age) ?? new Map<string, (typeof artifact.cells)[number]>();
          return (
            <article key={age} className="population-age-block">
              <h4>Age {age}</h4>
              <div className="population-matrix">
                <div className="population-corner">HbA1c / eGFR</div>
                {egfrAxis.map((egfr) => (
                  <div key={`col-${age}-${egfr}`} className="population-col-head">
                    {egfr}
                  </div>
                ))}

                {hba1cAxis.map((hba1c) => (
                  <Fragment key={`row-${age}-${hba1c}`}>
                    <div className="population-row-head">{hba1c}</div>
                    {egfrAxis.map((egfr) => {
                      const cell = ageMap.get(cellAxisKey(hba1c, egfr));
                      if (!cell) {
                        return (
                          <div key={`empty-${age}-${hba1c}-${egfr}`} className="population-cell population-cell-empty">
                            <small>No data</small>
                          </div>
                        );
                      }

                      const color = protocolColors.get(cell.top_protocol_label) ?? "#22d3ee";
                      const style = { "--protocol-color": color } as CSSProperties;

                      return (
                        <div key={cell.cell_id} className={`population-cell ${tone(cell.confidence_margin)}`} style={style}>
                          <strong title={cell.top_protocol_label}>{cell.top_protocol_label}</strong>
                          <p>Margin {cell.confidence_margin.toFixed(3)}</p>
                          <small>Blocked {cell.disqualified_count}</small>
                        </div>
                      );
                    })}
                  </Fragment>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
