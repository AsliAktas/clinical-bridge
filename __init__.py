"""
Clinical Bridge — SleepFM to FHIR R4 Adapter

A type-safe adapter that converts SleepFM CoxPH survival analysis
predictions into HL7 FHIR R4 RiskAssessment resources with SNOMED CT
terminology mapping and programmatic schema validation.
"""

from main import SleepFMToFHIRAdapter

__all__ = ["SleepFMToFHIRAdapter"]
__version__ = "1.0.0"
