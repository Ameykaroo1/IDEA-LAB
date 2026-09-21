# CRYSTAL-X: Generative AI-Based Novel Crystal Material Discovery for Advanced Energy Applications

CRYSTAL-X is a computational research prototype designed to discover, validate, screen, rank, visualize, and prepare candidate inorganic crystal materials for advanced energy applications (solid-state battery electrolytes, high-capacity electrodes, and energy storage frameworks).

```
NATURAL LANGUAGE INPUT
        ↓
NLP REQUIREMENT EXTRACTION
        ↓
STRUCTURED CONSTRAINTS NORMALIZATION
        ↓
USER REVIEW & CONFIRMATION
        ↓
CRYSTAL GENERATION (MatterGen / Local Demo Adapter)
        ↓
STRUCTURAL VALIDATION (pymatgen)
        ↓
PROPERTY SCREENING (Hard constraints & Provenance)
        ↓
MULTI-CRITERIA RANKING (Dynamic weight renormalization)
        ↓
3D WEBGL VISUALIZATION (3Dmol.js)
        ↓
CIF EXPORT
        ↓
DFT VALIDATION QUEUE (Downstream package export)
```

---

## Scientific Honesty & Disclaimer

> [!IMPORTANT]
> **COMPUTATIONAL INTEGRITY STANDARD**:
> - This software is a **decision-support research prototype**, not a production material discovery platform.
> - Structural validity and machine-learning property predictions **do not constitute proof of thermodynamic stability, synthesizability, or experimental performance**.
> - The platform strictly distinguishes six stages of certainty:
>   1. **Generated candidate**: Raw structural proposal.
>   2. **Structurally valid candidate**: Passes deterministic crystallographic syntax, physical density, coordinate bounds, and interatomic distance heuristics.
>   3. **ML-predicted properties**: Statistical estimates labeled with explicit model provenance.
>   4. **Computationally promising candidate**: Survives multi-criteria property screening and ranking.
>   5. **DFT-validated candidate**: Staged for downstream ab initio electronic relaxation.
>   6. **Experimentally validated material**: Synthesized and electrochemically tested in a laboratory.
> - If an advanced property model (such as calibrated ionic conductivity) is uninstalled, it is marked **`NOT AVAILABLE`**; property values are never fabricated.

---

## 1. Natural Language Requirement Processing

Users are not required to manually fill separate form fields. The primary user interface accepts natural language sentences and paragraphs.

### Workflow
1. **User Describes Material**: E.g., *"I need a stable silicon-based material for energy storage with a band gap around 2.3 eV, low energy above hull, high ionic conductivity, and no lead, cadmium or mercury."*
2. **Hybrid NLP Extraction** (`backend/services/nlp_requirement_service.py`):
   - **Chemical Elements**: Identifies required elements (`Si`) and excluded/toxic species (`Pb`, `Cd`, `Hg`).
   - **Application**: Classifies energy applications (Battery electrode, Solid electrolyte, Energy storage, Solar).
   - **Properties & Units**: Normalizes band gap targets/ranges (`2.3 eV`), stability thresholds (`0.05 eV/atom`), and qualitative preferences (`low`, `high`).
   - **Ambiguity Detection**: Highlights missing numerical thresholds (e.g. qualitative *"high conductivity"* without numerical S/cm value).
3. **Constraint Normalization** (`backend/services/constraint_normalizer.py`): Converts extraction into a validated single source of truth.
4. **User Review & Confirmation Screen**: Displays extracted requirements with confidence badges (High / Medium / Low). The user may edit fields before clicking **Confirm & Generate**.
5. **Downstream Routing**: The confirmed normalized constraint JSON is passed directly to Generation, Validation, Screening, and Ranking.

---

## 2. Architecture & Generator Modes

CRYSTAL-X isolates generative backends through a unified interface (`backend/services/generator_service.py`):

```python
class CrystalGenerator(ABC):
    def generate(self, requirements: MaterialRequirements, num_candidates: int): ...
    def is_available(self) -> bool: ...
```

### A. REAL_GENERATOR Mode (MatterGen)
- Active when `MATTERGEN_PATH` or the `mattergen` Python package is detected.
- Directly invokes pretrained crystal diffusion models with property conditioning.

### B. DEMO_GENERATOR Mode
- Active when MatterGen is unconfigured (e.g. local development on Windows).
- Synthesizes chemically plausible candidate crystals from curated templates (diamond cubic, olivine, layered oxides, thiophosphates) using controlled stoichiometric substitution, lattice strain, and relaxation.
- Strictly labeled: `"DEMO GENERATION MODE — candidates are prototype-generated and not equivalent to MatterGen output."`

---

## 3. Structural Validation & Crystallography

Implemented in `backend/services/validation_service.py` using `pymatgen`:

1. **CIF parsing**: Syntax and symmetry verification.
2. **Lattice volume**: Ensures positive, finite unit cell volume ($V > 0$).
3. **Periodic coordinate wrapping**: Coordinates outside $[0, 1)$ are mathematically wrapped into the equivalent unit cell (`frac_coords % 1.0`) rather than incorrectly rejecting valid periodic lattices.
4. **Obvious atom-overlap heuristic**: Flags unphysical atomic collisions under periodic boundary conditions ($< 0.7$ Å threshold). Explicitly labeled as a heuristic in reports.
5. **Valid chemical elements**: Checked against verified periodic table data.
6. **Required & excluded elements**: Hard constraint verification.
7. **Deduplication**: Crystallographic symmetry comparison via `pymatgen.analysis.structure_matcher.StructureMatcher`.

---

## 4. Property Screening & Multi-Criteria Ranking

### Property Provenance
Every predicted property exposes its source:
- `ML_MODEL`: Output from a deployed machine learning model.
- `DEMO_SURROGATE`: Transparent empirical heuristic for demonstration.
- `NOT_AVAILABLE`: Displayed when no dedicated model is configured (e.g. Ionic Conductivity displays *"No dedicated calibrated ionic-conductivity predictor is configured"*).

### Ranking with Dynamic Weight Renormalization
When a property is `NOT_AVAILABLE`, the ranking engine **does not assign a score of 0**. Instead, weights are dynamically renormalized across available properties:
$$w'_p = \frac{w_p}{\sum_{k \in \text{available}} w_k}, \quad \text{Total Score} = \sum_{p \in \text{available}} w'_p \cdot S_p$$
Full mathematical explanations and contributing criteria are shown for every candidate.

---

## 5. Downstream DFT Preparation Queue

Downstream DFT relaxation is not performed within the prototype due to compute expense. Instead, high-priority candidates are queued into `exports/dft_queue/` which generates:
- Candidate CIF
- VASP `POSCAR` geometry
- Standard spin-polarized relaxation `INCAR` template
- Provenance `metadata.json`
- Explicit `DISCLAIMER.txt`

---

## 6. Installation & Execution

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ & npm

### Backend Setup (FastAPI)
```powershell
# 1. Install dependencies (if not already installed)
pip install fastapi uvicorn pymatgen ase scipy numpy pydantic pytest

# 2. Run backend server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be accessible at: `http://localhost:8000/docs`

### Frontend Setup (Next.js)
```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Start development server
npm run dev
```
Web application will be accessible at: `http://localhost:3000`

---

## 7. Automated Testing Suite

CRYSTAL-X includes a 38-test automated test suite covering all critical workflows:

```powershell
python -m pytest tests/ -v
```

- `tests/test_nlp_requirements.py`: 10+ NLP extraction scenarios (elements, exclusions, band gap target/range, hull energy, qualitative preferences, toxic shorthand).
- `tests/test_validation.py`: 5 valid structures, 5 invalid structures, fractional coordinate wrapping, atom-overlap heuristic, and duplicate detection.
- `tests/test_ranking.py`: 5 ranking tests including dynamic weight renormalization.
- `tests/test_api.py`: REST API integration tests.
- `tests/test_end_to_end.py`: Full demonstration scenario test.
