"""
Clinical Bridge - Data Models Module

Defines the input data schema with strict type validation using Pydantic.
Acts as the security guard at the gate: any data that does not conform
to the expected structure is rejected with a clear, actionable error
message before it can enter the processing pipeline.

SleepFM uses CoxPH (Cox Proportional Hazards) survival analysis for
disease prediction. The risk_score field represents a normalized value
(0.0–1.0) derived from the model's hazard-based predictions.
"""

from pydantic import BaseModel, Field, field_validator


class SleepFMPrediction(BaseModel):
    """
    Validated input schema for a single SleepFM disease prediction.

    This model enforces type safety and value constraints on incoming
    data before it enters the Clinical Bridge processing pipeline.

    Attributes:
        patient_id: Unique patient identifier. Intentionally flexible
            to accommodate diverse identifier schemes across institutions.
            See design note below.
        condition: The predicted clinical condition name. Must match
            a key in config.SNOMED_MAPPINGS for successful FHIR conversion.
        risk_score: Normalized risk score (0.0–1.0) derived from
            SleepFM's CoxPH survival analysis hazard predictions.

    Design Note on patient_id:
        Patient ID validation is intentionally flexible to accommodate
        diverse identifier schemes across institutions (e.g., "P-102",
        "SU-44981", UUIDs). Custom format enforcement can be added via
        configuration as needed during institutional deployment.
    """

    patient_id: str = Field(
        ...,
        min_length=1,
        description="Unique patient identifier (non-empty string)",
    )

    condition: str = Field(
        ...,
        min_length=1,
        description="Predicted clinical condition name",
    )

    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Normalized risk score (0.0–1.0) derived from "
            "SleepFM CoxPH hazard predictions"
        ),
    )

    @field_validator("patient_id")
    @classmethod
    def patient_id_must_not_be_blank(cls, v: str) -> str:
        """Reject patient IDs that are only whitespace."""
        if not v.strip():
            raise ValueError(
                "Patient ID must contain at least one non-whitespace "
                "character. Received a blank string."
            )
        return v.strip()

    @field_validator("condition")
    @classmethod
    def condition_must_not_be_blank(cls, v: str) -> str:
        """Reject condition names that are only whitespace."""
        if not v.strip():
            raise ValueError(
                "Condition name must contain at least one non-whitespace "
                "character. Received a blank string."
            )
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "patient_id": "P-102",
                    "condition": "Atrial Fibrillation",
                    "risk_score": 0.85,
                }
            ]
        }
    }
