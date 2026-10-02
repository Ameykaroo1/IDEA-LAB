"""
FastAPI Route Handlers for CRYSTAL-X.
Exposes all endpoints for NLP parsing, discovery pipeline, structural validation,
stability evaluation, phenomena validation, screening, ranking, CIF export/import,
and DFT queue management.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import PlainTextResponse

from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter, CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from backend.models.schemas import (
    ParseRequest,
    ParseResponse,
    ValidateRequirementsRequest,
    ValidateRequirementsResponse,
    DiscoverRequest,
    DiscoverResponse,
    MaterialRequirements,
    Candidate,
    ReRankRequest,
    RankingScoreBreakdown,
    RequirementMatchInfo,
    DFTQueueItem,
    DFTExportResponse,
    UploadCIFResponse,
    LatticeParams,
    AtomSite,
    ModelStatusResponse,
    DatasetStatusResponse
)
from backend.services.nlp_requirement_service import NLPRequirementService
from backend.services.constraint_normalizer import ConstraintNormalizer
from backend.services.generator_service import GeneratorDispatchService
from backend.services.demo_generator import DemoCrystalGenerator
from backend.services.mattergen_adapter import MatterGenAdapter
from backend.services.validation_service import StructuralValidationService
from backend.services.stability_service import StabilityService
from backend.services.property_service import PropertyEvaluationService
from backend.services.ionic_conductivity_service import IonicConductivityService
from backend.services.volume_change_service import VolumeChangeService
from backend.services.capacity_service import CapacityService
from backend.services.phenomena_router import PhenomenaRouter
from backend.services.screening_service import PropertyScreeningService
from backend.services.ranking_service import MultiCriteriaRankingEngine
from backend.services.novelty_service import NoveltyService
from backend.services.cif_service import CIFService
from backend.services.dft_service import DFTQueueService
from backend.services.data_service import DataService

router = APIRouter(prefix="/api")

# Instantiate service dependencies
nlp_service = NLPRequirementService()
demo_gen = DemoCrystalGenerator()
mattergen_adapter = MatterGenAdapter()
dispatch_service = GeneratorDispatchService(demo_gen, mattergen_adapter)
validation_service = StructuralValidationService(min_atomic_distance_heuristic=0.7)
stability_service = StabilityService(screening_threshold=0.05)
ionic_service = IonicConductivityService(ml_model_available=False)
volume_service = VolumeChangeService()
capacity_service = CapacityService()
property_service = PropertyEvaluationService(
    stability_service=stability_service,
    ionic_service=ionic_service,
    volume_service=volume_service,
    capacity_service=capacity_service
)
phenomena_router = PhenomenaRouter(
    mattersim_available=stability_service.mattersim_available,
    mattergen_available=mattergen_adapter.is_available()
)
screening_service = PropertyScreeningService()
data_service = DataService()
novelty_service = NoveltyService()
dft_service = DFTQueueService()


def _get_crystal_symmetry_info(struct: Structure):
    """
    Safely extracts crystal system and space group symbol from a pymatgen Structure.
    """
    try:
        sga = SpacegroupAnalyzer(struct, symprec=0.1)
        crystal_sys = sga.get_crystal_system().capitalize()
        space_group = f"{sga.get_space_group_symbol()} (#{sga.get_space_group_number()})"
        sg_num = sga.get_space_group_number()
        return crystal_sys, space_group, sg_num
    except Exception:
        crystal_sys = getattr(struct.lattice, "crystal_system", "Cubic").capitalize()
        return crystal_sys, "P1 (#1)", 1


# ==========================================
# 1. Health & Statistics
# ==========================================

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": "CRYSTAL-X Scientific API",
        "timestamp": datetime.now().isoformat(),
        "configured_model": mattergen_adapter.get_configured_model() if mattergen_adapter.is_available() else "LOCAL_DEMO",
        "mattergen_available": mattergen_adapter.is_available(),
        "mattersim_available": stability_service.mattersim_available,
        "reference_datasets": ["MP-20", "JARVIS-DFT"]
    }


@router.get("/stats")
def get_dashboard_stats():
    queue_count = len(dft_service.get_queue())
    return data_service.get_dashboard_stats(dft_queue_count=queue_count)


@router.post("/reset")
def reset_system_state():
    data_service.clear_candidates()
    return {"message": "Candidate store reset successfully.", "stats": data_service.get_dashboard_stats()}


# ==========================================
# 2. NLP Requirement Endpoints
# ==========================================

@router.post("/requirements/parse", response_model=ParseResponse)
def parse_requirements(request: ParseRequest):
    """
    Parses natural language material requirement into structured constraints.
    """
    extracted = nlp_service.parse_text(request.text)
    response = ConstraintNormalizer.normalize(extracted)
    return response


@router.post("/requirements/validate", response_model=ValidateRequirementsResponse)
def validate_requirements(request: ValidateRequirementsRequest):
    """
    Validates reviewed or edited requirements prior to generation.
    """
    return ConstraintNormalizer.validate_requirements(request.requirements)


# ==========================================
# 3. Full Generative Discovery Pipeline
# ==========================================

@router.post("/discover", response_model=DiscoverResponse)
def run_discovery_pipeline(request: DiscoverRequest):
    """
    Executes the 14-step scientific discovery pipeline:
    1. Requirement Extraction & Confirmation
    2. Phenomena Routing
    3. MatterGen Candidate Generation (with Regeneration Loop if needed)
    4. Crystallographic Structural Validation
    5. Symmetry & Structure Standardization
    6. StructureMatcher Deduplication
    7. Stability Evaluation (MatterSim / screening threshold)
    8. Phenomena & Property Evaluation
    9. Hard Constraint Filtering
    10. Dynamic Soft Preference Ranking
    11. MP-20 Comparison
    12. JARVIS Comparison
    13. 3D WebGL / CIF Export
    14. DFT Validation Queue Linking
    """
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    reqs = request.requirements
    target_count = reqs.num_candidates or 10

    # 1. Dispatch Generator & Map Conditions
    generator, mode_name, model_name, notice = dispatch_service.get_active_generator(
        request.generator_mode,
        request.configured_model
    )

    _, supported_conds, unsupported_conds = mattergen_adapter.map_requirements_to_conditions(reqs)
    routes = phenomena_router.route_requirements(reqs)

    # 2. Generation & Regeneration Loop
    # Attempts generation in batches until enough valid candidates are found or max attempts reached (3)
    max_attempts = 3
    attempt = 0
    all_raw_candidates: List[Dict[str, Any]] = []
    seen_hashes = set()
    seen_structures = []

    all_evaluated_candidates: List[Candidate] = []
    rejected_candidates: List[Candidate] = []

    while attempt < max_attempts:
        attempt += 1
        needed = target_count - len(all_evaluated_candidates)
        if needed <= 0:
            break

        # In attempt 1, generate target_count candidates; in subsequent attempts, generate needed
        batch_size = target_count if attempt == 1 else needed
        batch_raw = generator.generate(reqs, batch_size)

        for raw in batch_raw:
            cand_id = raw["candidate_id"]
            cif_str = raw["raw_cif"]
            struct = raw["structure"]

            # A. Structural Validation (Crystallography & physical validity)
            val_result = validation_service.validate_structure(
                struct=struct,
                cif_string=cif_str,
                requirements=reqs,
                existing_structures=seen_structures
            )

            struct_hash = val_result.structure_hash or validation_service.compute_structure_hash(struct)

            # Deduplication check
            if struct_hash in seen_hashes or val_result.is_duplicate:
                val_result.is_duplicate = True
                val_result.is_valid = False
                val_result.status = "INVALID"
                val_result.reasons.append(f"Duplicate structure topology (hash {struct_hash}).")

            if not val_result.is_duplicate:
                seen_hashes.add(struct_hash)
                seen_structures.append((cand_id, struct))

            # B. Property & Phenomena Evaluation
            (
                predictions,
                stability,
                phenomena_res,
                prop_provenance,
                migration_res,
                vol_res,
                cap_res
            ) = property_service.evaluate_all(struct, reqs, generator_mode=mode_name)

            # C. Property Screening
            screening_res, req_match = screening_service.screen_candidate(struct, predictions, reqs)

            # Determine rejection criteria
            is_rejected = (
                not val_result.is_valid
                or not screening_res.passed
                or req_match.compliance_status in ("FAIL", "REJECTED")
                or (vol_res.is_hard_constraint and not vol_res.passed)
            )

            rejection_reason = None
            if is_rejected:
                reasons_combined = val_result.reasons + screening_res.reasons
                if vol_res.is_hard_constraint and not vol_res.passed:
                    reasons_combined.append(vol_res.detail)
                rejection_reason = "; ".join(reasons_combined) if reasons_combined else "Violated confirmed hard requirements."
                req_status = "REJECTED"
                compliance_label = "REJECTED"
            else:
                req_status = phenomena_res.overall_status  # "MATCH" or "PARTIAL"
                compliance_label = "MATCH"

            # D. Dynamic Requirement-Driven Ranking Score
            ranking_res = MultiCriteriaRankingEngine.calculate_score(
                predictions=predictions,
                validation=val_result,
                requirements=reqs,
                phenomena=phenomena_res,
                compliance_status=compliance_label
            )
            req_match.score = ranking_res.total_score
            req_match.compliance_status = compliance_label

            # E. MP-20 & JARVIS-DFT Reference Comparison
            novelty_res = novelty_service.evaluate_novelty(struct)
            ref_status = novelty_res.result

            # Symmetry & Lattice information
            crystal_sys, spg_str, spg_num = _get_crystal_symmetry_info(struct)

            lattice_p = LatticeParams(
                a=round(struct.lattice.a, 4),
                b=round(struct.lattice.b, 4),
                c=round(struct.lattice.c, 4),
                alpha=round(struct.lattice.alpha, 2),
                beta=round(struct.lattice.beta, 2),
                gamma=round(struct.lattice.gamma, 2),
                volume=round(struct.lattice.volume, 2)
            )

            atoms = [
                AtomSite(
                    species=site.species_string,
                    fract_coords=[round(float(c), 4) for c in site.frac_coords],
                    label=f"{site.species_string}{idx+1}"
                )
                for idx, site in enumerate(struct.sites)
            ]

            cand_obj = Candidate(
                candidate_id=cand_id,
                structure_hash=struct_hash,
                formula=struct.composition.formula,
                reduced_formula=struct.composition.reduced_formula,
                elements=[e.symbol for e in struct.composition.elements],
                crystal_system=crystal_sys,
                space_group=spg_str,
                space_group_number=spg_num,
                lattice=lattice_p,
                atom_count=len(struct),
                atoms=atoms,
                cif_string=cif_str,
                cif=cif_str,
                structure=struct.as_dict(),
                generation_status="GENERATED",
                generation_source=raw.get("generation_source", "LOCAL_DEMO"),
                generator_mode=raw.get("generation_mode", mode_name),
                configured_model=model_name,
                generator=raw.get("generator_name", "GenerativeCrystalModel"),
                structural_status=val_result.status,
                structure_status=val_result.status,
                stability_status=stability.stability_status,
                property_status="EVALUATED" if phenomena_res.overall_status == "MATCH" else "PARTIALLY_EVALUATED",
                requirement_status=req_status,
                requirement_compliance=compliance_label,
                reference_status=ref_status,
                dft_status="NOT_PERFORMED",
                rejection_reason=rejection_reason,
                validation=val_result,
                stability=stability,
                phenomena=phenomena_res,
                predictions=predictions,
                property_provenance=prop_provenance,
                migration=migration_res,
                volume_change=vol_res,
                capacity=cap_res,
                screening=screening_res,
                ranking=ranking_res,
                requirement_match=req_match,
                novelty=novelty_res,
                created_at=datetime.now().isoformat()
            )

            cand_obj.ranking_explanation = MultiCriteriaRankingEngine.generate_ranking_explanation(cand_obj, reqs)

            if is_rejected:
                rejected_candidates.append(cand_obj)
            else:
                all_evaluated_candidates.append(cand_obj)

        if len(all_evaluated_candidates) > 0:
            break

    # 3. Dynamic Ranking of Surviving Candidates
    ranked_candidates = MultiCriteriaRankingEngine.rank_candidates(all_evaluated_candidates, reqs)

    # Store candidates in memory / local database
    data_service.store_candidates(ranked_candidates + rejected_candidates)

    queue_count = len(dft_service.get_queue())
    stats = data_service.get_dashboard_stats(dft_queue_count=queue_count)

    pipeline_status = {
        "total_generated": len(ranked_candidates) + len(rejected_candidates),
        "valid_crystallographic": sum(1 for c in (ranked_candidates + rejected_candidates) if c.structural_status == "VALID"),
        "surviving_hard_constraints": len(ranked_candidates),
        "rejected_count": len(rejected_candidates),
        "regeneration_attempts_used": attempt,
        "max_regeneration_attempts": max_attempts
    }

    generator_status = {
        "active_generator": generator.get_mode_name(),
        "mattergen_available": mattergen_adapter.is_available(),
        "configured_model": model_name
    }

    property_status = {
        "stability_method": "MatterSim" if stability_service.mattersim_available else "Demo Surrogate Screening",
        "routes": {k: v.to_dict() for k, v in routes.items()}
    }

    dataset_status = novelty_service.get_dataset_status()

    return DiscoverResponse(
        job_id=job_id,
        status="completed",
        pipeline_status=pipeline_status,
        generator_status=generator_status,
        property_status=property_status,
        dataset_status=dataset_status,
        generator_used=generator.get_mode_name(),
        generator_mode=mode_name,
        configured_model=model_name,
        generator_notice=notice,
        supported_conditions=supported_conds,
        unsupported_conditions=unsupported_conds,
        candidates=ranked_candidates,
        rejected_candidates=rejected_candidates,
        stats=stats
    )


# ==========================================
# 4. Model & Reference Dataset Status
# ==========================================

@router.get("/model/status", response_model=ModelStatusResponse)
def get_model_status():
    """
    Returns truthful status of MatterGen model backend, MatterSim, and property models.
    """
    mg_status = mattergen_adapter.get_model_status()
    ms_status = stability_service.get_mattersim_status()
    
    return ModelStatusResponse(
        mattergen=mg_status.get("mattergen", "NOT CONFIGURED"),
        mattersim=ms_status,
        generator=mg_status.get("generator", "LOCAL DEMO"),
        status=mg_status.get("status", "NOT CONFIGURED"),
        configured_model=mg_status.get("configured_model", "LOCAL_DEMO"),
        checkpoint=mg_status.get("checkpoint"),
        device=mg_status.get("device", "CPU"),
        supported_conditions=mg_status.get("supported_conditions", []),
        property_models=mg_status.get("property_models", []),
        dft="NOT CONFIGURED",
        reference_datasets=["MP-20", "JARVIS-DFT"],
        notice=mg_status.get("notice")
    )


@router.get("/datasets/status", response_model=DatasetStatusResponse)
def get_datasets_status():
    """
    Returns status and counts of MP-20 and JARVIS-DFT reference datasets.
    """
    return novelty_service.get_dataset_status()


# ==========================================
# 5. Candidates Management Endpoints
# ==========================================

@router.get("/candidates", response_model=List[Candidate])
def list_candidates():
    cands = data_service.get_all_candidates()
    for c in cands:
        c.in_dft_queue = dft_service.is_in_queue(c.candidate_id)
    return cands


@router.get("/candidates/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str):
    cand = data_service.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")
    cand.in_dft_queue = dft_service.is_in_queue(candidate_id)
    return cand


@router.get("/candidates/{candidate_id}/cif")
def download_candidate_cif(candidate_id: str):
    cand = data_service.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")
    
    filename = f"{candidate_id}_{cand.reduced_formula.replace(' ', '')}.cif"
    return PlainTextResponse(
        content=cand.cif_string,
        media_type="chemical/x-cif",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/export-cifs")
def export_cifs(candidate_ids: Optional[List[str]] = None, mode: str = "selected"):
    all_cands = data_service.get_all_candidates()
    if mode == "top5":
        target_cands = [c for c in all_cands if c.validation.is_valid][:5]
    elif mode == "all_valid":
        target_cands = [c for c in all_cands if c.validation.is_valid]
    elif candidate_ids:
        target_cands = [c for c in all_cands if c.candidate_id in candidate_ids]
    else:
        target_cands = all_cands

    cand_dicts = [
        {"candidate_id": c.candidate_id, "reduced_formula": c.reduced_formula, "cif_string": c.cif_string}
        for c in target_cands
    ]
    zip_bytes = CIFService.create_cif_zip_package(cand_dicts)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="crystal_candidates.zip"'}
    )


@router.post("/rank", response_model=List[Candidate])
def re_rank_candidates(request: ReRankRequest):
    cands = data_service.get_all_candidates()
    dummy_reqs = MaterialRequirements(ranking_weights=request.weights)
    ranked = MultiCriteriaRankingEngine.rank_candidates(cands, dummy_reqs, weights=request.weights)
    data_service.store_candidates(ranked)
    return ranked


# ==========================================
# 6. CIF Upload & Validation
# ==========================================

@router.post("/upload-cif", response_model=UploadCIFResponse)
async def upload_cif(file: UploadFile = File(...)):
    try:
        content_bytes = await file.read()
        cif_content = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    try:
        parser = CifParser.from_str(cif_content)
        struct = parser.parse_structures(primitive=False)[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Crystallographic parse error: {str(e)}")

    val_result = validation_service.validate_structure(struct, cif_string=cif_content)
    struct_hash = val_result.structure_hash or validation_service.compute_structure_hash(struct)
    cand_id = f"UPL-{uuid.uuid4().hex[:6].upper()}"

    default_reqs = MaterialRequirements()
    (
        predictions,
        stability,
        phenomena_res,
        prop_provenance,
        migration_res,
        vol_res,
        cap_res
    ) = property_service.evaluate_all(struct, default_reqs, generator_mode="USER_IMPORT")

    screening_res, req_match = screening_service.screen_candidate(struct, predictions, default_reqs)
    ranking_res = MultiCriteriaRankingEngine.calculate_score(predictions, val_result, default_reqs)
    req_match.score = ranking_res.total_score
    novelty_res = novelty_service.evaluate_novelty(struct)

    crystal_sys, spg_str, spg_num = _get_crystal_symmetry_info(struct)

    lattice_p = LatticeParams(
        a=round(struct.lattice.a, 4),
        b=round(struct.lattice.b, 4),
        c=round(struct.lattice.c, 4),
        alpha=round(struct.lattice.alpha, 2),
        beta=round(struct.lattice.beta, 2),
        gamma=round(struct.lattice.gamma, 2),
        volume=round(struct.lattice.volume, 2)
    )

    atoms = [
        AtomSite(
            species=site.species_string,
            fract_coords=[round(float(c), 4) for c in site.frac_coords],
            label=f"{site.species_string}{idx+1}"
        )
        for idx, site in enumerate(struct.sites)
    ]

    candidate = Candidate(
        candidate_id=cand_id,
        structure_hash=struct_hash,
        formula=struct.composition.formula,
        reduced_formula=struct.composition.reduced_formula,
        elements=[e.symbol for e in struct.composition.elements],
        crystal_system=crystal_sys,
        space_group=spg_str,
        space_group_number=spg_num,
        lattice=lattice_p,
        atom_count=len(struct),
        atoms=atoms,
        cif_string=cif_content,
        generation_status="UPLOADED_BY_USER",
        generation_source="USER_UPLOADED",
        configured_model="USER_IMPORT",
        generator_mode="USER_IMPORT",
        generator="UserUploadedCIF",
        structural_status=val_result.status,
        structure_status=val_result.status,
        stability_status=stability.stability_status,
        property_status="EVALUATED",
        requirement_status=req_match.compliance_status,
        requirement_compliance=req_match.compliance_status,
        reference_status=novelty_res.result,
        dft_status="NOT_PERFORMED",
        validation=val_result,
        stability=stability,
        phenomena=phenomena_res,
        predictions=predictions,
        property_provenance=prop_provenance,
        migration=migration_res,
        volume_change=vol_res,
        capacity=cap_res,
        screening=screening_res,
        ranking=ranking_res,
        requirement_match=req_match,
        novelty=novelty_res,
        rank=1,
        rank_label="#1 Best Requirement Match",
        created_at=datetime.now().isoformat()
    )

    data_service.store_candidate(candidate)

    return UploadCIFResponse(
        candidate=candidate,
        message=f"Successfully imported CIF for {candidate.reduced_formula}. Status: {candidate.validation.status}"
    )


# ==========================================
# 7. DFT Validation Queue Endpoints
# ==========================================

@router.get("/dft-queue", response_model=List[DFTQueueItem])
def get_dft_queue():
    return dft_service.get_queue()


@router.post("/dft-queue")
def add_to_dft_queue(
    candidate_id: str = Form(...),
    reason: str = Form("High ranking candidate for clean-energy battery application")
):
    cand = data_service.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    item = DFTQueueItem(
        candidate_id=cand.candidate_id,
        formula=cand.reduced_formula,
        structure_hash=cand.structure_hash,
        status="QUEUED",
        properties_to_validate=["energy", "band_gap", "migration_barrier", "volume_change"],
        predicted_properties={
            "energy_above_hull": cand.predictions.energy_above_hull.value,
            "band_gap": cand.predictions.band_gap.value,
            "ionic_conductivity": cand.predictions.ionic_conductivity.value
        },
        ranking_score=cand.ranking.total_score,
        rank_label=cand.rank_label,
        reason_selected=reason,
        cif_string=cand.cif_string,
        priority="Normal",
        added_at=datetime.now().isoformat()
    )
    dft_service.add_to_queue(item)
    cand.dft_status = "QUEUED"
    cand.in_dft_queue = True
    data_service.store_candidate(cand)
    return {"message": f"Candidate {candidate_id} added to DFT validation queue.", "item": item}


@router.delete("/dft-queue/{candidate_id}")
def remove_from_dft_queue(candidate_id: str):
    removed = dft_service.remove_from_queue(candidate_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Candidate not found in DFT queue.")
    cand = data_service.get_candidate(candidate_id)
    if cand:
        cand.dft_status = "NOT_PERFORMED"
        cand.in_dft_queue = False
        data_service.store_candidate(cand)
    return {"message": f"Removed {candidate_id} from DFT queue."}


@router.post("/dft-queue/export", response_model=DFTExportResponse)
def export_dft_package():
    if not dft_service.get_queue():
        raise HTTPException(status_code=400, detail="DFT queue is empty. Add candidates before exporting.")
    return dft_service.export_package()


# ==========================================
# 8. Datasets Browser
# ==========================================

@router.get("/datasets")
def get_reference_datasets(
    query: Optional[str] = None,
    dataset_source: Optional[str] = None,
    element: Optional[str] = None,
    max_ehull: Optional[float] = None,
    min_band_gap: Optional[float] = None,
    stable_only: bool = False,
    limit: int = 24,
    page: int = 1
):
    search_res = data_service.search_reference_materials(
        query=query,
        dataset_source=dataset_source,
        element=element,
        max_ehull=max_ehull,
        min_band_gap=min_band_gap,
        stable_only=stable_only,
        limit=min(limit, 100),
        page=max(1, page)
    )
    status = novelty_service.get_dataset_status()
    return {
        "dataset_name": "Unified MP-20 & JARVIS-DFT Reference Catalog",
        "description": "Authentic reference inorganic crystal materials from MP-20 (Materials Project, 45,229) and JARVIS-DFT (NIST, 93,902) used for structure matching, novelty checks, and stability benchmarking.",
        "total_reference_structures": status.get("total_reference_structures", 139131),
        "mp20_count": status.get("mp20", {}).get("count", 45229),
        "jarvis_count": status.get("jarvis", {}).get("count", 93902),
        "total_records": search_res["total_records"],
        "page": search_res["page"],
        "limit": search_res["limit"],
        "total_pages": search_res["total_pages"],
        "materials": search_res["materials"]
    }


# ==========================================
# 9. Individual Pipeline Stage Endpoints
# ==========================================

@router.post("/generate")
def generate_candidates_endpoint(request: DiscoverRequest):
    """Generates crystal structures for the confirmed requirements."""
    generator, mode_name, model_name, notice = dispatch_service.get_active_generator(
        request.generator_mode, request.configured_model
    )
    raw_candidates = generator.generate(request.requirements, request.requirements.num_candidates or 10)
    return {
        "generator_used": generator.get_mode_name(),
        "configured_model": model_name,
        "count": len(raw_candidates),
        "candidates": raw_candidates
    }


@router.post("/candidates/{candidate_id}/validate")
def validate_candidate_endpoint(candidate_id: str):
    """Validates structural crystallographic integrity of a specific candidate."""
    cand = data_service.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")
    return cand.validation


@router.post("/screen")
def screen_candidate_endpoint(candidate_id: str, requirements: MaterialRequirements):
    """Evaluates candidate against specific material requirements."""
    cand = data_service.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")
    struct = Structure.from_str(cand.cif_string, fmt="cif")
    screening_res, req_match = screening_service.screen_candidate(struct, cand.predictions, requirements)
    return {"screening": screening_res, "requirement_match": req_match}


@router.post("/novelty/check")
def check_novelty_endpoint(candidate_id: str):
    """Performs crystallographic comparison against MP-20 and JARVIS-DFT."""
    cand = data_service.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")
    struct = Structure.from_str(cand.cif_string, fmt="cif")
    return novelty_service.evaluate_novelty(struct)
