"""Configuration constants for Clinical Bridge.

Contains risk stratification thresholds, FHIR terminology codes,
SNOMED CT condition mappings, and model metadata used by the risk
engine and FHIR builder.
"""
from dataclasses import dataclass

# ------ Risk Stratification Thresholds ---------------------------------------
# Clinical rationale:
#   >= HIGH_RISK_THRESHOLD      -> "high"     -> May require urgent intervention
#   >= MODERATE_RISK_THRESHOLD  -> "moderate" -> Close follow-up recommended
#   <  MODERATE_RISK_THRESHOLD  -> "low"      -> Routine monitoring sufficient
#
# NOTE: These thresholds are based on rough clinical intuition, not
# validated against specific literature or outcome data. A production
# deployment should calibrate these against prospective cohort data.

HIGH_RISK_THRESHOLD: float = 0.80
MODERATE_RISK_THRESHOLD: float = 0.50


# ------ FHIR R4 Risk Probability Code System ---------------------------------
# Official HL7 terminology for qualitative risk levels.
# Reference: http://terminology.hl7.org/CodeSystem/risk-probability

RISK_PROBABILITY_SYSTEM: str = (
    "http://terminology.hl7.org/CodeSystem/risk-probability"
)

@dataclass(frozen=True)
class RiskLevel:
    """Represents a FHIR-compliant qualitative risk classification.

    frozen=True makes instances immutable and hashable, which allows
    them to be safely used as dictionary keys and prevents accidental
    mutation of the FHIR coding values.
    """
    code: str
    display: str

# Lookup table mapping risk category names to FHIR-compliant RiskLevel
# objects. Used by risk_engine.py to convert threshold comparisons
# into structured FHIR coding entries.
RISK_LEVELS: dict[str, RiskLevel] = {
    "high": RiskLevel(code="high", display="High likelihood"),
    "moderate": RiskLevel(code="moderate", display="Moderate likelihood"),
    "low": RiskLevel(code="low", display="Low likelihood"),
}


# ------ SNOMED CT Terminology Mappings ---------------------------------------
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


# Mapping from human-readable condition names (used as internal keys)
# to their SNOMED CT coded concepts. Extended in v0.3 to support
# SleepFM's multi-condition output.
SNOMED_MAPPINGS: dict[str, SnomedConcept] = {
    "Atrial Fibrillation": SnomedConcept(
        code="71908006",
        display="Atrial fibrillation (disorder)",
    ),
}


# ------ AI Model Metadata ----------------------------------------------------
# Identifies the prediction model in the FHIR output.
# This allows downstream systems to trace which model version produced
# a given risk assessment.
#
# Reference: https://github.com/zou-group/sleepfm-clinical
# Published: Nature Medicine (2025)
# Method: CoxPH survival analysis on multimodal PSG embeddings
# NOTE: "http://custom.ai/models" is a placeholder URL, not a registered
# FHIR code system. It satisfies FHIR's URI format requirement for schema
# validation, but a production deployment would require either a
# project-specific namespace registered through a terminology authority
# or integration with an existing AI/ML model code system.
MODEL_SYSTEM: str = "http://custom.ai/models"
MODEL_CODE: str = "sleepfm-clinical-v1"
MODEL_DISPLAY: str = "SleepFM Clinical Risk Prediction Model v1"
