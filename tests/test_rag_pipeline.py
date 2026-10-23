"""
Comprehensive Unit and Integration Tests for CRYSTAL-X RAG Scientific Validation Module.
Tests:
1. Document ingestion and chunking (PDF and plain text)
2. Metadata preservation (title, year, DOI, page number, chemical tags)
3. Hybrid retrieval (exact formula boost, chemical analog matching, semantic cosine search)
4. Exact formula vs no-evidence-found behavior
5. Scientific validation tool execution and status handling (PASS, FAIL, WARNING, UNKNOWN, NOT_RUN)
6. Prevention of scientific hallucinations (literature does NOT equal thermodynamic stability)
7. Missing calculations treated as UNKNOWN, not FAIL
8. LLM prompt construction and structured report generation
9. FastAPI RAG endpoints (/api/rag/*)
"""

import pytest
import io
import json
from pymatgen.core import Structure, Lattice
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.rag.vector_store import RAGVectorStore, ScientificEmbeddingFunction
from backend.services.rag.ingestion import ScientificDocumentIngestionService
from backend.services.rag.retrieval import HybridScientificRetrievalService
from backend.services.rag.scientific_validator import ScientificValidator
from backend.services.rag.llm_reasoning import LLMScientificReasoningService, OfflineScientificReasoningEngine
from backend.services.rag.rag_service import RAGValidationService
from backend.models.rag_schemas import (
    RetrievalRequest,
    RunRAGValidationRequest,
    DocumentChunk
)

# Tests run with in-process service and route invocation


# -------------------------------------------------------------
# 1. Ingestion & Embedding Tests
# -------------------------------------------------------------

def test_scientific_embedder_deterministic_and_normalized():
    embedder = ScientificEmbeddingFunction(dimension=128)
    vec1 = embedder.embed_text("Li10GeP2S12 superionic solid state electrolyte")
    vec2 = embedder.embed_text("Li10GeP2S12 superionic solid state electrolyte")
    assert len(vec1) == 128
    assert vec1 == vec2  # Deterministic
    
    # Check unit normalization
    import numpy as np
    norm = np.linalg.norm(vec1)
    assert abs(norm - 1.0) < 1e-4


def test_document_chunking_and_formula_extraction(tmp_path):
    store = RAGVectorStore(storage_dir=str(tmp_path))
    ingestion = ScientificDocumentIngestionService(store)

    paper_text = (
        "Solid-state batteries utilizing Li7La3Zr2O12 (LLZO) garnet electrolytes exhibit remarkable stability against lithium metal.\n\n"
        "However, thiophosphate compounds such as Li10GeP2S12 and Li3PS4 deliver higher bulk ionic conductivity (up to 12 mS/cm), "
        "although they suffer from air moisture sensitivity releasing H2S gas."
    )

    formulas = ingestion.extract_chemical_formulas(paper_text)
    assert "Li7La3Zr2O12" in formulas
    assert "Li10GeP2S12" in formulas
    assert "Li3PS4" in formulas
    assert "H2S" in formulas

    res = ingestion.ingest_text_document(
        content=paper_text,
        title="Comparative Study of Solid Electrolytes",
        authors="Test Researcher",
        year=2024,
        doi_or_url="https://doi.org/10.1000/test"
    )
    assert res.success is True
    assert res.chunks_created >= 1

    chunks = [c for c in store.get_all_chunks() if c.document_id == res.document_id]
    assert len(chunks) >= 1
    c = chunks[0]
    assert c.title == "Comparative Study of Solid Electrolytes"
    assert c.publication_year == 2024
    assert c.authors == "Test Researcher"
    assert "Li10GeP2S12" in c.formulas_mentioned or "Li7La3Zr2O12" in c.formulas_mentioned


def test_corrupt_pdf_error_handling(tmp_path):
    store = RAGVectorStore(storage_dir=str(tmp_path))
    ingestion = ScientificDocumentIngestionService(store)

    # Intentionally corrupt random bytes
    corrupt_bytes = b"%PDF-1.4 non-valid garbage bytes that fail parser"
    res = ingestion.ingest_pdf_file(
        pdf_bytes=corrupt_bytes,
        filename="corrupted_paper.pdf",
        title="Corrupted Paper"
    )
    assert res.success is False
    assert "Failed to parse PDF" in res.message


# -------------------------------------------------------------
# 2. Hybrid Retrieval Tests
# -------------------------------------------------------------

def test_exact_formula_retrieval_priority(tmp_path):
    store = RAGVectorStore(storage_dir=str(tmp_path))
    ingestion = ScientificDocumentIngestionService(store)
    retrieval = HybridScientificRetrievalService(vector_store=store)

    ingestion.ingest_text_document(
        content="General discussion on batteries and energy storage frameworks without specific materials.",
        title="General Battery Review"
    )
    ingestion.ingest_text_document(
        content="Li10GeP2S12 shows 12 mS/cm lithium ionic conductivity with tetragonal space group P4_2/nmc.",
        title="LGPS Discovery Paper"
    )

    req = RetrievalRequest(
        formula="Li10GeP2S12",
        application="Solid electrolyte",
        max_results=5,
        include_external_sources=False
    )
    res = retrieval.retrieve(req)
    assert res.evidence_found is True
    assert len(res.evidence) >= 1
    top_match = res.evidence[0]
    assert top_match.match_type == "EXACT_FORMULA"
    assert top_match.relevance_score >= 0.70


def test_no_evidence_found_behavior(tmp_path):
    store = RAGVectorStore(storage_dir=str(tmp_path))
    # Clear out seed chunks to test pure empty state
    store.clear()
    retrieval = HybridScientificRetrievalService(vector_store=store)

    req = RetrievalRequest(
        formula="Unobtanium99Xy4",
        application="Superconductor",
        include_external_sources=False
    )
    res = retrieval.retrieve(req)
    assert res.evidence_found is False
    assert len(res.evidence) == 0
    assert any("No direct scientific literature" in note for note in res.retrieval_notes)


# -------------------------------------------------------------
# 3. Scientific Validation Tool Statuses & Checks
# -------------------------------------------------------------

def test_validator_detects_atomic_collision_as_fail():
    validator = ScientificValidator()
    # Construct cubic cell with two atoms right on top of each other (0.1 Å apart)
    lattice = Lattice.cubic(4.0)
    struct = Structure(lattice, ["Si", "Si"], [[0.0, 0.0, 0.0], [0.025, 0.0, 0.0]])  # dist = 0.10 Å

    checks, summary, _ = validator.run_all_checks(struct=struct, formula="Si2")
    assert summary["Interatomic Distance Heuristic"] == "FAIL"
    assert summary["Structure File Parsing"] == "PASS"


def test_validator_warns_on_unrelaxed_bond_distance():
    validator = ScientificValidator()
    lattice = Lattice.cubic(4.0)
    # dist = 0.90 Å -> between 0.70 Å and 1.20 Å -> WARNING
    struct = Structure(lattice, ["Si", "Si"], [[0.0, 0.0, 0.0], [0.225, 0.0, 0.0]])

    checks, summary, _ = validator.run_all_checks(struct=struct, formula="Si2")
    assert summary["Interatomic Distance Heuristic"] == "WARNING"


def test_validator_reports_missing_calculations_as_unknown_not_fail():
    validator = ScientificValidator()
    lattice = Lattice.cubic(4.0)
    struct = Structure(lattice, ["Si"], [[0.0, 0.0, 0.0]])

    checks, summary, _ = validator.run_all_checks(
        struct=struct,
        formula="Si",
        predicted_ehull=None,         # Uncalculated
        predicted_conductivity=None    # Uncalculated
    )
    # Critical requirement: Missing evidence must NOT be treated as a failed test!
    assert summary["Thermodynamic Convex Hull Stability (Ehull)"] == "UNKNOWN"
    assert summary["Ionic Conductivity Assessment"] == "UNKNOWN"
    assert summary["Structure File Parsing"] == "PASS"


def test_validator_fails_on_toxic_excluded_elements():
    validator = ScientificValidator()
    lattice = Lattice.cubic(4.0)
    struct = Structure(lattice, ["Pb", "S"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])

    checks, summary, _ = validator.run_all_checks(
        struct=struct,
        formula="PbS",
        excluded_elements=["Pb", "Cd", "Hg"]
    )
    assert summary["Element Restrictions"] == "FAIL"


def test_charge_neutrality_and_oxidation_state_check():
    validator = ScientificValidator()
    # LiFePO4 has well-defined oxidation states Li+1, Fe+2, P+5, O-2
    lattice = Lattice.cubic(10.0)
    struct = Structure(lattice, ["Li", "Fe", "P", "O", "O", "O", "O"], [
        [0.0, 0.0, 0.0], [0.2, 0.2, 0.2], [0.4, 0.4, 0.4],
        [0.6, 0.0, 0.0], [0.0, 0.6, 0.0], [0.0, 0.0, 0.6], [0.6, 0.6, 0.0]
    ])

    checks, summary, _ = validator.run_all_checks(struct=struct, formula="LiFePO4")
    assert summary["Charge Neutrality & Oxidation State Plausibility"] == "PASS"


# -------------------------------------------------------------
# 4. LLM Scientific Reasoning & Report Generation
# -------------------------------------------------------------

def test_offline_scientific_reasoning_engine_safety():
    engine = OfflineScientificReasoningEngine()
    
    # Passing checks prompt
    passing_prompt = (
        "Candidate Formula: Li10GeP2S12\n"
        "Application: Solid electrolyte\n"
        "--- SCIENTIFIC VALIDATION TOOL RESULTS ---\n"
        "- [PASS] Structure File Parsing\n"
        "- [PASS] Lattice Geometry & Volume\n"
        "- [PASS] Interatomic Distance Heuristic\n"
        "- [PASS] Chemical Composition Validity\n"
    )
    report = engine.generate_report_content("", passing_prompt)
    assert report["overall_verdict"] == "FAVORABLE_FOR_DFT"
    assert "FAVORABLE" in report["verdict_badge"]
    assert len(report["scientific_risks"]) > 0
    # Must flag known thiophosphate air sensitivity
    assert any("H2S" in r or "hydrolyze" in r.lower() for r in report["scientific_risks"])

    # Failing check prompt
    failing_prompt = (
        "Candidate Formula: Li10GeP2S12\n"
        "Application: Solid electrolyte\n"
        "--- SCIENTIFIC VALIDATION TOOL RESULTS ---\n"
        "- [FAIL] Interatomic Distance Heuristic: Atomic overlap at 0.45 A\n"
    )
    fail_report = engine.generate_report_content("", failing_prompt)
    assert fail_report["overall_verdict"] == "UNFAVORABLE"
    assert "UNFAVORABLE" in fail_report["verdict_badge"]


def test_full_rag_validation_service_end_to_end(tmp_path):
    service = RAGValidationService(storage_dir=str(tmp_path))
    
    # Ingest seed document
    service.ingest_text_document(
        content="Li10GeP2S12 crystallizes in tetragonal space group with high Li conductivity of 12 mS/cm.",
        title="LGPS Benchmark"
    )

    sample_cif = """data_LGPS
_cell_length_a 8.71
_cell_length_b 8.71
_cell_length_c 12.63
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Li1 Li 0.0 0.0 0.0
Ge1 Ge 0.5 0.5 0.0
P1 P 0.5 0.0 0.25
S1 S 0.18 0.18 0.18
"""

    req = RunRAGValidationRequest(
        candidate_id="cand-test-lgps",
        formula="Li10GeP2S12",
        cif_string=sample_cif,
        application="Solid electrolyte"
    )
    report = service.validate_candidate(req)

    assert report.candidate_id == "cand-test-lgps"
    assert report.formula == "Li10GeP2S12"
    assert len(report.checks) >= 6
    assert report.checks_summary["Structure File Parsing"] == "PASS"
    assert len(report.citations) >= 1
    assert len(report.recommended_computational_tests) >= 1
    assert "does not guarantee thermodynamic stability" in report.scientific_disclaimer.lower()

    # Verify cached retrieval
    cached = service.get_report("cand-test-lgps")
    assert cached is not None
    assert cached.report_id == report.report_id


# -------------------------------------------------------------
# 5. FastAPI RAG Route Handlers
# -------------------------------------------------------------

def test_api_rag_connectors_status_route(tmp_path):
    from backend.api.rag_routes import get_connectors_status
    service = RAGValidationService(storage_dir=str(tmp_path))
    data = get_connectors_status(service=service)
    assert "materials_project" in data
    assert "cod" in data
    assert "local_catalog" in data
    assert "vector_store" in data


def test_api_rag_documents_and_upload_route(tmp_path):
    from backend.api.rag_routes import list_documents, upload_document
    from fastapi import UploadFile
    service = RAGValidationService(storage_dir=str(tmp_path))
    
    # 1. List initial documents
    init_docs = list_documents(service=service)
    init_count = init_docs["count"]
    assert init_count >= 1  # Seed papers are present

    # 2. Upload text document via route
    file_bytes = b"LiFePO4 olivine material exhibits 170 mAh/g theoretical capacity with 3.45 V operating potential."
    upload_file = UploadFile(filename="lifepo4_paper.txt", file=io.BytesIO(file_bytes))
    
    upload_res = upload_document(
        file=upload_file,
        title="Olivine Cathodes Study",
        authors="Goodenough et al.",
        year=1997,
        doi="https://doi.org/10.1149/1.1837571",
        service=service
    )
    assert upload_res.success is True
    assert upload_res.chunks_created >= 1

    # 3. Verify count increased
    after_docs = list_documents(service=service)
    assert after_docs["count"] == init_count + 1


def test_api_rag_retrieve_route(tmp_path):
    from backend.api.rag_routes import retrieve_scientific_evidence
    service = RAGValidationService(storage_dir=str(tmp_path))

    req = RetrievalRequest(
        formula="Li10GeP2S12",
        application="Solid electrolyte",
        max_results=3,
        include_external_sources=False
    )
    res = retrieve_scientific_evidence(request=req, service=service)
    assert res.target_formula == "Li10GeP2S12"
    assert res.evidence_found is True
    assert len(res.evidence) >= 1


def test_api_rag_validate_route(tmp_path):
    from backend.api.rag_routes import run_rag_validation, get_validation_report
    service = RAGValidationService(storage_dir=str(tmp_path))

    sample_cif = """data_Si
_cell_length_a 5.43
_cell_length_b 5.43
_cell_length_c 5.43
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0.0 0.0 0.0
Si2 Si 0.25 0.25 0.25
"""
    req = RunRAGValidationRequest(
        candidate_id="cand-si-diamond",
        formula="Si",
        cif_string=sample_cif,
        application="Anode material"
    )
    report = run_rag_validation(request=req, service=service)
    assert report.candidate_id == "cand-si-diamond"
    assert report.overall_verdict in ["FAVORABLE_FOR_DFT", "MARGINAL_WITH_CONCERNS"]
    assert "Structure File Parsing" in report.checks_summary

    # Test GET cached report route
    cached = get_validation_report(candidate_id="cand-si-diamond", service=service)
    assert cached.report_id == report.report_id
