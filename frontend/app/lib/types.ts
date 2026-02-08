export type Sex = "female" | "male" | "other";

export type PatientTwinInput = {
  schema_version?: string;
  patient_id?: string;
  age: number;
  sex: Sex;
  bmi: number;
  hba1c: number;
  fasting_glucose: number;
  systolic_bp: number;
  diastolic_bp: number;
  egfr: number;
  alt: number;
  adherence_probability: number;
  comorbidities: string[];
  meds_current: string[];
  objective: string;
};

export type RunStartResponse = {
  schema_version: string;
  run_id: string;
  status: "queued" | "running";
};

export type RunEvent = {
  id: number;
  eventType: string;
  timestamp?: string;
  payload: Record<string, unknown>;
};

export type DailyState = {
  day: number;
  hba1c_est: number;
  fasting_glucose_est: number;
  bmi_est: number;
  systolic_bp_est: number;
  diastolic_bp_est: number;
  egfr_est: number;
  alt_est: number;
  adherence_est: number;
  adverse_events: string[];
  severe_event: boolean;
  alive: boolean;
};

export type SafetyFlag = {
  protocol_id: string;
  day: number;
  severity: "low" | "medium" | "high" | "critical";
  code: string;
  message: string;
  disqualifying: boolean;
};

export type ProtocolScore = {
  protocol_id: string;
  efficacy_score: number;
  safety_score: number;
  adherence_score: number;
  robustness_score: number;
  total_score: number;
  disqualified: boolean;
};

export type ProtocolCandidate = {
  protocol_id: string;
  label: string;
  meds: string[];
  lifestyle_plan: string;
  rationale: string;
  citations: string[];
  citation_source_ids: string[];
};

export type ProtocolResult = {
  protocol: ProtocolCandidate;
  coarse_summary: {
    protocol_id: string;
    expected_hba1c_delta: number;
    expected_glucose_delta: number;
    adverse_event_rate: number;
    robustness_index: number;
    mortality_proxy_rate: number;
    safety_risk_index: number;
    trials: number;
  };
  trajectory: DailyState[];
  flags: SafetyFlag[];
  score: ProtocolScore;
  explanation: string;
  black_box_warning?: string | null;
  black_box_code?: string | null;
};

export type RunArtifact = {
  schema_version: string;
  run_id: string;
  status: "completed" | "failed" | "queued" | "running";
  patient: PatientTwinInput;
  results: ProtocolResult[];
  final_recommendation: string;
  disclaimer: string;
  calibrations?: Record<string, { reasoning: string }>;
};

export type ChatExplainResponse = {
  schema_version: string;
  run_id: string;
  answer: string;
  grounded_source_ids: string[];
};
