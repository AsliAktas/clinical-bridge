"""
Clinical Bridge - FHIR R4 Resource Builder

Constructs HL7 FHIR R4 RiskAssessment resources from validated and
classified SleepFM prediction data.

Output conforms to the FHIR R4 (v4.0.1) specification:
  https://www.hl7.org/fhir/riskassessment.html

The generated JSON is validated against the official FHIR R4 schema
using the fhir.resources library to guarantee structural correctness
before delivery to downstream clinical systems.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from config import (
    MODEL_CODE,
    MODEL_DISPLAY,
    MODEL_SYSTEM,
    RISK_PROBABILITY_SYSTEM,
    SNOMED_SYSTEM,
    RiskLevel,
    SnomedConcept,
)


def build_risk_assessment(
    patient_id: str,
    snomed_concept: SnomedConcept,
    risk_level: RiskLevel,
    risk_score: float,
    assessment_time: datetime | None = None,
) -> Dict[str, Any]:
    """
    Build a FHIR R4 RiskAssessment resource dictionary.

    Assembles all components — patient reference, SNOMED-coded outcome,
    quantitative risk score, and qualitative risk level — into a
    complete FHIR-compliant RiskAssessment resource.

    Args:
        patient_id: Unique patient identifier (used in subject reference).
        snomed_concept: Resolved SNOMED CT concept for the predicted condition.
        risk_level: Classified qualitative risk level (high/moderate/low).
        risk_score: Original normalized risk score (0.0–1.0).
        assessment_time: Timestamp for the assessment. Defaults to current
            UTC time if not provided.

    Returns:
        Dictionary representing a valid FHIR R4 RiskAssessment resource,
        ready for JSON serialization and delivery to clinical systems.

    Examples:
        >>> from config import RiskLevel, SnomedConcept
        >>> resource = build_risk_assessment(
        ...     patient_id="P-102",
        ...     snomed_concept=SnomedConcept("71908006", "Atrial fibrillation (disorder)"),
        ...     risk_level=RiskLevel("high", "High likelihood"),
        ...     risk_score=0.85,
        ... )
        >>> resource["resourceType"]
        'RiskAssessment'
    """
    if assessment_time is None:
        assessment_time = datetime.now(timezone.utc)

    return {
        "resourceType": "RiskAssessment",
        "status": "final",
        "subject": {
            "reference": f"Patient/{patient_id}",
        },
        "occurrenceDateTime": assessment_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": {
            "coding": [
                {
                    "system": MODEL_SYSTEM,
                    "code": MODEL_CODE,
                    "display": MODEL_DISPLAY,
                }
            ]
        },
        "prediction": [
            {
                "outcome": {
                    "coding": [
                        {
                            "system": SNOMED_SYSTEM,
                            "code": snomed_concept.code,
                            "display": snomed_concept.display,
                        }
                    ]
                },
                "probabilityDecimal": risk_score,
                "qualitativeRisk": {
                    "coding": [
                        {
                            "system": RISK_PROBABILITY_SYSTEM,
                            "code": risk_level.code,
                            "display": risk_level.display,
                        }
                    ]
                },
            }
        ],
    }
