# Clinical Bridge

**In one sentence:** Clinical Bridge is a Python tool that converts AI-generated disease risk predictions into a standardized format that hospital information systems can read.

**A bit more detail:** SleepFM, an AI model developed at Stanford, analyzes overnight sleep recordings (polysomnography) and predicts a patient's risk for over 130 conditions — atrial fibrillation, dementia, heart failure, and more. But SleepFM's raw output is just a number, like `{"risk_score": 0.85}`. Hospital information systems can't store or interpret raw numbers — they need data structured according to international standards (HL7 FHIR) with universal medical codes (SNOMED CT). Clinical Bridge sits between these two worlds: it takes the model's output, validates it, classifies the risk level, attaches the right medical terminology codes, and produces a `FHIR R4 RiskAssessment` resource that any compliant hospital system can consume.

*Built and maintained by Aslı Aktaş, a Computer Engineering student in Türkiye exploring AI-clinical interoperability as an independent extension to the SleepFM ecosystem.*

**Status:** Reference implementation · Single condition (AFib) · Mock-data validated · Not certified for clinical use
**License:** MIT · Open source · Contributions welcome

**A type-safe adapter that converts [SleepFM](https://github.com/zou-group/sleepfm-clinical) CoxPH survival analysis predictions into HL7 FHIR R4 RiskAssessment resources.**

Clinical Bridge sits between AI model output and clinical information systems, handling input validation (Pydantic), clinical terminology mapping (SNOMED CT), risk stratification, and standards-compliant resource generation (FHIR R4) — so researchers don't have to.

---

## Why This Exists

SleepFM produces powerful disease risk predictions from polysomnography data, but its raw outputs are not directly consumable by hospital information systems. Clinical systems require structured, standards-compliant data with universal terminology codes. Clinical Bridge solves this interoperability gap.

## What This Is NOT

- **Not a risk prediction model** — only post-processing of model outputs. No ML, no inference, no training data inside this repository.
- **Not a replacement for SleepFM** — this adapter sits *downstream* of the model, converting its outputs to clinical formats.
- **Not affiliated with Stanford or the official SleepFM team** — this is an independent, community-built extension. Inspired by the SleepFM paper, not endorsed by it.
- **Not validated on real patient data** — tested only on synthetic CoxPH-style inputs.
- **Not certified for clinical use** — no regulatory review (FDA, CE, or otherwise) has been performed.
- **Not currently multi-condition** — Atrial Fibrillation reference  implementation only. The architecture is designed to scale to all   130 SleepFM conditions, but additional conditions are not yet configured.

### Before → After

```
┌─────────────────────────┐          ┌──────────────────────────────────────┐
│  SleepFM Raw Output     │          │  FHIR R4 RiskAssessment              │
│                         │          │                                      │
│  {                      │          │  {                                   │
│    "patient_id": "P-102"│  ──────► │    "resourceType": "RiskAssessment", │
│    "condition": "AFib", │          │    "status": "final",                │
│    "risk_score": 0.85   │          │    "subject": {"reference":          │
│  }                      │          │      "Patient/P-102"},               │
│                         │          │    "prediction": [{                  │
│  No terminology codes.  │          │      "outcome": {"coding": [{        │
│  No risk classification.│          │        "system": "http://snomed...", │
│  No FHIR compliance.    │          │        "code": "71908006"}]},        │
│                         │          │      "qualitativeRisk": {"coding":   │
│                         │          │        [{"code": "high"}]}           │
└─────────────────────────┘          │    }]                                │
                                     │  }                                   │
                                     │                                      │
                                     │  ✓ SNOMED CT coded                   │
                                     │  ✓ Risk stratified                   │
                                     │  ✓ FHIR R4 schema validated          │
                                     └──────────────────────────────────────┘
```

---

## Quick Start

### Installation

```bash
git clone https://github.com/AsliAktas/clinical-bridge.git
cd clinical-bridge
pip install -r requirements.txt
```

### Usage

```python
from main import SleepFMToFHIRAdapter

adapter = SleepFMToFHIRAdapter()

fhir_resource = adapter.translate({
    "patient_id": "P-102",
    "condition": "Atrial Fibrillation",
    "risk_score": 0.85,
})
# Returns a validated FHIR R4 RiskAssessment dict
```

### CLI Demo

```bash
python main.py
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    SleepFMToFHIRAdapter                       │
│                                                              │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │  models.py   │──►│ risk_engine  │──►│  fhir_builder    │  │
│  │  (Pydantic)  │   │  .py         │   │  .py             │  │
│  │             │   │              │   │                  │  │
│  │ Validates   │   │ Classifies   │   │ Builds FHIR R4   │  │
│  │ input types │   │ risk level   │   │ RiskAssessment   │  │
│  │ and ranges  │   │ + resolves   │   │ + validates      │  │
│  │             │   │ SNOMED CT    │   │ against schema   │  │
│  └─────────────┘   └──────────────┘   └──────────────────┘  │
│         ▲                  ▲                                 │
│         │                  │                                 │
│         └──────────────────┘                                 │
│                    │                                         │
│              config.py                                       │
│         (thresholds, SNOMED                                  │
│          mappings, constants)                                │
└──────────────────────────────────────────────────────────────┘
```

| Module | Responsibility |
|---|---|
| `config.py` | Risk thresholds, SNOMED CT mappings, model metadata. Single source of truth for all constants. |
| `models.py` | Pydantic input validation. Rejects malformed data with clear error messages before it enters the pipeline. |
| `risk_engine.py` | Risk score classification (high/moderate/low) and SNOMED CT terminology resolution. |
| `fhir_builder.py` | Constructs FHIR R4 RiskAssessment resources from processed data. |
| `main.py` | Orchestrates the full pipeline. Exposes `SleepFMToFHIRAdapter` as the single public entry point. |

---

## Risk Stratification

Risk scores are classified using configurable thresholds defined in `config.py`:

| Condition | FHIR Code | Clinical Meaning |
|---|---|---|
| `risk_score ≥ 0.80` | `high` | May require urgent intervention |
| `0.50 ≤ risk_score < 0.80` | `moderate` | Close follow-up recommended |
| `risk_score < 0.50` | `low` | Routine monitoring sufficient |

Thresholds are intentionally externalized so clinicians can adjust them without modifying application logic.

---

## Standards Compliance

- **FHIR R4 (v4.0.1)**: Output resources conform to the [RiskAssessment](https://www.hl7.org/fhir/riskassessment.html) specification and are programmatically validated using [`fhir.resources`](https://pypi.org/project/fhir.resources/).
- **SNOMED CT**: Conditions are mapped to universal codes via the [SNOMED CT Browser](https://browser.ihtsdotools.org/).
- **HL7 Risk Probability**: Qualitative risk levels use the [official code system](http://terminology.hl7.org/CodeSystem/risk-probability).

---

## Testing

```bash
pytest tests/ -v
```

The test suite includes 44 tests covering:

- **Input validation**: boundary values, type errors, missing fields, whitespace handling
- **Risk classification**: threshold boundaries (0.00, 0.50, 0.80, 1.00), out-of-range values
- **SNOMED resolution**: known conditions, case-insensitive lookup, unknown condition errors
- **FHIR construction**: all resource fields, timestamp handling, model metadata
- **FHIR schema validation**: output verified against official FHIR R4 schema
- **End-to-end integration**: full pipeline from raw input to validated output

---

## Extending to New Conditions

Adding support for a new condition requires only a single entry in `config.py`:

```python
SNOMED_MAPPINGS: Dict[str, SnomedConcept] = {
    "Atrial Fibrillation": SnomedConcept(
        code="71908006",
        display="Atrial fibrillation (disorder)",
    ),
    # Add new conditions here:
    "Sleep Apnea": SnomedConcept(
        code="78275009",
        display="Obstructive sleep apnea syndrome (disorder)",
    ),
}
```

No other code changes are required. The architecture is designed to scale from the current single-condition proof of concept to the full 130 conditions that SleepFM supports.

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **Flexible patient ID format** | Patient ID validation is intentionally flexible to accommodate diverse identifier schemes across institutions (e.g., `P-102`, `SU-44981`, UUIDs). Custom format enforcement can be added via configuration as needed. |
| **`risk_score` not `probability`** | SleepFM uses CoxPH survival analysis, producing hazard-based outputs rather than direct probabilities. The field name reflects this. |
| **Thresholds in config, not code** | Clinicians can adjust risk classification boundaries without touching application logic. |
| **Programmatic FHIR validation** | The `fhir.resources` library validates output against the official FHIR R4 schema — not just structural correctness but semantic compliance. |

---

## Context

[SleepFM](https://github.com/zou-group/sleepfm-clinical) is a multimodal sleep foundation model developed at Stanford, trained on 585,000+ hours of PSG recordings from ~65,000 participants. Published in [Nature Medicine (2025)](https://doi.org/10.1038/s41591-025-04133-4), it predicts risk for 130+ conditions with C-Index ≥ 0.75. This adapter addresses the clinical interoperability gap between model predictions and hospital information systems.

### Relevant SleepFM Performance Benchmarks

These C-Index values from the original publication provide context for the risk scores this adapter processes:

| Condition | C-Index | SNOMED CT Code | Status |
|---|---|---|---|
| All-Cause Mortality | 0.84 | — | Planned |
| Dementia | 0.85 | 52448006 | Planned |
| Myocardial Infarction | 0.81 | 22298006 | Planned |
| Heart Failure | 0.80 | 84114007 | Planned |
| Chronic Kidney Disease | 0.79 | 709044004 | Planned |
| Stroke | 0.78 | 230690007 | Planned |
| **Atrial Fibrillation** | **0.78** | **71908006** | **✓ Implemented** |

---

## Frequently Asked Questions

### For Researchers

**Q: Why does the adapter use `risk_score` instead of `probability`?**

SleepFM uses Cox Proportional Hazards (CoxPH) loss for disease prediction. CoxPH models produce hazard-based outputs — relative risk rankings — rather than calibrated probabilities. A "0.85" from SleepFM does not mean "85% chance of developing AFib." It means the patient's hazard profile, as derived from their sleep data, places them in a high-risk tier relative to the study population. The field is named `risk_score` to avoid misinterpretation. The adapter normalizes these values to a 0.0–1.0 range for downstream risk stratification.

**Q: Why only Atrial Fibrillation? SleepFM supports 130 conditions.**

This is an intentional proof-of-concept scope. The architecture is designed so that adding any of the remaining 129 conditions requires only a single dictionary entry in `config.py` — no logic changes, no new modules. We chose AFib because it has strong clinical relevance, a well-established SNOMED CT code, and a solid C-Index (0.78) in the SleepFM benchmarks. Once the adapter is validated in a real pipeline, scaling to all 130 conditions is a configuration task, not an engineering task.

**Q: How do I connect this to a live SleepFM model?**

The adapter is intentionally decoupled from the model runtime. SleepFM produces embeddings and hazard predictions through its own pipeline (`sleepfm/pipeline/finetune_diagnosis_coxph.py`). Your integration code should:
1. Run SleepFM inference to get the hazard-based prediction
2. Normalize the output to a 0.0–1.0 risk score
3. Pass it to `SleepFMToFHIRAdapter.translate()` as a dictionary

```python
# Example integration sketch
from main import SleepFMToFHIRAdapter

adapter = SleepFMToFHIRAdapter()

# Your code: get prediction from SleepFM
raw_score = your_sleepfm_pipeline.predict(patient_psg_data)
normalized_score = your_normalization_function(raw_score)

fhir_resource = adapter.translate({
    "patient_id": patient_record_id,
    "condition": "Atrial Fibrillation",
    "risk_score": normalized_score,
})
```

**Q: Can I adjust the risk thresholds?**

Yes. Edit `config.py`:

```python
HIGH_RISK_THRESHOLD: float = 0.80   # Change to your clinical requirement
MODERATE_RISK_THRESHOLD: float = 0.50
```

No other changes needed. Tests will still pass because they reference these config values dynamically.

### For Engineers

**Q: How is FHIR compliance verified?**

Two layers. First, the `fhir_builder.py` module constructs the resource using the exact field names, nesting, and coding systems specified in the [FHIR R4 RiskAssessment spec](https://www.hl7.org/fhir/riskassessment.html). Second, every generated resource is validated at runtime using the [`fhir.resources`](https://pypi.org/project/fhir.resources/) library, which checks against the official HL7 FHIR R4 JSON schema. If the library is not installed, a warning is emitted but the pipeline continues — this allows lightweight deployment in environments where schema validation is handled downstream.

**Q: What happens when invalid data is submitted?**

The pipeline fails fast with specific, actionable error messages:

| Error Scenario | Exception Type | Example Message |
|---|---|---|
| `risk_score` out of range | `pydantic.ValidationError` | "Input should be less than or equal to 1" |
| Non-numeric `risk_score` | `pydantic.ValidationError` | "Input should be a valid number, unable to parse string as a number" |
| Empty `patient_id` | `pydantic.ValidationError` | "String should have at least 1 character" |
| Whitespace-only `patient_id` | `pydantic.ValidationError` | "Patient ID must contain at least one non-whitespace character" |
| Unknown condition | `UnknownConditionError` | "No SNOMED CT mapping found for condition: 'X'. Currently supported: [Atrial Fibrillation]" |
| FHIR schema violation | `FHIRValidationError` | Details about which fields are non-compliant |

All errors are raised before any partial output is produced. The system never generates a malformed FHIR resource.

**Q: Why Pydantic v2 instead of dataclasses or manual validation?**

Pydantic v2 provides declarative validation with zero boilerplate: type coercion, range constraints (`ge=0.0, le=1.0`), custom validators, and automatic error messages — all from a single class definition. Manual `if/else` validation is error-prone and verbose. Dataclasses don't validate types at runtime. In a clinical context, silent type coercion failures are unacceptable.

**Q: Can this run in a Docker container or CI/CD pipeline?**

Yes. The project has no system-level dependencies beyond Python 3.10+. A minimal Dockerfile:

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
```

For CI, add to your workflow:
```yaml
- run: pip install -r requirements.txt
- run: pytest tests/ -v
```

### For Clinicians

**Q: What do the risk levels mean clinically?**

The adapter translates a continuous risk score into three categories using the official HL7 FHIR risk-probability code system. "High" (≥ 0.80) suggests the patient's sleep patterns are strongly associated with future disease onset and may warrant proactive clinical attention. "Moderate" (0.50–0.79) indicates elevated risk warranting closer follow-up. "Low" (< 0.50) suggests routine monitoring is appropriate. These are screening signals from an AI model, not diagnoses — they are intended to support clinical decision-making, not replace it.

**Q: Is this a diagnostic tool?**

No. Clinical Bridge is a data interoperability layer, not a diagnostic system. It translates AI model predictions into a format that hospital systems can consume. The clinical interpretation and any resulting care decisions remain entirely with the treating physician. The FHIR `RiskAssessment` resource type is specifically designed for this purpose — it represents a risk evaluation, not a diagnosis.

---

## Roadmap

- [ ] Expand SNOMED CT mappings for top SleepFM conditions (dementia, MI, heart failure, stroke, CKD)
- [ ] Add batch processing support for multi-patient pipelines
- [ ] FHIR Bundle output for multi-condition assessments per patient
- [ ] Integration examples with MedAgentBench and hospital simulation environments
- [ ] Configurable risk threshold profiles (e.g., conservative vs. standard)
- [ ] Structured logging for audit trails in clinical environments

---

## Contributing

Contributions are welcome. Please ensure all new code includes corresponding test cases and that `pytest tests/ -v` passes with no failures before submitting a pull request.

---

## License

MIT
