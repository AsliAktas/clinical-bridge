# Changelog

All notable changes to Clinical Bridge will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.1] — 2026-05-02

### Added
- Introduction paragraphs at the top of README for readers without prior context in sleep medicine, AI, or healthcare interoperability standards.
- Status indicator clarifying current maturity (reference implementation, AFib only, mock-data validated, not certified for clinical use).
- "What This Is NOT" section to prevent misinterpretation of the project's scope. Clarifies that the adapter is not a model, not affiliated with Stanford, not validated on real patient data, and not yet multi-condition.
- Author and project context note.
   
### Changed
- README framing: clarified "reference implementation" status throughout to avoid implying production readiness.

## [0.2.0] — 2026-04 (initial public release)

### Added
- Single-condition (Atrial Fibrillation) reference implementation.
- 44 unit tests covering input validation, risk classification, SNOMED CT resolution, FHIR construction, and schema validation.
- FHIR R4 RiskAssessment output with dual coding (SNOMED CT + ICD-10).
- Pydantic v2 input validation with custom validators.
- Three-layer architecture: input validation → risk classification → FHIR resource construction.
- Comprehensive FAQ for researchers, engineers, and clinicians.
- SleepFM integration sketch and SNOMED CT mappings for AFib.
- Risk threshold externalization (configurable in `config.py`).
