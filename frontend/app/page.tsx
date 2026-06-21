"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PatientSheet } from "@/components/patient-sheet";
import { createRun } from "@/lib/api";
import { PatientTwinInput } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const launch = async (payload: PatientTwinInput) => {
    setIsRunning(true);
    setError(null);
    try {
      const run = await createRun(payload, 10);
      router.push(`/run/${run.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run launch failed");
      setIsRunning(false);
    }
  };

  return (
    <main className="home-root">
      <section className="hero">
        <p className="eyebrow">Clinical Research Sandbox</p>
        <h1>Astra-Gemma In-Silico Simulator</h1>
        <p>
          Designed for clinical researchers and medical educators. Build a synthetic patient profile below to simulate, 
          rank, and analyze the 180-day efficacy and safety of custom Type 2 Diabetes treatment protocols.
        </p>
      </section>

      <PatientSheet onRun={launch} isRunning={isRunning} />

      {error ? <p className="error-banner">{error}</p> : null}

      <aside className="compliance-note">
        <h3>Research Sandbox Scope</h3>
        <p>
          This is an educational prototype exploring AI-driven medical simulation. It utilizes synthetic patient twins 
          and mock data endpoints to evaluate therapeutic logic. All simulation insights and recommendations are for 
          research purposes and do not represent clinical medical advice.
        </p>
      </aside>
    </main>
  );
}
