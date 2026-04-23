"""
Clinical Bridge - Data Models Module

Defines the input data schema with strict type validation using Pydantic.
Acts as the security guard at the gate: any data that does not conform
to the expected structure is rejected with a clear, actionable error
message before it can enter the processing pipeline.
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
    
    v0.3 Refactoring Plan:
    This class will be split into two models to match SleepFM's
    multi-condition output:
      - A new `SleepFMOutput` will hold patient_id and a list of predictions
      - This class will be renamed `SingleConditionPrediction` and drop
        patient_id, becoming an element within SleepFMOutput.predictions
    
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
    
    # TODO(v0.3): Consider case-insensitive condition matching to SNOMED_MAPPINGS.
    # Current implementation is case-sensitive which may cause confusion when
    # upstream systems produce labels like "atrial fibrillation" (lowercase).
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

    # Pydantic model configuration with example data.
    # This appears in the auto-generated JSON schema, useful for OpenAPI/Swagger
    # documentation when Clinical Bridge is wrapped with a FastAPI layer.
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
    
# TODO(v0.3): Add a top-level SleepFMOutput model to support multi-condition
# predictions. Expected structure:
#   class SleepFMOutput(BaseModel):
#       patient_id: str
#       predictions: List[SingleConditionPrediction]
# Then rename current SleepFMPrediction → SingleConditionPrediction (drop patient_id)
# to represent a single (condition, risk_score) pair within the list.