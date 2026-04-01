"""
Clinical Bridge - Risk Stratification Engine

Translates a normalized risk score (0.0–1.0) from SleepFM's CoxPH
survival analysis into a clinically meaningful, FHIR-compliant
qualitative risk level (high / moderate / low).

All threshold values are read from config.py — no magic numbers here.
This ensures clinicians can adjust classification boundaries without
touching application logic.
"""

from config import (
    HIGH_RISK_THRESHOLD,
    MODERATE_RISK_THRESHOLD,
    RISK_LEVELS,
    SNOMED_MAPPINGS,
    RiskLevel,
    SnomedConcept,
)


class RiskStratificationError(Exception):
    """Raised when risk stratification encounters an unrecoverable error."""
    pass


class UnknownConditionError(RiskStratificationError):
    """Raised when a condition has no SNOMED CT mapping in configuration."""
    pass


def classify_risk(risk_score: float) -> RiskLevel:
    """
    Classify a normalized risk score into a qualitative risk level.

    Uses threshold values defined in config.py to map continuous
    risk scores to discrete clinical categories.

    Args:
        risk_score: Normalized value between 0.0 and 1.0 derived
            from SleepFM's CoxPH hazard predictions.

    Returns:
        RiskLevel with FHIR-compliant code and display string.

    Raises:
        ValueError: If risk_score is outside the valid [0.0, 1.0] range.

    Examples:
        >>> classify_risk(0.85)
        RiskLevel(code='high', display='High likelihood')

        >>> classify_risk(0.65)
        RiskLevel(code='moderate', display='Moderate likelihood')

        >>> classify_risk(0.30)
        RiskLevel(code='low', display='Low likelihood')
    """
    if not 0.0 <= risk_score <= 1.0:
        raise ValueError(
            f"risk_score must be between 0.0 and 1.0, got {risk_score}"
        )

    if risk_score >= HIGH_RISK_THRESHOLD:
        return RISK_LEVELS["high"]

    if risk_score >= MODERATE_RISK_THRESHOLD:
        return RISK_LEVELS["moderate"]

    return RISK_LEVELS["low"]


def resolve_snomed(condition: str) -> SnomedConcept:
    """
    Resolve a condition name to its SNOMED CT concept.

    Performs case-insensitive lookup against the terminology
    mappings defined in config.py.

    Args:
        condition: Clinical condition name (e.g., "Atrial Fibrillation").

    Returns:
        SnomedConcept with the universal code and display term.

    Raises:
        UnknownConditionError: If the condition has no SNOMED CT mapping.
            The error message lists all currently supported conditions
            to guide the caller toward valid inputs.

    Examples:
        >>> resolve_snomed("Atrial Fibrillation")
        SnomedConcept(code='71908006', display='Atrial fibrillation (disorder)')
    """
    # Build a case-insensitive lookup to tolerate minor formatting differences
    normalized_mappings = {
        key.lower(): value for key, value in SNOMED_MAPPINGS.items()
    }

    concept = normalized_mappings.get(condition.lower())

    if concept is None:
        supported = ", ".join(sorted(SNOMED_MAPPINGS.keys()))
        raise UnknownConditionError(
            f"No SNOMED CT mapping found for condition: '{condition}'. "
            f"Currently supported conditions: [{supported}]. "
            f"To add support, create an entry in config.SNOMED_MAPPINGS."
        )

    return concept
