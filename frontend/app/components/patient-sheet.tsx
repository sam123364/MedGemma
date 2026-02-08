"use client";

import { FormEvent, useMemo, useState } from "react";

import { PatientTwinInput } from "@/lib/types";

type Props = {
  onRun: (payload: PatientTwinInput) => Promise<void>;
  isRunning: boolean;
};

const defaultPatient: PatientTwinInput = {
  age: 57,
  sex: "male",
  bmi: 31.4,
  hba1c: 9.4,
  fasting_glucose: 214,
  systolic_bp: 140,
  diastolic_bp: 88,
  egfr: 76,
  alt: 34,
  adherence_probability: 0.72,
  comorbidities: ["hypertension"],
  meds_current: ["metformin"],
  objective: "maximize glycemic control while minimizing adverse risk",
};

export function PatientSheet({ onRun, isRunning }: Props) {
  const [patient, setPatient] = useState<PatientTwinInput>(defaultPatient);
  const [comorbidText, setComorbidText] = useState(defaultPatient.comorbidities.join(", "));
  const [medsText, setMedsText] = useState(defaultPatient.meds_current.join(", "));

  const profilePower = useMemo(() => {
    const riskPressure = (patient.hba1c - 6.5) * 7 + Math.max(0, 130 - patient.egfr) * 0.2 + patient.bmi * 0.4;
    return Math.max(0, Math.min(100, Math.round(riskPressure)));
  }, [patient]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const clean = {
      ...patient,
      comorbidities: comorbidText
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      meds_current: medsText
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };
    await onRun(clean);
  };

  return (
    <form className="patient-sheet" onSubmit={submit}>
      <div className="sheet-header">
        <div>
          <p className="eyebrow">Digital Twin Builder</p>
          <h2>Patient Archetype Console</h2>
        </div>
        <div className="threat-meter" title="Projected protocol complexity score">
          <span>Complexity</span>
          <strong>{profilePower}</strong>
        </div>
      </div>

      <div className="sheet-grid">
        <label>
          Age
          <input
            type="number"
            value={patient.age}
            onChange={(event) => setPatient((prev) => ({ ...prev, age: Number(event.target.value) }))}
          />
        </label>
        <label>
          Sex
          <select
            value={patient.sex}
            onChange={(event) => setPatient((prev) => ({ ...prev, sex: event.target.value as PatientTwinInput["sex"] }))}
          >
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>
          BMI
          <input
            type="number"
            step="0.1"
            value={patient.bmi}
            onChange={(event) => setPatient((prev) => ({ ...prev, bmi: Number(event.target.value) }))}
          />
        </label>
        <label>
          HbA1c
          <input
            type="number"
            step="0.1"
            value={patient.hba1c}
            onChange={(event) => setPatient((prev) => ({ ...prev, hba1c: Number(event.target.value) }))}
          />
        </label>
        <label>
          Fasting Glucose
          <input
            type="number"
            value={patient.fasting_glucose}
            onChange={(event) => setPatient((prev) => ({ ...prev, fasting_glucose: Number(event.target.value) }))}
          />
        </label>
        <label>
          Systolic BP
          <input
            type="number"
            value={patient.systolic_bp}
            onChange={(event) => setPatient((prev) => ({ ...prev, systolic_bp: Number(event.target.value) }))}
          />
        </label>
        <label>
          Diastolic BP
          <input
            type="number"
            value={patient.diastolic_bp}
            onChange={(event) => setPatient((prev) => ({ ...prev, diastolic_bp: Number(event.target.value) }))}
          />
        </label>
        <label>
          eGFR
          <input
            type="number"
            step="0.1"
            value={patient.egfr}
            onChange={(event) => setPatient((prev) => ({ ...prev, egfr: Number(event.target.value) }))}
          />
        </label>
        <label>
          ALT
          <input
            type="number"
            step="0.1"
            value={patient.alt}
            onChange={(event) => setPatient((prev) => ({ ...prev, alt: Number(event.target.value) }))}
          />
        </label>
        <label>
          Adherence Probability
          <input
            type="number"
            step="0.01"
            value={patient.adherence_probability}
            onChange={(event) =>
              setPatient((prev) => ({
                ...prev,
                adherence_probability: Number(event.target.value),
              }))
            }
          />
        </label>
      </div>

      <div className="sheet-stack">
        <label>
          Comorbidities (comma separated)
          <input value={comorbidText} onChange={(event) => setComorbidText(event.target.value)} />
        </label>
        <label>
          Current Medications (comma separated)
          <input value={medsText} onChange={(event) => setMedsText(event.target.value)} />
        </label>
        <label>
          Optimization Objective
          <textarea
            value={patient.objective}
            onChange={(event) => setPatient((prev) => ({ ...prev, objective: event.target.value }))}
            rows={3}
          />
        </label>
      </div>

      <button type="submit" className="launch-button" disabled={isRunning}>
        {isRunning ? "Running 1,000 in-silico trials..." : "Launch Astra-Gemma Run"}
      </button>
    </form>
  );
}
