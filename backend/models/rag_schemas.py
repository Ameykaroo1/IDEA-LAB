"""
Pydantic Schemas for RAG-Based Scientific Validation in CRYSTAL-X.
Defines data structures for document ingestion, citations, retrieved evidence,
scientific validation checks, and evidence-grounded reports.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ==========================================
# 1. Document & Ingestion Schemas
# ==========================================

class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    title: str
    authors: Optional[str] = None
    publication_year: Optional[int] = None
    doi_or_url: Optional[str] = None
    source_type: str = "PEER_REVIEWED_PAPER"  # PEER_REVIEWED_PAPER, DATABASE_RECORD, USER_UPLOADED, BENCHMARK_CATALOG
    chemical_systems: List[str] = Field(default_factory=list)
    formulas_mentioned: List[str] = Field(default_factory=list)
    property_tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    document_id: str
    title: str
    authors: Optional[str] = None
    publication_year: Optional[int] = None
    doi_or_url: Optional[str] = None
    source_type: str = "PEER_REVIEWED_PAPER"
    file_name: Optional[str] = None
    file_type: str = "txt"  # pdf, txt, md, json
    chunk_count: int = 0
    added_at: str
    summary: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    title: str
    chunks_created: int
    formulas_detected: List[str] = Field(default_factory=list)
    message: str
    success: bool = True


# ==========================================
# 2. Retrieval Schemas
# ==========================================

class EvidenceItem(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    authors: Optional[str] = None
    publication_year: Optional[int] = None
    doi_or_url: Optional[str] = None
    page_number: Optional[int] = None
    passage_text: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_type: Literal["EXACT_FORMULA", "CHEMICAL_ANALOG", "SEMANTIC_SIMILARITY", "PROPERTY_MATCH", "DATABASE_RECORD"]
    matched_formulas: List[str] = Field(default_factory=list)
    source_type: str = "PEER_REVIEWED_PAPER"


class RetrievalRequest(BaseModel):
    formula: str
    reduced_formula: Optional[str] = None
    elements: List[str] = Field(default_factory=list)
    application: Optional[str] = "Solid electrolyte"
    target_properties: Dict[str, Any] = Field(default_factory=dict)
    query_text: Optional[str] = None
    max_results: int = Field(default=8, ge=1, le=25)
    include_external_sources: bool = True


class RetrievalResponse(BaseModel):
    query: str
    target_formula: str
    evidence_found: bool
    total_retrieved: int
    evidence: List[EvidenceItem] = Field(default_factory=list)
    comparable_materials: List[Dict[str, Any]] = Field(default_factory=list)
    external_source_status: Dict[str, str] = Field(default_factory=dict)
    retrieval_notes: List[str] = Field(default_factory=list)


# ==========================================
# 3. Scientific Validation Check Schemas
# ==========================================

ValidationCheckStatus = Literal["PASS", "FAIL", "WARNING", "UNKNOWN", "NOT_RUN"]

class ScientificCheckResult(BaseModel):
    name: str
    status: ValidationCheckStatus
    detail: str
    category: Literal["GEOMETRY", "CHEMISTRY", "STABILITY", "TARGET_PROPERTIES"]
    actual_value: Optional[Any] = None
    reference_value: Optional[Any] = None
    unit: Optional[str] = None
    source_or_method: Optional[str] = None


# ==========================================
# 4. RAG Validation Report Schemas
# ==========================================

class CitationItem(BaseModel):
    citation_id: str
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    source: str
    url_or_doi: Optional[str] = None
    page_or_section: Optional[str] = None
    relevance_summary: str


class ComparableMaterial(BaseModel):
    formula: str
    similarity_type: Literal["EXACT_MATCH", "ISOSTRUCTURAL", "SAME_CHEMICAL_SYSTEM", "KNOWN_ANALOG"]
    reported_stability: Optional[str] = None
    reported_conductivity: Optional[str] = None
    key_properties: Dict[str, Any] = Field(default_factory=dict)
    reference_source: str


class RAGValidationReport(BaseModel):
    report_id: str
    candidate_id: str
    formula: str
    reduced_formula: str
    application: str
    timestamp: str
    
    # Executive summary & overall scientific verdict
    overall_verdict: Literal["FAVORABLE_FOR_DFT", "MARGINAL_WITH_CONCERNS", "UNFAVORABLE", "INSUFFICIENT_EVIDENCE"]
    verdict_badge: str
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    executive_summary: str
    
    # Tool-computed check status counts
    checks_summary: Dict[str, ValidationCheckStatus]
    checks: List[ScientificCheckResult]
    
    # Domain specific sections
    geometry_assessment: Dict[str, Any]
    chemistry_assessment: Dict[str, Any]
    stability_assessment: Dict[str, Any]
    target_properties_assessment: Dict[str, Any]
    
    # Literature & Evidence
    literature_evidence: List[EvidenceItem]
    comparable_materials: List[ComparableMaterial]
    citations: List[CitationItem]
    
    # Transparent Scientific Explanations
    scientific_risks: List[str]
    missing_evidence_and_unknowns: List[str]
    recommended_computational_tests: List[str]
    recommended_experimental_tests: List[str]
    
    # LLM and System Provenance
    llm_provider: str
    llm_model: str
    retrieval_mode: str
    scientific_disclaimer: str = (
        "RAG scientific validation provides literature-grounded evidence and computational tool verification. "
        "It does not guarantee thermodynamic stability, synthesizability, or electrochemical performance. "
        "Literature existence of related materials does not prove stability of this specific candidate."
    )


class RunRAGValidationRequest(BaseModel):
    candidate_id: Optional[str] = None
    formula: Optional[str] = None
    cif_string: Optional[str] = None
    application: Optional[str] = "Solid electrolyte"
    energy_domain: Optional[str] = "BATTERY"
    include_literature: bool = True
    llm_provider: Optional[str] = None  # None = auto-detect configured provider or offline fallback
