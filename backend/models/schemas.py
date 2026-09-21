"""
Pydantic schemas and data models for CRYSTAL-X.
Defines structured schemas for requirements, NLP extraction, crystallographic validation,
stability evaluation, phenomena validation, property predictions, ranking, candidates,
and downstream DFT queue packages.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


# ==========================================
# 1. NLP & Requirements Schemas
# ==========================================

class PropertyConstraint(BaseModel):
    target: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    tolerance: Optional[float] = None
    preference: Optional[str] = None  # e.g. "high", "low", "stable", "around"
    type: Optional[str] = "soft_preference"  # "hard_constraint" vs "soft_preference"
    unit: Optional[str] = None
    confidence: Optional[str] = "High"  # High, Medium, Low


class StructuralConstraints(BaseModel):
    crystal_system: Optional[str] = None
    space_group: Optional[str] = None
    min_atoms: Optional[int] = None
    max_atoms: Optional[int] = None


class RankingWeights(BaseModel):
    stability: float = Field(default=0.4, ge=0.0, le=1.0)
    band_gap: float = Field(default=0.3, ge=0.0, le=1.0)
    ionic_conductivity: float = Field(default=0.2, ge=0.0, le=1.0)
    chemistry: float = Field(default=0.1, ge=0.0, le=1.0)


class MaterialRequirements(BaseModel):
    application: str = "Energy storage"
    energy_domain: str = "BATTERY"  # BATTERY, SOLID_ELECTROLYTE, CATHODE, ANODE, IONIC_CONDUCTOR, ENERGY_STORAGE
    battery_type: Optional[str] = None  # e.g. "lithium_ion", "sodium_ion"
    material_type: Optional[str] = None  # e.g. "sodium-based", "solid_electrolyte"
    required_elements: List[str] = Field(default_factory=list)
    preferred_elements: List[str] = Field(default_factory=list)
    allowed_elements: List[str] = Field(default_factory=list)
    excluded_elements: List[str] = Field(default_factory=list)
    properties: Dict[str, PropertyConstraint] = Field(default_factory=dict)
    band_gap: Optional[PropertyConstraint] = None
    energy_above_hull: Optional[PropertyConstraint] = None
    ionic_conductivity: Optional[PropertyConstraint] = None
    structural_constraints: StructuralConstraints = Field(default_factory=StructuralConstraints)
    ranking_weights: RankingWeights = Field(default_factory=RankingWeights)
    num_candidates: int = Field(default=10, ge=1, le=100)


class ParseRequest(BaseModel):
    text: str


class ParseResponse(BaseModel):
    raw_text: str
    requirements: MaterialRequirements
    confidences: Dict[str, str] = Field(default_factory=dict)
    ambiguities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    needs_confirmation: bool = True
    extraction_steps: List[str] = Field(default_factory=list)


class ValidateRequirementsRequest(BaseModel):
    requirements: MaterialRequirements


class ValidateRequirementsResponse(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ==========================================
# 2. Structural Validation Schemas
# ==========================================

class ValidationCheckItem(BaseModel):
    name: str
    passed: bool
    detail: str


class StructuralValidationResult(BaseModel):
    status: str = "VALID"  # "VALID" or "INVALID"
    is_valid: bool = True
    checks: List[ValidationCheckItem] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    overlap_heuristic_flag: bool = False
    coordinates_wrapped: bool = False
    is_duplicate: bool = False
    duplicate_of_id: Optional[str] = None
    standardized_space_group: Optional[str] = None
    standardized_space_group_number: Optional[int] = None
    structure_hash: Optional[str] = None


# ==========================================
# 3. Stability Evaluation Schemas
# ==========================================

class StabilityEvaluation(BaseModel):
    stability_status: str = "NOT_AVAILABLE"  # "COMPUTATIONALLY_FAVORABLE", "UNFAVORABLE", "SCREENED", "NOT_AVAILABLE"
    energy: Optional[float] = None
    energy_above_hull: Optional[float] = None
    unit: str = "eV/atom"
    relaxation_method: Optional[str] = None  # "MatterSim", "ML_FORCE_FIELD", "DEMO_SURROGATE", "NOT_AVAILABLE"
    reference_hull_source: Optional[str] = "MP-20 / Materials Project Reference Hull"
    provenance: str = "NOT_AVAILABLE"  # "DATABASE", "MATTERGEN", "MATTERSIM", "ML_MODEL", "ANALYTICAL", "MD", "DFT", "DEMO_SURROGATE", "NOT_AVAILABLE"
    status: str = "NOT_AVAILABLE"
    screening_threshold: float = 0.05  # PROJECT SCREENING THRESHOLD
    detail: str = "Stability assessment based on energy above hull."


# ==========================================
# 4. Property Prediction & Provenance Schemas
# ==========================================

class PropertyPrediction(BaseModel):
    value: Optional[float] = None
    unit: str
    method: Optional[str] = None
    provenance: str = "NOT_AVAILABLE"  # "DATABASE", "MATTERGEN", "MATTERSIM", "ML_MODEL", "ANALYTICAL", "MD", "DFT", "DEMO_SURROGATE", "NOT_AVAILABLE"
    status: str = "NOT_AVAILABLE"      # "PREDICTED", "EVALUATED", "SCREENED", "NOT_AVAILABLE", "REQUIRES_DFT"
    confidence: Optional[float] = None
    confidence_str: Optional[str] = "NOT_AVAILABLE"
    uncertainty: Optional[str] = "NOT_AVAILABLE"
    
    # Backwards compatibility fields
    source: Optional[str] = None
    model: Optional[str] = None
    reason: Optional[str] = None


class PropertyPredictions(BaseModel):
    energy_above_hull: PropertyPrediction
    band_gap: PropertyPrediction
    ionic_conductivity: PropertyPrediction
    formation_energy: Optional[PropertyPrediction] = None
    capacity: Optional[PropertyPrediction] = None
    volume_change: Optional[PropertyPrediction] = None
    migration_barrier: Optional[PropertyPrediction] = None


# ==========================================
# 5. Specialized Phenomena Schemas
# ==========================================

class PhenomenonEvaluationItem(BaseModel):
    phenomenon: str
    value: Optional[float] = None
    unit: str = ""
    status: str = "NOT_AVAILABLE"  # "PASS", "FAIL", "PREFERENCE", "NOT_AVAILABLE", "REQUIRES_DFT"
    method: Optional[str] = None
    provenance: str = "NOT_AVAILABLE"
    passed: Optional[bool] = None
    detail: str = ""


class PhenomenaValidationResult(BaseModel):
    overall_status: str = "PARTIAL"  # "MATCH", "PARTIAL", "FAIL", "REJECTED"
    evaluations: Dict[str, PhenomenonEvaluationItem] = Field(default_factory=dict)
    summary: str = ""


class IonMigrationAnalysis(BaseModel):
    mobile_species: Optional[str] = None
    sites_detected: int = 0
    pathway_detected: bool = False
    bottleneck_radius_angstrom: Optional[float] = None
    migration_barrier: Optional[float] = None
    unit: str = "eV"
    method: str = "PERCOLATION_ANALYSIS"
    provenance: str = "NOT_AVAILABLE"
    status: str = "REQUIRES_DFT"
    detail: str = "Ion transport pathway analysis. Accurate barrier requires downstream NEB/DFT."


class VolumeChangeEvaluation(BaseModel):
    initial_volume: Optional[float] = None
    final_volume: Optional[float] = None
    volume_change_percent: Optional[float] = None
    unit: str = "%"
    method: str = "ION_INSERTION_LATTICE_RELAXATION"
    provenance: str = "NOT_AVAILABLE"
    status: str = "NOT_AVAILABLE"
    is_hard_constraint: bool = False
    threshold: Optional[float] = None
    passed: Optional[bool] = None
    detail: str = ""


class CapacityEvaluation(BaseModel):
    theoretical_capacity: Optional[float] = None
    unit: str = "mAh/g"
    transferable_electrons: Optional[float] = None
    redox_species: Optional[str] = None
    molar_mass: Optional[float] = None
    formula: str = ""
    method: str = "ANALYTICAL_FARADAY"
    provenance: str = "ANALYTICAL"
    status: str = "EVALUATED"
    capacity_type: str = "THEORETICAL CAPACITY"
    detail: str = "Calculated via Q = nF / (3.6 * M). Not experimental capacity."


# ==========================================
# 6. Screening Schemas
# ==========================================

class ScreeningCriterionResult(BaseModel):
    name: str
    passed: bool
    detail: str
    actual_value: Optional[Any] = None
    target_value: Optional[Any] = None


class ScreeningResult(BaseModel):
    overall_status: str = "PASS"  # "PASS" or "FAIL"
    passed: bool = True
    criteria: List[ScreeningCriterionResult] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)


# ==========================================
# 7. Ranking Schemas
# ==========================================

class RankingScoreBreakdown(BaseModel):
    stability_score: Optional[float] = None  # 0-100
    band_gap_score: Optional[float] = None    # 0-100
    conductivity_score: Optional[float] = None # 0-100 or None if not available
    chemistry_score: Optional[float] = None   # 0-100
    volume_change_score: Optional[float] = None # 0-100
    capacity_score: Optional[float] = None    # 0-100
    
    # Effective weights used (after renormalizing for unavailable properties)
    effective_weights: Dict[str, float] = Field(default_factory=dict)
    total_score: float = 0.0  # 0-100
    explanation: str = ""
    ranking_notes: List[str] = Field(default_factory=list)


class RequirementMatchInfo(BaseModel):
    compliance_status: str = "MATCH"  # "MATCH", "PARTIAL", "FAIL", "REJECTED"
    score: float = 0.0
    rank_label: Optional[str] = None  # e.g. "#1 Best Requirement Match"
    ranking_title: str = "Ranked according to your confirmed material requirements"
    criteria_matches: Dict[str, str] = Field(default_factory=dict)


# ==========================================
# 8. Novelty & Reference Comparison
# ==========================================

class NoveltyAssessment(BaseModel):
    result: str  # "DUPLICATE OF MP-20", "DUPLICATE OF JARVIS-DFT", "SIMILAR TO MP-20", "SIMILAR TO JARVIS-DFT", "NO CLOSE MATCH IN MP-20/JARVIS REFERENCE DATASET"
    verdict_label: str
    matched_reference_id: Optional[str] = None
    matched_formula: Optional[str] = None
    matched_dataset: Optional[str] = None  # "MP-20" or "JARVIS-DFT"
    similarity_metric: Optional[float] = None
    reference_datasets: List[str] = Field(default_factory=lambda: ["MP-20", "JARVIS-DFT"])
    structures_compared: int = 5
    scientific_disclaimer: str = "Generated by the configured generative model; no close match found in the configured MP-20/JARVIS reference datasets. Does not claim absolute scientific novelty."


# ==========================================
# 9. Candidate Record Schema
# ==========================================

class AtomSite(BaseModel):
    species: str
    fract_coords: List[float]
    label: Optional[str] = None


class LatticeParams(BaseModel):
    a: float
    b: float
    c: float
    alpha: float
    beta: float
    gamma: float
    volume: float


class Candidate(BaseModel):
    candidate_id: str
    structure_hash: str
    formula: str
    reduced_formula: str
    elements: List[str]
    crystal_system: str
    space_group: str
    space_group_number: Optional[int] = None
    lattice: LatticeParams
    atom_count: int
    atoms: List[AtomSite]
    cif_string: str
    cif: Optional[str] = None
    cif_path: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None
    
    # Provenance and Model configuration
    generation_status: str = "GENERATED"
    generation_source: str = "LOCAL_DEMO"  # "MATTERGEN" or "LOCAL_DEMO" or "USER_UPLOADED"
    generator_mode: str = "DEMO_GENERATOR"  # "REAL_GENERATOR" or "DEMO_GENERATOR" or "USER_IMPORT"
    configured_model: str = "LOCAL_DEMO"
    generator_checkpoint: Optional[str] = None
    generation_seed: Optional[int] = None
    generator: str = "LOCAL_DEMO"  # For backwards compatibility
    source_datasets: List[str] = Field(default_factory=lambda: ["MP-20", "JARVIS-DFT"])
    reference_datasets: List[str] = Field(default_factory=lambda: ["MP-20", "JARVIS-DFT"])
    
    # Multi-Status Model
    structural_status: str = "VALID"  # "VALID" or "INVALID"
    structure_status: str = "VALID"   # "VALID" or "INVALID"
    stability_status: str = "NOT_AVAILABLE"  # "COMPUTATIONALLY_FAVORABLE", "UNFAVORABLE", "SCREENED", "NOT_AVAILABLE"
    property_status: str = "PARTIALLY_EVALUATED"  # "EVALUATED", "PARTIALLY_EVALUATED", "NOT_AVAILABLE"
    requirement_status: str = "MATCH"  # "MATCH", "PARTIAL", "FAIL", "REJECTED"
    requirement_compliance: str = "MATCH"  # For backwards compatibility
    reference_status: str = "NO_CLOSE_MATCH"  # "DUPLICATE_OF_MP20", "SIMILAR_TO_MP20", "NO_CLOSE_MATCH", etc.
    dft_status: str = "NOT_PERFORMED"  # "NOT_PERFORMED", "QUEUED", "COMPLETED"
    rejection_reason: Optional[str] = None
    
    # Evaluation Packages
    validation: StructuralValidationResult
    stability: StabilityEvaluation
    phenomena: PhenomenaValidationResult
    predictions: PropertyPredictions
    property_provenance: Dict[str, str] = Field(default_factory=dict)
    
    # Specialized Phenomenon Analysis
    migration: Optional[IonMigrationAnalysis] = None
    volume_change: Optional[VolumeChangeEvaluation] = None
    capacity: Optional[CapacityEvaluation] = None
    
    screening: ScreeningResult
    ranking: RankingScoreBreakdown
    requirement_match: RequirementMatchInfo = Field(default_factory=RequirementMatchInfo)
    ranking_explanation: List[str] = Field(default_factory=list)
    novelty: NoveltyAssessment
    reference_comparison: Optional[Dict[str, Any]] = None
    
    rank: Optional[int] = None
    rank_label: Optional[str] = None  # "#1 Best Requirement Match"
    in_dft_queue: bool = False
    created_at: str


# ==========================================
# 10. Generation & Discovery Request/Response
# ==========================================

class DiscoverRequest(BaseModel):
    requirements: MaterialRequirements
    generator_mode: Optional[str] = None  # "mattergen" or "demo" or auto-detect
    configured_model: Optional[str] = None  # "MATTERGEN_BASE", "MATTERGEN_PROPERTY_CONDITIONED", "MATTERGEN_CSP", "LOCAL_DEMO"


class DiscoverResponse(BaseModel):
    job_id: str
    status: str
    pipeline_status: Dict[str, Any] = Field(default_factory=dict)
    generator_status: Dict[str, Any] = Field(default_factory=dict)
    property_status: Dict[str, Any] = Field(default_factory=dict)
    dataset_status: Dict[str, Any] = Field(default_factory=dict)
    generator_used: str
    generator_mode: str
    configured_model: str
    generator_notice: Optional[str] = None
    supported_conditions: List[str] = Field(default_factory=list)
    unsupported_conditions: List[str] = Field(default_factory=list)
    candidates: List[Candidate]
    rejected_candidates: List[Candidate] = Field(default_factory=list)
    stats: Dict[str, int]


class ModelStatusResponse(BaseModel):
    mattergen: str = "NOT CONFIGURED"  # "CONNECTED", "NOT CONFIGURED", "ERROR"
    mattersim: str = "NOT CONFIGURED"  # "CONNECTED", "NOT CONFIGURED", "ERROR"
    generator: str = "LOCAL DEMO"      # "REAL MATTERGEN" or "LOCAL DEMO"
    status: str = "NOT CONFIGURED"     # "CONNECTED" or "NOT CONFIGURED"
    configured_model: str = "LOCAL_DEMO"
    checkpoint: Optional[str] = None
    device: str = "CPU"                # "CUDA" or "CPU"
    supported_conditions: List[str] = Field(default_factory=list)
    property_models: List[str] = Field(default_factory=list)
    dft: str = "NOT CONFIGURED"        # "AVAILABLE", "QUEUED", "NOT CONFIGURED"
    reference_datasets: List[str] = Field(default_factory=lambda: ["MP-20", "JARVIS-DFT"])
    notice: Optional[str] = None


class DatasetStatusResponse(BaseModel):
    mp20: Dict[str, Any]
    jarvis: Dict[str, Any]
    total_reference_structures: int
    last_harmonized: str


class ReRankRequest(BaseModel):
    candidate_ids: Optional[List[str]] = None
    weights: RankingWeights


# ==========================================
# 11. DFT Queue Schemas
# ==========================================

class DFTQueueItem(BaseModel):
    candidate_id: str
    formula: str
    structure_hash: Optional[str] = None
    status: str = "QUEUED"  # "QUEUED", "IN_PROGRESS", "COMPLETED", "NOT_PERFORMED"
    properties_to_validate: List[str] = Field(default_factory=lambda: ["energy", "band_gap", "migration_barrier", "volume_change"])
    predicted_properties: Dict[str, Any] = Field(default_factory=dict)
    ranking_score: float = 0.0
    rank_label: Optional[str] = None
    reason_selected: str = "High ranking candidate selected for high-fidelity DFT verification."
    cif_string: str = ""
    priority: str = "Normal"
    added_at: str = ""


class DFTExportResponse(BaseModel):
    export_dir: str
    exported_candidates: List[str]
    package_zip_path: Optional[str] = None
    disclaimer: str = "DFT validation is downstream and is not performed by this prototype."


# ==========================================
# 12. CIF Upload Schema
# ==========================================

class UploadCIFResponse(BaseModel):
    candidate: Candidate
    message: str
