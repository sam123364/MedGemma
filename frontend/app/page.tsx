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
        <p className="eyebrow">Astra-Gemma</p>
        <h1>Autonomous In-Silico Trial Engine</h1>
        <p>
          Build a synthetic patient twin, launch 1,000 coarse trial trajectories, and watch MedGemma-driven
          protocol intelligence rank personalized treatment options live.
        </p>
      </section>

      <PatientSheet onRun={launch} isRunning={isRunning} />

      {error ? <p className="error-banner">{error}</p> : null}

      <aside className="compliance-note">
        <h3>Safety & Compliance</h3>
        <p>
          Research prototype only. Synthetic profiles only. Outputs are not medical advice and must not be used for
          clinical decision-making.
        </p>
      </aside>
    </main>
  );
}
