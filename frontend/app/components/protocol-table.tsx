"use client";

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

export function ProtocolTable({ results }: Props) {
  if (results.length === 0) {
    return <p className="empty-copy">Protocol leaderboard will appear after simulation.</p>;
  }

  return (
    <div className="board-shell">
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
                      <a key={`${result.protocol.protocol_id}-${citeIndex}`} href={cite} target="_blank" rel="noreferrer">
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
    </div>
  );
}
