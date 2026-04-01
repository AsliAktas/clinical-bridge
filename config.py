"""
Clinical Bridge - Configuration Module

Single source of truth for all constants, thresholds, and terminology mappings.
Designed for extensibility: adding new conditions requires only adding entries
to the dictionaries below — no architectural changes needed.
"""

from dataclasses import dataclass, field
from typing import Dict


# ─── Risk Stratification Thresholds ─────────────────────────────────────────
# These thresholds determine how a normalized risk score (0.0–1.0) derived
# from SleepFM's CoxPH survival analysis is translated into a clinically
# meaningful risk category.
#
# SleepFM uses Cox Proportional Hazards loss for disease prediction,
# producing hazard-based outputs. The risk_score field in our input schema
# represents a normalized value derived from these hazard predictions.
#
# Clinical rationale:
#   >= HIGH_THRESHOLD  → "high"     → May require urgent intervention
#   >= MOD_THRESHOLD   → "moderate" → Close follow-up recommended
#   <  MOD_THRESHOLD   → "low"      → Routine monitoring sufficient
#
# These values are intentionally kept in configuration so that clinicians
# can adjust them without modifying application logic.

HIGH_RISK_THRESHOLD: float = 0.80
MODERATE_RISK_THRESHOLD: float = 0.50


# ─── FHIR R4 Risk Probability Code System ───────────────────────────────────
# Official HL7 terminology for qualitative risk levels.
# Reference: http://terminology.hl7.org/CodeSystem/risk-probability

RISK_PROBABILITY_SYSTEM: str = (
    "http://terminology.hl7.org/CodeSystem/risk-probability"
)

@dataclass(frozen=True)
class RiskLevel:
    """Represents a FHIR-compliant qualitative risk classification."""
    code: str
    display: str

RISK_LEVELS: Dict[str, RiskLevel] = {
    "high": RiskLevel(code="high", display="High likelihood"),
    "moderate": RiskLevel(code="moderate", display="Moderate likelihood"),
    "low": RiskLevel(code="low", display="Low likelihood"),
}


# ─── SNOMED CT Terminology Mappings ──────────────────────────────────────────
# Maps internal condition identifiers to their universal SNOMED CT codes.
# SNOMED CT is the global clinical terminology standard used in FHIR resources.
#
# To add a new condition:
#   1. Find the SNOMED CT code at https://browser.ihtsdotools.org
#   2. Add an entry to SNOMED_MAPPINGS below
#   3. No other code changes required
#
# Planned expansions (not yet implemented):
#   - Sleep Apnea: 78275009
#   - Insomnia: 193462001
#   - Periodic Limb Movement Disorder: 230480001

SNOMED_SYSTEM: str = "http://snomed.info/sct"

@dataclass(frozen=True)
class SnomedConcept:
    """Represents a SNOMED CT coded clinical concept."""
    code: str
    display: str

SNOMED_MAPPINGS: Dict[str, SnomedConcept] = {
    "Atrial Fibrillation": SnomedConcept(
        code="71908006",
        display="Atrial fibrillation (disorder)",
    ),
}


# ─── AI Model Metadata ──────────────────────────────────────────────────────
# Identifies the prediction model in the FHIR output.
# This allows downstream systems to trace which model version produced
# a given risk assessment.
#
# Reference: https://github.com/zou-group/sleepfm-clinical
# Published: Nature Medicine (2025)
# Method: CoxPH survival analysis on multimodal PSG embeddings

MODEL_SYSTEM: str = "http://custom.ai/models"
MODEL_CODE: str = "sleepfm-clinical-v1"
MODEL_DISPLAY: str = "SleepFM Clinical Risk Prediction Model v1"
