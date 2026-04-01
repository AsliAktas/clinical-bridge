"""
Clinical Bridge - Main Orchestrator

The single entry point for converting SleepFM predictions into
FHIR R4 RiskAssessment resources.

This module implements the "black box" pattern: callers pass in raw
prediction data and receive a validated, FHIR-compliant clinical
resource — without needing to understand the internal pipeline.

Pipeline flow:
    1. Validate input via Pydantic (models.py)
    2. Classify risk level (risk_engine.py)
    3. Resolve SNOMED CT code (risk_engine.py)
    4. Build FHIR R4 resource (fhir_builder.py)
    5. Validate output against FHIR R4 schema (fhir.resources)
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from models import SleepFMPrediction
from risk_engine import classify_risk, resolve_snomed
from fhir_builder import build_risk_assessment


class ClinicalBridgeError(Exception):
    """Base exception for Clinical Bridge pipeline errors."""
    pass


class FHIRValidationError(ClinicalBridgeError):
    """Raised when the generated FHIR resource fails schema validation."""
    pass


class SleepFMToFHIRAdapter:
    """
    Adapter that converts SleepFM CoxPH predictions into FHIR R4
    RiskAssessment resources.

    This class encapsulates the entire conversion pipeline behind a
    single public method: translate(). Internal processing steps are
    private (prefixed with _) and should not be called directly.

    Usage:
        adapter = SleepFMToFHIRAdapter()
        fhir_json = adapter.translate({
            "patient_id": "P-102",
            "condition": "Atrial Fibrillation",
            "risk_score": 0.85,
        })

    The adapter will:
        - Reject invalid input with clear error messages
        - Map risk scores to clinical risk levels
        - Resolve conditions to SNOMED CT codes
        - Produce a FHIR R4 RiskAssessment resource
        - Validate the output against the official FHIR schema
    """

    def translate(
        self,
        raw_input: Dict[str, Any],
        assessment_time: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        Convert a raw SleepFM prediction into a FHIR R4 RiskAssessment.

        This is the only public method. It orchestrates the full pipeline:
        validation → classification → terminology resolution → FHIR
        construction → schema verification.

        Args:
            raw_input: Dictionary with keys: patient_id (str),
                condition (str), risk_score (float 0.0–1.0).
            assessment_time: Optional timestamp override. Defaults to
                current UTC time.

        Returns:
            Dictionary representing a validated FHIR R4 RiskAssessment.

        Raises:
            pydantic.ValidationError: If input data fails type/value checks.
            UnknownConditionError: If condition has no SNOMED CT mapping.
            FHIRValidationError: If generated resource fails FHIR schema.
            ClinicalBridgeError: For any other pipeline errors.
        """
        # Step 1: Validate input through Pydantic gate
        prediction = self._validate_input(raw_input)

        # Step 2: Classify risk level from score
        risk_level = classify_risk(prediction.risk_score)

        # Step 3: Resolve SNOMED CT concept
        snomed_concept = resolve_snomed(prediction.condition)

        # Step 4: Build FHIR R4 RiskAssessment resource
        fhir_resource = build_risk_assessment(
            patient_id=prediction.patient_id,
            snomed_concept=snomed_concept,
            risk_level=risk_level,
            risk_score=prediction.risk_score,
            assessment_time=assessment_time,
        )

        # Step 5: Validate against FHIR R4 schema
        self._validate_fhir(fhir_resource)

        return fhir_resource

    def _validate_input(self, raw_input: Dict[str, Any]) -> SleepFMPrediction:
        """Gate check: enforce type safety and value constraints."""
        return SleepFMPrediction(**raw_input)

    def _validate_fhir(self, resource: Dict[str, Any]) -> None:
        """
        Validate the generated resource against the official FHIR R4 schema.

        Uses the fhir.resources library to programmatically verify that
        the output conforms to the HL7 FHIR R4 specification.

        Args:
            resource: FHIR resource dictionary to validate.

        Raises:
            FHIRValidationError: If validation fails, with details about
                which fields or structures are non-compliant.
        """
        try:
            from fhir.resources.riskassessment import RiskAssessment
            RiskAssessment.model_validate(resource)
        except ImportError:
            # fhir.resources not installed — skip schema validation
            # but log a warning so it's visible in test output
            import warnings
            warnings.warn(
                "fhir.resources package not installed. "
                "FHIR schema validation skipped. Install with: "
                "pip install fhir.resources",
                stacklevel=2,
            )
        except Exception as e:
            raise FHIRValidationError(
                f"Generated FHIR resource failed schema validation: {e}"
            ) from e


def main() -> None:
    """
    CLI entry point for demonstration and quick testing.

    Runs the adapter with sample data and prints the resulting
    FHIR R4 RiskAssessment to stdout.
    """
    adapter = SleepFMToFHIRAdapter()

    sample_input = {
        "patient_id": "P-102",
        "condition": "Atrial Fibrillation",
        "risk_score": 0.85,
    }

    print("=" * 60)
    print("Clinical Bridge — SleepFM to FHIR R4 Adapter")
    print("=" * 60)
    print()
    print("INPUT (SleepFM Prediction):")
    print(json.dumps(sample_input, indent=2))
    print()

    try:
        fhir_resource = adapter.translate(sample_input)
        print("OUTPUT (FHIR R4 RiskAssessment):")
        print(json.dumps(fhir_resource, indent=2))
        print()
        print("Status: SUCCESS — Resource generated and validated.")
    except Exception as e:
        print(f"Status: FAILURE — {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
