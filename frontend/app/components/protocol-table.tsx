"use client";

import { useState } from "react";
import { ProtocolResult } from "@/lib/types";

type Props = {
  results: ProtocolResult[];
};

function severityTone(totalFlags: number): string {
  if (totalFlags >= 8) return "critical";
  if (totalFlags >= 4) return "high";
  if (totalFlags >= 2) return "medium";
  return "low";
}

// Guideline Mock summaries database mapping
const GUIDELINE_SUMMARIES: Record<string, string> = {
  "E-ADA-2025": "ADA 2025: Recommends early combination therapy for HbA1c > 1.5% above target. Prioritizes GLP-1 RA / SGLT2i with proven CVD benefit.",
  "E-PUBMED-001": "Clinical trial data confirming robust HbA1c reduction when combining metformin and semaglutide with minimal hypoglycemia risk.",
  "E-KDIGO-2024": "KDIGO 2024: Prefers SGLT2 inhibitors as first-line therapy for patients with chronic kidney disease (eGFR >= 20) to slow renal decline.",
  "E-ADA-CKD": "ADA Renal Guidelines: Avoid Metformin initiation if eGFR < 45. Discontinue completely if eGFR drops below 30.",
  "E-EASD-2024": "EASD Consensus: Promotes weight-management target optimization alongside glycemic targets. Recommends high-potency GLP-1 RAs.",
  "default": "ADA / EASD clinical practice recommendation supporting individual treatment prioritization based on comorbidity indicators."
};

export function ProtocolTable({ results }: Props) {
  const [hoveredCitation, setHoveredCitation] = useState<{ id: string; x: number; y: number } | null>(null);
  const [hoveredText, setHoveredText] = useState("");

  if (results.length === 0) {
    return <p className="empty-copy">Protocol leaderboard will appear after simulation.</p>;
  }

  const handleMouseEnter = (event: React.MouseEvent, citationUrl: string) => {
    // Extract a mock ID string key from the URL or index for summary matching
    let key = "default";
    if (citationUrl.includes("ADA")) key = "E-ADA-2025";
    if (citationUrl.includes("pubmed")) key = "E-PUBMED-001";
    if (citationUrl.includes("kdigo")) key = "E-KDIGO-2024";
    if (citationUrl.includes("easd")) key = "E-EASD-2024";

    const rect = event.currentTarget.getBoundingClientRect();
    setHoveredCitation({
      id: citationUrl,
      x: rect.left + window.scrollX,
      y: rect.top + window.scrollY - 80
    });
    setHoveredText(GUIDELINE_SUMMARIES[key] || GUIDELINE_SUMMARIES["default"]);
  };

  return (
    <div className="board-shell" style={{ position: "relative" }}>
      <h3>Ranked Protocol Board</h3>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Protocol</th>
            <th>Total Score</th>
            <th>Efficacy</th>
            <th>Safety</th>
            <th>Flags</th>
            <th>Citations</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result, index) => {
            const flagCount = result.flags.length;
            return (
              <tr key={result.protocol.protocol_id} className={result.score.disqualified ? "blocked" : ""}>
                <td>{index + 1}</td>
                <td>
                  <strong>{result.protocol.label}</strong>
                  <p>{result.protocol.meds.join(" + ")}</p>
                </td>
                <td>{result.score.total_score.toFixed(3)}</td>
                <td>{result.score.efficacy_score.toFixed(3)}</td>
                <td>{result.score.safety_score.toFixed(3)}</td>
                <td>
                  <span className={`risk-tag ${severityTone(flagCount)}`}>{flagCount}</span>
                </td>
                <td>
                  <div className="citation-stack">
                    {result.protocol.citations.slice(0, 2).map((cite, citeIndex) => (
                      <a 
                        key={`${result.protocol.protocol_id}-${citeIndex}`} 
                        href={cite} 
                        target="_blank" 
                        rel="noreferrer"
                        onMouseEnter={(e) => handleMouseEnter(e, cite)}
                        onMouseLeave={() => setHoveredCitation(null)}
                        style={{ position: "relative", cursor: "help" }}
                      >
                        Source {citeIndex + 1}
                      </a>
                    ))}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Floating Citation Hover Card */}
      {hoveredCitation && (
        <div style={{
          position: "absolute",
          left: `${hoveredCitation.x - 140}px`,
          top: `${hoveredCitation.y - 120}px`,
          width: "280px",
          background: "#1e293b",
          color: "#f8fafc",
          padding: "0.75rem",
          borderRadius: "6px",
          boxShadow: "0 10px 15px -3px rgba(0,0,0,0.3)",
          zIndex: 1000,
          fontSize: "0.76rem",
          lineHeight: "1.4",
          border: "1px solid #475569"
        }}>
          <strong style={{ color: "#38bdf8", display: "block", marginBottom: "0.25rem" }}>Clinical Guideline Insight:</strong>
          {hoveredText}
        </div>
      )}
    </div>
  );
}
