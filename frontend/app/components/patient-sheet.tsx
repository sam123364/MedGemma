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

  const setPreset = (type: "controlled" | "severe_uncontrolled" | "renal_impaired") => {
    if (type === "controlled") {
      setPatient({
        age: 52,
        sex: "female",
        bmi: 27.5,
        hba1c: 7.2,
        fasting_glucose: 145,
        systolic_bp: 130,
        diastolic_bp: 80,
        egfr: 92,
        alt: 28,
        adherence_probability: 0.85,
        comorbidities: ["hypertension"],
        meds_current: ["metformin"],
        objective: "Maintain glycemic control, avoid cardiovascular risk",
      });
      setComorbidText("hypertension");
      setMedsText("metformin");
    } else if (type === "severe_uncontrolled") {
      setPatient({
        age: 61,
        sex: "male",
        bmi: 34.2,
        hba1c: 9.8,
        fasting_glucose: 242,
        systolic_bp: 148,
        diastolic_bp: 92,
        egfr: 72,
        alt: 42,
        adherence_probability: 0.65,
        comorbidities: ["hypertension", "dyslipidemia", "obesity"],
        meds_current: ["metformin", "glimepiride"],
        objective: "Aggressively reduce HbA1c, minimize hypoglycemia risk, encourage weight loss",
      });
      setComorbidText("hypertension, dyslipidemia, obesity");
      setMedsText("metformin, glimepiride");
    } else if (type === "renal_impaired") {
      setPatient({
        age: 68,
        sex: "female",
        bmi: 29.8,
        hba1c: 8.5,
        fasting_glucose: 188,
        systolic_bp: 138,
        diastolic_bp: 82,
        egfr: 42.0,
        alt: 31,
        adherence_probability: 0.78,
        comorbidities: ["hypertension", "chronic-kidney-disease"],
        meds_current: ["insulin glargine"],
        objective: "Manage glycemic control while strictly respecting renal dose adjustments/contraindications",
      });
      setComorbidText("hypertension, chronic-kidney-disease");
      setMedsText("insulin glargine");
    }
  };

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

      {/* Preset Profiles Picker */}
      <div className="preset-bar" style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.85rem", alignSelf: "center", color: "var(--muted)", marginRight: "0.5rem", fontWeight: 500 }}>Presets:</span>
        <button type="button" className="preset-btn" onClick={() => setPreset("controlled")} style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", padding: "0.35rem 0.65rem", fontSize: "0.78rem", cursor: "pointer", fontWeight: 500 }}>
          Controlled Twin
        </button>
        <button type="button" className="preset-btn" onClick={() => setPreset("severe_uncontrolled")} style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", padding: "0.35rem 0.65rem", fontSize: "0.78rem", cursor: "pointer", fontWeight: 500 }}>
          Severe Uncontrolled Twin
        </button>
        <button type="button" className="preset-btn" onClick={() => setPreset("renal_impaired")} style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", padding: "0.35rem 0.65rem", fontSize: "0.78rem", cursor: "pointer", fontWeight: 500 }}>
          CKD Renal Impaired Twin
        </button>
      </div>

      <div className="sheet-grid">
        <label>
          Age (years)
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
          BMI (kg/m²)
          <input
            type="number"
            step="0.1"
            value={patient.bmi}
            onChange={(event) => setPatient((prev) => ({ ...prev, bmi: Number(event.target.value) }))}
          />
        </label>
        <label>
          HbA1c (%)
          <input
            type="number"
            step="0.1"
            value={patient.hba1c}
            onChange={(event) => setPatient((prev) => ({ ...prev, hba1c: Number(event.target.value) }))}
          />
        </label>
        <label>
          Fasting Glucose (mg/dL)
          <input
            type="number"
            value={patient.fasting_glucose}
            onChange={(event) => setPatient((prev) => ({ ...prev, fasting_glucose: Number(event.target.value) }))}
          />
        </label>
        <label>
          Systolic BP (mmHg)
          <input
            type="number"
            value={patient.systolic_bp}
            onChange={(event) => setPatient((prev) => ({ ...prev, systolic_bp: Number(event.target.value) }))}
          />
        </label>
        <label>
          Diastolic BP (mmHg)
          <input
            type="number"
            value={patient.diastolic_bp}
            onChange={(event) => setPatient((prev) => ({ ...prev, diastolic_bp: Number(event.target.value) }))}
          />
        </label>
        <label>
          eGFR (mL/min/1.73m²)
          <input
            type="number"
            step="0.1"
            value={patient.egfr}
            onChange={(event) => setPatient((prev) => ({ ...prev, egfr: Number(event.target.value) }))}
          />
        </label>
        <label>
          ALT (U/L)
          <input
            type="number"
            step="0.1"
            value={patient.alt}
            onChange={(event) => setPatient((prev) => ({ ...prev, alt: Number(event.target.value) }))}
          />
        </label>
        <label>
          Adherence Prob. (0 - 1)
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
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
          Comorbidities (comma separated list, e.g. hypertension, dyslipidemia)
          <input value={comorbidText} onChange={(event) => setComorbidText(event.target.value)} />
        </label>
        <label>
          Current Medications (comma separated list, e.g. metformin)
          <input value={medsText} onChange={(event) => setMedsText(event.target.value)} />
        </label>
        <label>
          Optimization Objective / Goals
          <textarea
            value={patient.objective}
            onChange={(event) => setPatient((prev) => ({ ...prev, objective: event.target.value }))}
            rows={2}
          />
        </label>
      </div>

      <button type="submit" className="launch-button" disabled={isRunning}>
        {isRunning ? "Running 1,000 in-silico trials..." : "Launch Astra-Gemma Run"}
      </button>
    </form>
  );
}
