from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.schemas import PatientTwinInput, ProtocolCandidate, SafetyFlag


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(pattern)}\b", text) for pattern in patterns)


def _normalize_med_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s\-]", " ", name.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    aliases = {
        "metformin": "metformin",
        "semaglutide": "semaglutide",
        "liraglutide": "liraglutide",
        "dulaglutide": "dulaglutide",
        "exenatide": "exenatide",
        "tirzepatide": "tirzepatide",
        "empagliflozin": "empagliflozin",
        "dapagliflozin": "dapagliflozin",
        "canagliflozin": "canagliflozin",
        "ertugliflozin": "ertugliflozin",
        "sitagliptin": "sitagliptin",
        "linagliptin": "linagliptin",
        "saxagliptin": "saxagliptin",
        "alogliptin": "alogliptin",
        "glimepiride": "glimepiride",
        "glipizide": "glipizide",
        "glyburide": "glyburide",
        "gliclazide": "gliclazide",
        "pioglitazone": "pioglitazone",
        "insulin glargine": "insulin glargine",
        "insulin detemir": "insulin detemir",
        "insulin degludec": "insulin degludec",
        "nph insulin": "nph insulin",
    }

    for alias, canonical in aliases.items():
        if alias in normalized:
            return canonical
    return normalized


def _med_class(med: str) -> str:
    if med in {"semaglutide", "liraglutide", "dulaglutide", "exenatide", "tirzepatide"}:
        return "glp1"
    if med in {"empagliflozin", "dapagliflozin", "canagliflozin", "ertugliflozin"}:
        return "sglt2"
    if med in {"sitagliptin", "linagliptin", "saxagliptin", "alogliptin"}:
        return "dpp4"
    if med in {"glimepiride", "glipizide", "glyburide", "gliclazide"}:
        return "sulfonylurea"
    if med == "pioglitazone":
        return "tzd"
    if med == "metformin":
        return "metformin"
    if "insulin" in med:
        return "insulin"
    return "other"


def _med_set(protocol: ProtocolCandidate) -> set[str]:
    return {_normalize_med_name(med) for med in protocol.meds}


@dataclass
class ComorbidityProfile:
    hypertension: bool = False
    ckd: bool = False
    advanced_ckd: bool = False
    ascvd: bool = False
    heart_failure: bool = False
    obesity: bool = False
    liver_metabolic_disease: bool = False


@dataclass
class GuidelineAssessment:
    efficacy_bonus: float = 0.0
    safety_penalty: float = 0.0
    adherence_penalty: float = 0.0
    soft_flags: list[SafetyFlag] = field(default_factory=list)
    hard_flags: list[SafetyFlag] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)


def build_profile(patient: PatientTwinInput) -> ComorbidityProfile:
    text = " ".join(patient.comorbidities).lower()

    hypertension = (
        patient.systolic_bp >= 130
        or patient.diastolic_bp >= 80
        or _contains_any(text, ("hypertension", "high blood pressure", "htn"))
    )
    ckd = patient.egfr < 60 or _contains_any(
        text,
        ("ckd", "chronic kidney disease", "kidney disease", "renal disease", "nephropathy", "albuminuria"),
    )
    advanced_ckd = patient.egfr < 30
    ascvd = _contains_any(
        text,
        (
            "ascvd",
            "coronary artery disease",
            "cad",
            "myocardial infarction",
            "mi",
            "stroke",
            "tia",
            "peripheral artery disease",
            "pad",
            "atherosclerosis",
        ),
    )
    heart_failure = _contains_any(
        text,
        ("heart failure", "congestive heart failure", "chf", "hfrEF", "hfpef"),
    )
    obesity = patient.bmi >= 30 or _contains_any(text, ("obesity", "overweight", "metabolic syndrome"))
    liver_metabolic_disease = _contains_any(text, ("masld", "mash", "nafld", "fatty liver"))

    return ComorbidityProfile(
        hypertension=hypertension,
        ckd=ckd,
        advanced_ckd=advanced_ckd,
        ascvd=ascvd,
        heart_failure=heart_failure,
        obesity=obesity,
        liver_metabolic_disease=liver_metabolic_disease,
    )


def assess_protocol_against_profile(
    patient: PatientTwinInput,
    protocol: ProtocolCandidate,
) -> GuidelineAssessment:
    profile = build_profile(patient)
    meds = _med_set(protocol)
    current_meds = {_normalize_med_name(med) for med in patient.meds_current}
    current_meds.discard("")

    def add_soft_flag(code: str, message: str) -> None:
        out.soft_flags.append(
            SafetyFlag(
                protocol_id=protocol.protocol_id,
                day=0,
                severity="medium",
                code=code,
                message=message,
                disqualifying=False,
            )
        )

    has_sglt2 = any(med in meds for med in {"empagliflozin", "dapagliflozin", "canagliflozin", "ertugliflozin"})
    has_glp1 = any(
        med in meds for med in {"semaglutide", "liraglutide", "dulaglutide", "exenatide", "tirzepatide"}
    )
    has_tzd = "pioglitazone" in meds
    has_su = any(med in meds for med in {"glimepiride", "glipizide", "glyburide"})
    has_basal_insulin = any("insulin" in med for med in meds)

    out = GuidelineAssessment()
    mismatch_reasons: list[str] = []
    protocol_classes = {_med_class(med) for med in meds}
    current_classes = {_med_class(med) for med in current_meds}

    overlap = meds & current_meds
    if overlap:
        continuity_bonus = min(0.04, 0.02 * len(overlap))
        out.adherence_penalty -= continuity_bonus
        out.rationale.append(
            "Medication continuity with current regimen improves transition adherence "
            f"({', '.join(sorted(overlap))})."
        )

    if "dpp4" in current_classes and "glp1" in protocol_classes:
        out.safety_penalty += 0.08
        out.adherence_penalty += 0.02
        mismatch_reasons.append("Current DPP-4 therapy overlaps with protocol GLP-1 strategy.")
        add_soft_flag(
            "DPP4_GLP1_OVERLAP",
            "Current DPP-4 therapy may overlap with protocol GLP-1 mechanism without added benefit.",
        )

    if "glp1" in current_classes and "dpp4" in protocol_classes:
        out.safety_penalty += 0.08
        out.adherence_penalty += 0.02
        mismatch_reasons.append("Current GLP-1 therapy overlaps with protocol DPP-4 strategy.")
        add_soft_flag(
            "GLP1_DPP4_OVERLAP",
            "Current GLP-1 therapy may overlap with protocol DPP-4 mechanism without added benefit.",
        )

    if ("insulin" in current_classes and "sulfonylurea" in protocol_classes) or (
        "sulfonylurea" in current_classes and "insulin" in protocol_classes
    ):
        out.safety_penalty += 0.07
        out.adherence_penalty += 0.03
        mismatch_reasons.append("Current/proposed insulin plus sulfonylurea stack increases hypoglycemia burden.")
        add_soft_flag(
            "HYPOGLYCEMIA_STACK_RISK",
            "Combining current insulin/sulfonylurea exposure with protocol intensification raises hypoglycemia risk.",
        )

    duplicate_classes = {"sglt2", "glp1", "dpp4", "sulfonylurea", "tzd"}
    for med_class in duplicate_classes:
        if med_class not in current_classes or med_class not in protocol_classes:
            continue
        protocol_in_class = {med for med in meds if _med_class(med) == med_class}
        current_in_class = {med for med in current_meds if _med_class(med) == med_class}
        if protocol_in_class.isdisjoint(current_in_class):
            out.safety_penalty += 0.04
            out.adherence_penalty += 0.02
            mismatch_reasons.append(f"Potential within-class duplication against current {med_class} therapy.")
            add_soft_flag(
                f"CLASS_DUPLICATION_{med_class.upper()}",
                f"Protocol may duplicate current {med_class} class therapy without clear incremental mechanism benefit.",
            )

    if profile.heart_failure and has_tzd:
        out.hard_flags.append(
            SafetyFlag(
                protocol_id=protocol.protocol_id,
                day=0,
                severity="critical",
                code="HF_TZD_CONTRAINDICATION",
                message="Pioglitazone can worsen fluid retention in heart failure.",
                disqualifying=True,
            )
        )
        out.rationale.append("Heart failure profile conflicts with pioglitazone due to fluid-retention risk.")

    if profile.ckd:
        if patient.egfr >= 20 and has_sglt2:
            out.efficacy_bonus += 0.06
            out.rationale.append("CKD profile favors SGLT2 for kidney/cardiovascular risk reduction.")
        elif has_glp1:
            out.efficacy_bonus += 0.03
            out.rationale.append("CKD profile uses GLP-1 as a cardio-metabolic fallback when SGLT2 fit is weaker.")
        else:
            out.safety_penalty += 0.08
            mismatch_reasons.append("CKD profile without SGLT2/GLP-1 cardiometabolic coverage.")

    if profile.ascvd:
        if has_sglt2 or has_glp1:
            out.efficacy_bonus += 0.05
            out.rationale.append("ASCVD profile favors agents with proven cardiovascular benefit.")
        else:
            out.safety_penalty += 0.06
            mismatch_reasons.append("ASCVD profile lacks GLP-1/SGLT2 cardiovascular-preferred agent.")

    if profile.hypertension:
        if has_sglt2:
            out.efficacy_bonus += 0.02
            out.rationale.append("Hypertension profile may benefit from modest BP/cardiorenal effect of SGLT2.")
        if has_tzd:
            out.safety_penalty += 0.05
            mismatch_reasons.append("Hypertension profile penalizes TZD due to edema/volume concerns.")

    if profile.obesity:
        if has_glp1:
            out.efficacy_bonus += 0.06
            out.rationale.append("Obesity profile favors GLP-1 for stronger glycemic plus weight effects.")
        if has_su or has_basal_insulin or has_tzd:
            out.safety_penalty += 0.03
            out.adherence_penalty += 0.04
            mismatch_reasons.append("Obesity profile penalizes weight-gain-prone options (SU/insulin/TZD).")

    if profile.liver_metabolic_disease and has_glp1:
        out.efficacy_bonus += 0.03
        out.rationale.append("Metabolic liver disease profile may benefit from GLP-1 cardiometabolic effects.")

    if patient.age >= 75 and (has_su or has_basal_insulin):
        out.safety_penalty += 0.05
        out.adherence_penalty += 0.03
        mismatch_reasons.append("Older-adult profile penalizes hypoglycemia-prone regimens (SU/insulin).")

    if mismatch_reasons:
        out.rationale.append("Guideline mismatch: " + " ".join(mismatch_reasons))

    return out
