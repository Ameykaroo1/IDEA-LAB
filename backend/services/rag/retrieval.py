"""
Hybrid Scientific Retrieval Service for CRYSTAL-X RAG.
Combines:
1. Exact formula and reduced formula matching (highest priority)
2. Elemental subsystem / chemical family matching
3. Keyword & property tag filtering
4. Cosine similarity vector search
5. External database queries (Materials Project, COD, Local Catalog)
Ensures transparent relevance scoring and explicit 'no-evidence-found' handling.
"""

import re
from typing import List, Dict, Any, Optional, Set
from backend.models.rag_schemas import (
    EvidenceItem,
    RetrievalRequest,
    RetrievalResponse,
    DocumentChunk
)
from backend.services.rag.vector_store import RAGVectorStore
from backend.services.rag.connectors import (
    MaterialsProjectConnector,
    CrystallographyOpenDatabaseConnector,
    LocalCatalogConnector
)


class HybridScientificRetrievalService:
    def __init__(
        self,
        vector_store: RAGVectorStore,
        mp_connector: Optional[MaterialsProjectConnector] = None,
        cod_connector: Optional[CrystallographyOpenDatabaseConnector] = None,
        local_catalog: Optional[LocalCatalogConnector] = None
    ):
        self.vector_store = vector_store
        self.mp_connector = mp_connector or MaterialsProjectConnector()
        self.cod_connector = cod_connector or CrystallographyOpenDatabaseConnector()
        self.local_catalog = local_catalog or LocalCatalogConnector()

    @staticmethod
    def _normalize_formula(formula: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", formula)

    @staticmethod
    def _get_elements(formula: str) -> List[str]:
        return sorted(list(set(re.findall(r"[A-Z][a-z]?", formula))))

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        target_formula = self._normalize_formula(request.formula)
        reduced = self._normalize_formula(request.reduced_formula or request.formula)
        target_elements = request.elements or self._get_elements(target_formula)
        chem_system = "-".join(sorted(target_elements)) if target_elements else ""

        # 1. Query vector store for candidates
        query_text = request.query_text or f"{target_formula} {request.application or ''} ionic conductivity stability band gap structure"
        similar_chunks = self.vector_store.search_similar(query_text, top_k=20)

        scored_evidence: List[EvidenceItem] = []
        retrieval_notes: List[str] = []

        target_set = {target_formula.lower(), reduced.lower()}

        for chunk, sim_score in similar_chunks:
            chunk_formulas_lower = [f.lower() for f in chunk.formulas_mentioned]
            chunk_text_lower = chunk.content.lower()

            # Check exact formula match
            has_exact = any(tf in chunk_formulas_lower or tf in chunk_text_lower for tf in target_set)
            
            # Check elemental overlap
            chunk_elements = set()
            for cf in chunk.formulas_mentioned:
                chunk_elements.update(self._get_elements(cf))
            
            elem_overlap = len(set(target_elements).intersection(chunk_elements)) if target_elements else 0
            elem_ratio = elem_overlap / max(1, len(target_elements))

            # Composite hybrid scoring
            if has_exact:
                match_type = "EXACT_FORMULA"
                relevance = 0.60 + (sim_score * 0.40)  # High boost for exact formula match
            elif elem_ratio >= 0.75:
                match_type = "CHEMICAL_ANALOG"
                relevance = 0.40 + (elem_ratio * 0.30) + (sim_score * 0.30)
            elif any(tag in chunk.property_tags for tag in ["ionic_conductivity", "thermodynamic_stability"]):
                match_type = "PROPERTY_MATCH"
                relevance = 0.25 + (sim_score * 0.50)
            else:
                match_type = "SEMANTIC_SIMILARITY"
                relevance = sim_score * 0.70

            relevance = round(min(0.99, max(0.10, relevance)), 3)

            scored_evidence.append(EvidenceItem(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.title,
                authors=chunk.authors,
                publication_year=chunk.publication_year,
                doi_or_url=chunk.doi_or_url,
                page_number=chunk.page_number,
                passage_text=chunk.content,
                relevance_score=relevance,
                match_type=match_type,
                matched_formulas=[f for f in chunk.formulas_mentioned if any(el in target_elements for el in self._get_elements(f))],
                source_type=chunk.source_type
            ))

        # Sort evidence by relevance score descending
        scored_evidence.sort(key=lambda e: e.relevance_score, reverse=True)
        top_evidence = scored_evidence[:request.max_results]

        # 2. Query external & local materials databases
        comparable_materials: List[Dict[str, Any]] = []
        ext_status: Dict[str, str] = {}

        # Local catalog
        local_res = self.local_catalog.lookup_formula_and_system(target_formula, chem_system, limit=4)
        ext_status["Local Reference Database (MP-20 / JARVIS-DFT)"] = local_res.get("status", "UNKNOWN")
        for rec in local_res.get("records", []):
            comparable_materials.append(rec)

        # Materials Project & COD
        if request.include_external_sources:
            mp_res = self.mp_connector.lookup_formula(target_formula)
            ext_status["Materials Project API"] = mp_res.get("status", "NOT_CONFIGURED")
            for rec in mp_res.get("records", []):
                comparable_materials.append(rec)

            cod_res = self.cod_connector.lookup_formula(target_formula)
            ext_status["Crystallography Open Database (COD)"] = cod_res.get("status", "OFFLINE")
            for rec in cod_res.get("records", []):
                comparable_materials.append(rec)

        # 3. Determine overall evidence found status
        evidence_found = len(top_evidence) > 0 or len(comparable_materials) > 0

        if not evidence_found:
            retrieval_notes.append(
                f"No direct scientific literature or database records found for exact formula '{target_formula}' "
                f"or related chemical system '{chem_system}' in the local knowledge base."
            )
        else:
            exact_count = sum(1 for e in top_evidence if e.match_type == "EXACT_FORMULA")
            if exact_count > 0:
                retrieval_notes.append(f"Identified {exact_count} direct exact-formula literature passage(s).")
            else:
                retrieval_notes.append(
                    "No exact formula match in indexed literature; retrieved closest chemical analogs and property benchmarks."
                )

        return RetrievalResponse(
            query=query_text,
            target_formula=target_formula,
            evidence_found=evidence_found,
            total_retrieved=len(top_evidence),
            evidence=top_evidence,
            comparable_materials=comparable_materials,
            external_source_status=ext_status,
            retrieval_notes=retrieval_notes
        )
