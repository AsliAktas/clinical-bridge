"""
Clinical Bridge - Test Suite

Comprehensive unit tests covering:
    - Input validation (Pydantic gate)
    - Risk classification logic (boundary values)
    - SNOMED CT terminology resolution
    - FHIR R4 resource construction
    - FHIR R4 schema validation (fhir.resources)
    - End-to-end pipeline integration

Run with: pytest tests/ -v
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SleepFMPrediction
from config import (
    HIGH_RISK_THRESHOLD,
    MODERATE_RISK_THRESHOLD,
    SNOMED_MAPPINGS,
)
from risk_engine import classify_risk, resolve_snomed, UnknownConditionError
from fhir_builder import build_risk_assessment
from main import SleepFMToFHIRAdapter, FHIRValidationError


# ═══════════════════════════════════════════════════════════════════════
# 1. INPUT VALIDATION (Pydantic Gate)
# ═══════════════════════════════════════════════════════════════════════

class TestInputValidation:
    """Tests for the Pydantic security guard at the gate."""

    def test_valid_input_accepted(self):
        """Standard valid input should pass without errors."""
        pred = SleepFMPrediction(
            patient_id="P-102",
            condition="Atrial Fibrillation",
            risk_score=0.85,
        )
        assert pred.patient_id == "P-102"
        assert pred.condition == "Atrial Fibrillation"
        assert pred.risk_score == 0.85

    def test_risk_score_upper_bound_accepted(self):
        """Boundary: risk_score = 1.0 is valid (maximum)."""
        pred = SleepFMPrediction(
            patient_id="P-001",
            condition="Atrial Fibrillation",
            risk_score=1.0,
        )
        assert pred.risk_score == 1.0

    def test_risk_score_lower_bound_accepted(self):
        """Boundary: risk_score = 0.0 is valid (minimum)."""
        pred = SleepFMPrediction(
            patient_id="P-001",
            condition="Atrial Fibrillation",
            risk_score=0.0,
        )
        assert pred.risk_score == 0.0

    def test_risk_score_above_one_rejected(self):
        """risk_score > 1.0 must be rejected."""
        with pytest.raises(ValidationError):
            SleepFMPrediction(
                patient_id="P-001",
                condition="Atrial Fibrillation",
                risk_score=1.5,
            )

    def test_risk_score_below_zero_rejected(self):
        """Negative risk_score must be rejected."""
        with pytest.raises(ValidationError):
            SleepFMPrediction(
                patient_id="P-001",
                condition="Atrial Fibrillation",
                risk_score=-0.1,
            )

    def test_risk_score_string_rejected(self):
        """Non-numeric risk_score must be rejected."""
        with pytest.raises(ValidationError):
            SleepFMPrediction(
                patient_id="P-001",
                condition="Atrial Fibrillation",
                risk_score="Eighty Five",
            )

    def test_empty_patient_id_rejected(self):
        """Empty string patient_id must be rejected."""
        with pytest.raises(ValidationError):
            SleepFMPrediction(
                patient_id="",
                condition="Atrial Fibrillation",
                risk_score=0.5,
            )

    def test_whitespace_patient_id_rejected(self):
        """Whitespace-only patient_id must be rejected."""
        with pytest.raises(ValidationError):
            SleepFMPrediction(
                patient_id="   ",
                condition="Atrial Fibrillation",
                risk_score=0.5,
            )

    def test_blank_condition_rejected(self):
        """Empty condition must be rejected."""
        with pytest.raises(ValidationError):
            SleepFMPrediction(
                patient_id="P-001",
                condition="",
                risk_score=0.5,
            )

    def test_missing_field_rejected(self):
        """Missing required fields must be rejected."""
        with pytest.raises(ValidationError):
            SleepFMPrediction(patient_id="P-001", condition="Atrial Fibrillation")

    def test_patient_id_whitespace_stripped(self):
        """Leading/trailing whitespace should be stripped from patient_id."""
        pred = SleepFMPrediction(
            patient_id="  P-102  ",
            condition="Atrial Fibrillation",
            risk_score=0.5,
        )
        assert pred.patient_id == "P-102"

    def test_diverse_patient_id_formats_accepted(self):
        """Various ID formats should be accepted (flexible by design)."""
        for pid in ["P-102", "SU-44981", "abc-def-123", "00042"]:
            pred = SleepFMPrediction(
                patient_id=pid,
                condition="Atrial Fibrillation",
                risk_score=0.5,
            )
            assert pred.patient_id == pid


# ═══════════════════════════════════════════════════════════════════════
# 2. RISK CLASSIFICATION (Boundary Value Analysis)
# ═══════════════════════════════════════════════════════════════════════

class TestRiskClassification:
    """Tests for risk score → clinical risk level classification."""

    def test_high_risk_above_threshold(self):
        """Score clearly above HIGH threshold → high."""
        assert classify_risk(0.95).code == "high"

    def test_high_risk_at_threshold(self):
        """Score exactly at HIGH threshold → high (boundary)."""
        assert classify_risk(HIGH_RISK_THRESHOLD).code == "high"

    def test_moderate_risk_below_high(self):
        """Score just below HIGH threshold → moderate."""
        assert classify_risk(HIGH_RISK_THRESHOLD - 0.01).code == "moderate"

    def test_moderate_risk_at_threshold(self):
        """Score exactly at MODERATE threshold → moderate (boundary)."""
        assert classify_risk(MODERATE_RISK_THRESHOLD).code == "moderate"

    def test_low_risk_below_moderate(self):
        """Score just below MODERATE threshold → low."""
        assert classify_risk(MODERATE_RISK_THRESHOLD - 0.01).code == "low"

    def test_low_risk_zero(self):
        """Score of 0.0 → low (minimum boundary)."""
        assert classify_risk(0.0).code == "low"

    def test_high_risk_one(self):
        """Score of 1.0 → high (maximum boundary)."""
        assert classify_risk(1.0).code == "high"

    def test_invalid_score_above_range(self):
        """Score > 1.0 raises ValueError."""
        with pytest.raises(ValueError):
            classify_risk(1.5)

    def test_invalid_score_below_range(self):
        """Score < 0.0 raises ValueError."""
        with pytest.raises(ValueError):
            classify_risk(-0.1)

    def test_risk_level_has_display_text(self):
        """Each risk level should have a human-readable display string."""
        level = classify_risk(0.85)
        assert level.display == "High likelihood"


# ═══════════════════════════════════════════════════════════════════════
# 3. SNOMED CT RESOLUTION
# ═══════════════════════════════════════════════════════════════════════

class TestSnomedResolution:
    """Tests for condition name → SNOMED CT code resolution."""

    def test_known_condition_resolved(self):
        """Known condition should resolve to correct SNOMED code."""
        concept = resolve_snomed("Atrial Fibrillation")
        assert concept.code == "71908006"
        assert concept.display == "Atrial fibrillation (disorder)"

    def test_case_insensitive_resolution(self):
        """Lookup should be case-insensitive."""
        concept = resolve_snomed("atrial fibrillation")
        assert concept.code == "71908006"

    def test_unknown_condition_raises_error(self):
        """Unknown condition should raise UnknownConditionError."""
        with pytest.raises(UnknownConditionError) as exc_info:
            resolve_snomed("Nonexistent Disease XYZ")
        assert "Nonexistent Disease XYZ" in str(exc_info.value)
        assert "config.SNOMED_MAPPINGS" in str(exc_info.value)

    def test_error_lists_supported_conditions(self):
        """Error message should list all supported conditions."""
        with pytest.raises(UnknownConditionError) as exc_info:
            resolve_snomed("Unknown")
        for condition in SNOMED_MAPPINGS.keys():
            assert condition in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════
# 4. FHIR R4 RESOURCE CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════

class TestFHIRBuilder:
    """Tests for FHIR R4 RiskAssessment resource generation."""

    @pytest.fixture
    def sample_resource(self):
        """Build a sample FHIR resource for testing."""
        from config import RiskLevel, SnomedConcept
        return build_risk_assessment(
            patient_id="P-102",
            snomed_concept=SnomedConcept("71908006", "Atrial fibrillation (disorder)"),
            risk_level=RiskLevel("high", "High likelihood"),
            risk_score=0.85,
            assessment_time=datetime(2026, 4, 1, 10, 30, 0, tzinfo=timezone.utc),
        )

    def test_resource_type(self, sample_resource):
        """Resource type must be RiskAssessment."""
        assert sample_resource["resourceType"] == "RiskAssessment"

    def test_status_is_final(self, sample_resource):
        """Status must be 'final'."""
        assert sample_resource["status"] == "final"

    def test_patient_reference(self, sample_resource):
        """Subject reference must follow Patient/{id} format."""
        assert sample_resource["subject"]["reference"] == "Patient/P-102"

    def test_occurrence_datetime(self, sample_resource):
        """Datetime must be in ISO 8601 format."""
        assert sample_resource["occurrenceDateTime"] == "2026-04-01T10:30:00Z"

    def test_model_metadata(self, sample_resource):
        """Method coding must reference the SleepFM model."""
        method = sample_resource["method"]["coding"][0]
        assert method["code"] == "sleepfm-clinical-v1"
        assert "SleepFM" in method["display"]

    def test_prediction_outcome_snomed(self, sample_resource):
        """Prediction outcome must use SNOMED CT coding."""
        outcome = sample_resource["prediction"][0]["outcome"]["coding"][0]
        assert outcome["system"] == "http://snomed.info/sct"
        assert outcome["code"] == "71908006"

    def test_prediction_probability(self, sample_resource):
        """Prediction must include the original risk score."""
        assert sample_resource["prediction"][0]["probabilityDecimal"] == 0.85

    def test_prediction_qualitative_risk(self, sample_resource):
        """Prediction must include the qualitative risk classification."""
        risk = sample_resource["prediction"][0]["qualitativeRisk"]["coding"][0]
        assert risk["code"] == "high"
        assert risk["system"] == "http://terminology.hl7.org/CodeSystem/risk-probability"

    def test_default_timestamp_is_utc(self):
        """When no timestamp is provided, default should be UTC now."""
        from config import RiskLevel, SnomedConcept
        resource = build_risk_assessment(
            patient_id="P-001",
            snomed_concept=SnomedConcept("71908006", "Atrial fibrillation (disorder)"),
            risk_level=RiskLevel("low", "Low likelihood"),
            risk_score=0.20,
        )
        assert resource["occurrenceDateTime"].endswith("Z")


# ═══════════════════════════════════════════════════════════════════════
# 5. FHIR R4 SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════

class TestFHIRSchemaValidation:
    """Tests that generated resources pass official FHIR R4 schema validation."""

    def test_valid_resource_passes_schema(self):
        """A correctly built resource should pass FHIR schema validation."""
        from fhir.resources.riskassessment import RiskAssessment
        from config import RiskLevel, SnomedConcept

        resource = build_risk_assessment(
            patient_id="P-102",
            snomed_concept=SnomedConcept("71908006", "Atrial fibrillation (disorder)"),
            risk_level=RiskLevel("high", "High likelihood"),
            risk_score=0.85,
            assessment_time=datetime(2026, 4, 1, 10, 30, 0, tzinfo=timezone.utc),
        )
        # This will raise if the resource is non-compliant
        validated = RiskAssessment.model_validate(resource)
        assert validated.__resource_type__ == "RiskAssessment"


# ═══════════════════════════════════════════════════════════════════════
# 6. END-TO-END INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    """Integration tests for the complete pipeline via SleepFMToFHIRAdapter."""

    @pytest.fixture
    def adapter(self):
        return SleepFMToFHIRAdapter()

    def test_happy_path_high_risk(self, adapter):
        """Full pipeline: high risk score → valid FHIR with 'high' classification."""
        result = adapter.translate({
            "patient_id": "P-102",
            "condition": "Atrial Fibrillation",
            "risk_score": 0.85,
        })
        assert result["resourceType"] == "RiskAssessment"
        assert result["prediction"][0]["qualitativeRisk"]["coding"][0]["code"] == "high"

    def test_happy_path_moderate_risk(self, adapter):
        """Full pipeline: moderate risk score → 'moderate' classification."""
        result = adapter.translate({
            "patient_id": "P-200",
            "condition": "Atrial Fibrillation",
            "risk_score": 0.65,
        })
        assert result["prediction"][0]["qualitativeRisk"]["coding"][0]["code"] == "moderate"

    def test_happy_path_low_risk(self, adapter):
        """Full pipeline: low risk score → 'low' classification."""
        result = adapter.translate({
            "patient_id": "P-300",
            "condition": "Atrial Fibrillation",
            "risk_score": 0.30,
        })
        assert result["prediction"][0]["qualitativeRisk"]["coding"][0]["code"] == "low"

    def test_invalid_score_rejected_at_gate(self, adapter):
        """Invalid risk_score should be caught by Pydantic before processing."""
        with pytest.raises(ValidationError):
            adapter.translate({
                "patient_id": "P-102",
                "condition": "Atrial Fibrillation",
                "risk_score": 1.5,
            })

    def test_unknown_condition_rejected(self, adapter):
        """Unknown condition should raise UnknownConditionError."""
        with pytest.raises(UnknownConditionError):
            adapter.translate({
                "patient_id": "P-102",
                "condition": "Nonexistent Disease",
                "risk_score": 0.5,
            })

    def test_missing_field_rejected(self, adapter):
        """Missing required field should raise ValidationError."""
        with pytest.raises(ValidationError):
            adapter.translate({
                "patient_id": "P-102",
                "condition": "Atrial Fibrillation",
            })

    def test_output_is_fhir_valid(self, adapter):
        """End-to-end output must pass FHIR R4 schema validation."""
        from fhir.resources.riskassessment import RiskAssessment

        result = adapter.translate({
            "patient_id": "P-102",
            "condition": "Atrial Fibrillation",
            "risk_score": 0.78,
        })
        validated = RiskAssessment.model_validate(result)
        assert validated.__resource_type__ == "RiskAssessment"

    def test_custom_timestamp_preserved(self, adapter):
        """Custom assessment_time should appear in the output."""
        ts = datetime(2026, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        result = adapter.translate(
            {
                "patient_id": "P-102",
                "condition": "Atrial Fibrillation",
                "risk_score": 0.85,
            },
            assessment_time=ts,
        )
        assert result["occurrenceDateTime"] == "2026-01-15T08:00:00Z"
