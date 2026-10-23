"""
Central RAG Scientific Validation Service for CRYSTAL-X.
Orchestrates:
1. Document ingestion and vector storage
2. Hybrid scientific retrieval & database connectors
3. Crystallographic & chemical validation tool execution
4. LLM-based evidence-grounded scientific synthesis
5. Report caching and persistence
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser

from backend.models.rag_schemas import (
    RAGValidationReport,
    RunRAGValidationRequest,
    RetrievalRequest,
    RetrievalResponse,
    DocumentUploadResponse,
    DocumentChunk
)
from backend.services.rag.vector_store import RAGVectorStore
from backend.services.rag.ingestion import ScientificDocumentIngestionService
from backend.services.rag.connectors import (
    MaterialsProjectConnector,
    CrystallographyOpenDatabaseConnector,
    LocalCatalogConnector
)
from backend.services.rag.retrieval import HybridScientificRetrievalService
from backend.services.rag.scientific_validator import ScientificValidator
from backend.services.rag.llm_reasoning import LLMScientificReasoningService
from backend.services.data_service import DataService


class RAGValidationService:
    def __init__(
        self,
        data_service: Optional[DataService] = None,
        storage_dir: Optional[str] = None
    ):
        self.data_service = data_service or DataService()
        self.vector_store = RAGVectorStore(storage_dir=storage_dir)
        self.ingestion_service = ScientificDocumentIngestionService(self.vector_store)
        
        self.mp_connector = MaterialsProjectConnector()
        self.cod_connector = CrystallographyOpenDatabaseConnector()
        self.local_catalog = LocalCatalogConnector()

        self.retrieval_service = HybridScientificRetrievalService(
            vector_store=self.vector_store,
            mp_connector=self.mp_connector,
            cod_connector=self.cod_connector,
            local_catalog=self.local_catalog
        )

        self.validator = ScientificValidator()
        self.reasoning_service = LLMScientificReasoningService()

        # In-memory and disk report storage
        self._reports: Dict[str, RAGValidationReport] = {}
        self.reports_file = os.path.join(self.vector_store.storage_dir, "validation_reports.json")
        self._load_cached_reports()

    def _load_cached_reports(self):
        if os.path.exists(self.reports_file):
            try:
                with open(self.reports_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self._reports[k] = RAGValidationReport(**v)
            except Exception:
                pass

    def _save_cached_reports(self):
        try:
            data = {k: v.model_dump() for k, v in self._reports.items()}
            with open(self.reports_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def list_documents(self) -> List[Dict[str, Any]]:
        return self.vector_store.get_all_documents()

    def ingest_text_document(
        self,
        content: str,
        title: str,
        authors: Optional[str] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None
    ) -> DocumentUploadResponse:
        return self.ingestion_service.ingest_text_document(
            content=content,
            title=title,
            authors=authors,
            year=year,
            doi_or_url=doi
        )

    def ingest_pdf_file(
        self,
        pdf_bytes: bytes,
        filename: str,
        title: Optional[str] = None,
        authors: Optional[str] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None
    ) -> DocumentUploadResponse:
        return self.ingestion_service.ingest_pdf_file(
            pdf_bytes=pdf_bytes,
            filename=filename,
            title=title,
            authors=authors,
            year=year,
            doi_or_url=doi
        )

    def retrieve_evidence(self, request: RetrievalRequest) -> RetrievalResponse:
        return self.retrieval_service.retrieve(request)

    def validate_candidate(self, request: RunRAGValidationRequest) -> RAGValidationReport:
        """
        Executes end-to-end RAG scientific validation on a candidate:
        1. Resolves candidate structure and metadata from Candidate store or custom input
        2. Executes deterministic validation tools (pymatgen, charge balance, distances, Ehull)
        3. Retrieves hybrid scientific evidence and comparable materials
        4. Invokes LLM reasoning for evidence synthesis and transparent risk analysis
        5. Caches and returns structured validation report
        """
        candidate = None
        struct = None
        cif_string = request.cif_string
        formula = request.formula
        app = request.application or "Solid electrolyte"
        candidate_id = request.candidate_id or f"custom-{formula or 'candidate'}"

        # 1. If candidate_id is known in DataService, load candidate record
        if request.candidate_id:
            candidate = self.data_service.get_candidate(request.candidate_id)
            if candidate:
                formula = candidate.formula
                cif_string = candidate.cif_string
                app = getattr(candidate, "application", app)

        # 2. Parse pymatgen Structure
        if cif_string:
            try:
                parser = CifParser.from_str(cif_string)
                structs = parser.parse_structures(primitive=False)
                if structs:
                    struct = structs[0]
                    if not formula:
                        formula = struct.composition.reduced_formula
            except Exception:
                struct = None

        if not formula and struct is not None:
            formula = struct.composition.reduced_formula

        if not formula:
            formula = "UnknownComposition"

        reduced_formula = formula
        if struct is not None:
            try:
                reduced_formula = struct.composition.reduced_formula
            except Exception:
                reduced_formula = formula

        # Extract predictions if available on candidate
        ehull = None
        band_gap = None
        conductivity = None

        if candidate:
            if candidate.predictions:
                if candidate.predictions.energy_above_hull and candidate.predictions.energy_above_hull.value is not None:
                    ehull = candidate.predictions.energy_above_hull.value
                if candidate.predictions.band_gap and candidate.predictions.band_gap.value is not None:
                    band_gap = candidate.predictions.band_gap.value
                if candidate.predictions.ionic_conductivity and candidate.predictions.ionic_conductivity.value is not None:
                    conductivity = candidate.predictions.ionic_conductivity.value

        # 3. Run Deterministic Validation Tools
        checks, checks_summary, domain_data = self.validator.run_all_checks(
            struct=struct,
            cif_string=cif_string,
            formula=formula,
            application=app,
            predicted_ehull=ehull,
            predicted_band_gap=band_gap,
            predicted_conductivity=conductivity
        )

        # 4. Run Hybrid Retrieval
        elements = [e.symbol for e in struct.composition.elements] if struct else []
        retrieval_req = RetrievalRequest(
            formula=formula,
            reduced_formula=reduced_formula,
            elements=elements,
            application=app,
            max_results=6,
            include_external_sources=True
        )
        retrieval_res = self.retrieval_service.retrieve(retrieval_req)

        # 5. Run LLM Scientific Reasoning
        report = self.reasoning_service.generate_scientific_report(
            candidate_id=candidate_id,
            formula=formula,
            reduced_formula=reduced_formula,
            application=app,
            checks=checks,
            checks_summary=checks_summary,
            domain_data=domain_data,
            retrieved_evidence=retrieval_res.evidence,
            comparable_materials=retrieval_res.comparable_materials,
            preferred_provider=request.llm_provider
        )

        # 6. Cache and return report
        self._reports[candidate_id] = report
        self._save_cached_reports()
        return report

    def get_report(self, candidate_id: str) -> Optional[RAGValidationReport]:
        return self._reports.get(candidate_id)

    def get_connectors_status(self) -> Dict[str, Any]:
        return {
            "materials_project": {
                "name": "Materials Project API (v2)",
                "configured": self.mp_connector.is_configured(),
                "status": "CONNECTED" if self.mp_connector.is_configured() else "NOT_CONFIGURED (Requires MP_API_KEY in .env)",
                "url": "https://materialsproject.org/"
            },
            "cod": {
                "name": "Crystallography Open Database (COD)",
                "configured": True,
                "status": "AVAILABLE (Public Open Access)",
                "url": "https://www.crystallography.net/cod/"
            },
            "local_catalog": {
                "name": "Local Reference Catalog (MP-20 & JARVIS-DFT)",
                "configured": True,
                "status": "AVAILABLE (139,131 SQLite Records)",
                "database_path": self.local_catalog.db_path
            },
            "vector_store": {
                "total_chunks": len(self.vector_store.get_all_chunks()),
                "total_documents": len(self.vector_store.get_all_documents()),
                "backend": "ChromaDB + Offline Scientific Embeddings"
            }
        }
