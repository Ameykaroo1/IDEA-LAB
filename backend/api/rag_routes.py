"""
FastAPI Routes for RAG Scientific Validation and Explainability Module.
Exposes endpoints for:
1. Scientific document ingestion (PDF & text)
2. Hybrid scientific retrieval & literature search
3. RAG-based scientific validation & report generation
4. Report caching & retrieval
5. External data source connector statuses
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from backend.models.rag_schemas import (
    RAGValidationReport,
    RunRAGValidationRequest,
    RetrievalRequest,
    RetrievalResponse,
    DocumentUploadResponse
)
from backend.services.rag.rag_service import RAGValidationService

rag_router = APIRouter(prefix="/api/rag", tags=["RAG Scientific Validation"])

# Singleton RAG service instance
_rag_service = None

def get_rag_service() -> RAGValidationService:
    global _rag_service
    if _rag_service is None:
        try:
            from backend.api.routes import data_service
        except Exception:
            data_service = None
        _rag_service = RAGValidationService(data_service=data_service)
    return _rag_service


@rag_router.get("/connectors/status")
def get_connectors_status(service: RAGValidationService = Depends(get_rag_service)):
    """
    Returns the real-time connectivity status of scientific data sources:
    Materials Project, COD, Local Reference Database, and the Vector Store.
    """
    return service.get_connectors_status()


@rag_router.get("/documents")
def list_documents(service: RAGValidationService = Depends(get_rag_service)):
    """
    Lists all indexed peer-reviewed papers and documents in the RAG knowledge base.
    """
    return {
        "count": len(service.list_documents()),
        "documents": service.list_documents()
    }


@rag_router.post("/documents/upload", response_model=DocumentUploadResponse)
def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    doi: Optional[str] = Form(None),
    service: RAGValidationService = Depends(get_rag_service)
):
    """
    Uploads and indexes a scientific research paper (PDF, plain text, or markdown).
    Performs chunking, formula extraction, and dense vector indexing.
    """
    filename = file.filename or "unknown_file"
    try:
        content_bytes = file.file.read()
    except Exception:
        content_bytes = b""
    
    if filename.lower().endswith(".pdf"):
        res = service.ingest_pdf_file(
            pdf_bytes=content_bytes,
            filename=filename,
            title=title,
            authors=authors,
            year=year,
            doi=doi
        )
    else:
        text_content = content_bytes.decode("utf-8", errors="replace")
        doc_title = title or filename
        res = service.ingest_text_document(
            content=text_content,
            title=doc_title,
            authors=authors,
            year=year,
            doi=doi
        )

    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)
    return res


@rag_router.post("/retrieve", response_model=RetrievalResponse)
def retrieve_scientific_evidence(
    request: RetrievalRequest,
    service: RAGValidationService = Depends(get_rag_service)
):
    """
    Performs hybrid scientific retrieval combining:
    1. Exact formula match
    2. Chemical system match
    3. Dense semantic cosine similarity
    4. Database query to MP-20 / JARVIS / Materials Project / COD
    """
    return service.retrieve_evidence(request)


@rag_router.post("/validate", response_model=RAGValidationReport)
def run_rag_validation(
    request: RunRAGValidationRequest,
    service: RAGValidationService = Depends(get_rag_service)
):
    """
    Runs full RAG scientific validation on a candidate:
    - Deterministic crystallographic & chemical validation (pymatgen)
    - Hybrid retrieval of literature & database records
    - Evidence-grounded LLM reasoning & risk assessment
    - Caches report by candidate ID
    """
    try:
        return service.validate_candidate(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG validation failed: {str(e)}")


@rag_router.get("/reports/{candidate_id}", response_model=RAGValidationReport)
def get_validation_report(
    candidate_id: str,
    service: RAGValidationService = Depends(get_rag_service)
):
    """
    Retrieves a cached RAG scientific validation report for a candidate ID.
    """
    report = service.get_report(candidate_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"No RAG validation report found for candidate '{candidate_id}'.")
    return report
