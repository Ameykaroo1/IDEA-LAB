export interface PropertyConstraint {
  target?: number | null;
  min?: number | null;
  max?: number | null;
  tolerance?: number | null;
  preference?: string | null;
  type?: string | null; // "hard_constraint" | "soft_preference"
  unit?: string | null;
  confidence?: string | null;
}

export interface StructuralConstraints {
  crystal_system?: string | null;
  space_group?: string | null;
  min_atoms?: number | null;
  max_atoms?: number | null;
}

export interface RankingWeights {
  stability: number;
  band_gap: number;
  ionic_conductivity: number;
  chemistry: number;
}

export interface MaterialRequirements {
  application: string;
  energy_domain?: string;
  battery_type?: string | null;
  material_type?: string | null;
  required_elements: string[];
  preferred_elements?: string[];
  allowed_elements: string[];
  excluded_elements: string[];
  properties: Record<string, PropertyConstraint>;
  band_gap?: PropertyConstraint | null;
  energy_above_hull?: PropertyConstraint | null;
  ionic_conductivity?: PropertyConstraint | null;
  structural_constraints: StructuralConstraints;
  ranking_weights: RankingWeights;
  num_candidates: number;
}

export interface ParseResponse {
  raw_text: string;
  requirements: MaterialRequirements;
  confidences: Record<string, string>;
  ambiguities: string[];
  warnings: string[];
  needs_confirmation: boolean;
  extraction_steps: string[];
}

export interface ValidationCheckItem {
  name: string;
  passed: boolean;
  detail: string;
}

export interface StructuralValidationResult {
  status: string; // "VALID" | "INVALID"
  is_valid: boolean;
  checks: ValidationCheckItem[];
  reasons: string[];
  overlap_heuristic_flag: boolean;
  coordinates_wrapped: boolean;
  is_duplicate: boolean;
  duplicate_of_id?: string | null;
  standardized_space_group?: string | null;
  standardized_space_group_number?: number | null;
  structure_hash?: string | null;
}

export interface StabilityEvaluation {
  stability_status: string; // "COMPUTATIONALLY_FAVORABLE" | "UNFAVORABLE" | "SCREENED" | "NOT_AVAILABLE"
  energy?: number | null;
  energy_above_hull?: number | null;
  unit: string;
  relaxation_method?: string | null;
  reference_hull_source?: string | null;
  provenance: string;
  status: string;
  screening_threshold: number;
  detail: string;
}

export interface PhenomenonEvaluationItem {
  phenomenon: string;
  value?: number | null;
  unit: string;
  status: string; // "PASS" | "FAIL" | "PREFERENCE" | "NOT_AVAILABLE" | "REQUIRES_DFT"
  method?: string | null;
  provenance: string;
  passed?: boolean | null;
  detail: string;
}

export interface PhenomenaValidationResult {
  overall_status: string; // "MATCH" | "PARTIAL" | "FAIL" | "REJECTED"
  evaluations: Record<string, PhenomenonEvaluationItem>;
  summary: string;
}

export interface IonMigrationAnalysis {
  mobile_species?: string | null;
  sites_detected: number;
  pathway_detected: boolean;
  bottleneck_radius_angstrom?: number | null;
  migration_barrier?: number | null;
  unit: string;
  method: string;
  provenance: string;
  status: string;
  detail: string;
}

export interface VolumeChangeEvaluation {
  initial_volume?: number | null;
  final_volume?: number | null;
  volume_change_percent?: number | null;
  unit: string;
  method: string;
  provenance: string;
  status: string;
  is_hard_constraint: boolean;
  threshold?: number | null;
  passed?: boolean | null;
  detail: string;
}

export interface CapacityEvaluation {
  theoretical_capacity?: number | null;
  theoretical_capacity_gravimetric?: number | null;
  unit: string;
  transferable_electrons?: number | null;
  redox_species?: string | null;
  molar_mass?: number | null;
  formula: string;
  method: string;
  provenance: string;
  status: string;
  capacity_type: string;
  detail: string;
}

export interface PropertyPrediction {
  value?: number | null;
  unit: string;
  method?: string | null;
  provenance?: string; // "DATABASE" | "MATTERGEN" | "MATTERSIM" | "ML_MODEL" | "ANALYTICAL" | "MD" | "DFT" | "DEMO_SURROGATE" | "NOT_AVAILABLE"
  status?: string; // "PREDICTED" | "EVALUATED" | "SCREENED" | "NOT_AVAILABLE" | "REQUIRES_DFT"
  confidence?: number | null;
  confidence_str?: string | null;
  uncertainty?: string | null;
  source?: string; // backwards compatibility
  model?: string | null;
  reason?: string | null;
}

export interface PropertyPredictions {
  energy_above_hull: PropertyPrediction;
  band_gap: PropertyPrediction;
  ionic_conductivity: PropertyPrediction;
  formation_energy?: PropertyPrediction | null;
  capacity?: PropertyPrediction | null;
  voltage?: PropertyPrediction | null;
  volume_change?: PropertyPrediction | null;
  migration_barrier?: PropertyPrediction | null;
}

export interface ScreeningCriterionResult {
  name: string;
  passed: boolean;
  detail: string;
  actual_value?: any;
  target_value?: any;
}

export interface ScreeningResult {
  overall_status: string; // "PASS" | "FAIL"
  passed: boolean;
  criteria: ScreeningCriterionResult[];
  reasons: string[];
}

export interface RankingScoreBreakdown {
  stability_score?: number | null;
  band_gap_score?: number | null;
  conductivity_score?: number | null;
  chemistry_score?: number | null;
  volume_change_score?: number | null;
  capacity_score?: number | null;
  effective_weights: Record<string, number>;
  total_score: number;
  explanation: string;
  ranking_notes: string[];
}

export interface RequirementMatchInfo {
  compliance_status: string; // "MATCH" | "PARTIAL" | "FAIL" | "REJECTED"
  score: number;
  rank_label?: string | null; // "#1 Best Requirement Match"
  ranking_title: string;
  criteria_matches: Record<string, string>;
}

export interface NoveltyAssessment {
  result: string;
  verdict_label: string;
  matched_reference_id?: string | null;
  matched_formula?: string | null;
  matched_dataset?: string | null;
  similarity_metric?: number | null;
  reference_datasets: string[];
  structures_compared: number;
  scientific_disclaimer?: string;
}

export interface AtomSite {
  species: string;
  fract_coords: number[];
  label?: string | null;
}

export interface LatticeParams {
  a: number;
  b: number;
  c: number;
  alpha: number;
  beta: number;
  gamma: number;
  volume: number;
}

export interface Candidate {
  candidate_id: string;
  structure_hash: string;
  formula: string;
  reduced_formula: string;
  elements: string[];
  crystal_system: string;
  space_group: string;
  space_group_number?: number | null;
  lattice: LatticeParams;
  atom_count: number;
  atoms: AtomSite[];
  cif_string: string;
  cif?: string | null;
  cif_path?: string | null;
  structure?: any;
  generation_status?: string;
  generator: string;
  generation_source: string; // "MATTERGEN" | "LOCAL_DEMO" | "USER_UPLOADED"
  configured_model: string; // "MATTERGEN_BASE" | "MATTERGEN_PROPERTY_CONDITIONED" | "MATTERGEN_CSP" | "LOCAL_DEMO"
  generator_mode: string;
  generation_mode?: string;
  reference_datasets: string[];
  structural_status: string; // "VALID" | "INVALID"
  structure_status?: string;
  stability_status?: string;
  property_status?: string;
  requirement_status?: string;
  requirement_compliance: string; // "MATCH" | "PARTIAL" | "FAIL" | "REJECTED"
  reference_status?: string;
  dft_status?: string;
  rejection_reason?: string | null;
  validation: StructuralValidationResult;
  stability?: StabilityEvaluation;
  phenomena?: PhenomenaValidationResult;
  migration?: IonMigrationAnalysis | null;
  volume_change?: VolumeChangeEvaluation | null;
  capacity?: CapacityEvaluation | null;
  predictions: PropertyPredictions;
  property_provenance?: Record<string, string>;
  screening: ScreeningResult;
  ranking: RankingScoreBreakdown;
  requirement_match?: RequirementMatchInfo;
  ranking_explanation?: string[];
  novelty: NoveltyAssessment;
  rank?: number | null;
  rank_label?: string | null;
  in_dft_queue?: boolean;
  created_at: string;
}

export interface DiscoverResponse {
  job_id: string;
  status: string;
  pipeline_status?: Record<string, any>;
  generator_status?: Record<string, any>;
  property_status?: Record<string, any>;
  dataset_status?: Record<string, any>;
  generator_used: string;
  generator_mode: string;
  configured_model: string;
  generator_notice?: string | null;
  supported_conditions: string[];
  unsupported_conditions: string[];
  candidates: Candidate[];
  rejected_candidates: Candidate[];
  stats: Record<string, any>;
}

export interface ModelStatusResponse {
  mattergen?: string; // "CONNECTED" | "NOT CONFIGURED" | "ERROR"
  mattersim?: string; // "CONNECTED" | "NOT CONFIGURED" | "ERROR"
  generator: string;
  status: string;
  configured_model: string;
  checkpoint?: string | null;
  device: string;
  supported_conditions: string[];
  property_models: string[];
  dft?: string;
  reference_datasets: string[];
  notice?: string | null;
}

export interface DatasetStatusResponse {
  mp20: Record<string, any>;
  jarvis: Record<string, any>;
  total_reference_structures: number;
  last_harmonized: string;
}

export interface DFTQueueItem {
  candidate_id: string;
  formula: string;
  status: string;
  predicted_properties: Record<string, any>;
  ranking_score: number;
  rank_label?: string | null;
  reason_selected: string;
  cif_string: string;
  added_at: string;
}

export interface DashboardStats {
  generated: number;
  valid: number;
  invalid: number;
  passed_screening: number;
  potentially_novel: number;
  top_ranked: number;
  dft_queue: number;
}

// ==========================================
// RAG Scientific Validation Types
// ==========================================

export type ValidationCheckStatus = "PASS" | "FAIL" | "WARNING" | "UNKNOWN" | "NOT_RUN";

export interface ScientificCheckResult {
  name: string;
  status: ValidationCheckStatus;
  detail: string;
  category: "GEOMETRY" | "CHEMISTRY" | "STABILITY" | "TARGET_PROPERTIES";
  actual_value?: any;
  reference_value?: any;
  unit?: string | null;
  source_or_method?: string | null;
}

export interface EvidenceItem {
  chunk_id: string;
  document_id: string;
  title: string;
  authors?: string | null;
  publication_year?: number | null;
  doi_or_url?: string | null;
  page_number?: number | null;
  passage_text: string;
  relevance_score: number;
  match_type: "EXACT_FORMULA" | "CHEMICAL_ANALOG" | "SEMANTIC_SIMILARITY" | "PROPERTY_MATCH" | "DATABASE_RECORD";
  matched_formulas: string[];
  source_type: string;
}

export interface CitationItem {
  citation_id: string;
  title: string;
  authors?: string | null;
  year?: number | null;
  source: string;
  url_or_doi?: string | null;
  page_or_section?: string | null;
  relevance_summary: string;
}

export interface ComparableMaterial {
  formula: string;
  similarity_type: "EXACT_MATCH" | "ISOSTRUCTURAL" | "SAME_CHEMICAL_SYSTEM" | "KNOWN_ANALOG";
  reported_stability?: string | null;
  reported_conductivity?: string | null;
  key_properties: Record<string, any>;
  reference_source: string;
}

export interface RAGValidationReport {
  report_id: string;
  candidate_id: string;
  formula: string;
  reduced_formula: string;
  application: string;
  timestamp: string;
  overall_verdict: "FAVORABLE_FOR_DFT" | "MARGINAL_WITH_CONCERNS" | "UNFAVORABLE" | "INSUFFICIENT_EVIDENCE";
  verdict_badge: string;
  confidence_level: "HIGH" | "MEDIUM" | "LOW";
  executive_summary: string;
  checks_summary: Record<string, ValidationCheckStatus>;
  checks: ScientificCheckResult[];
  geometry_assessment: Record<string, any>;
  chemistry_assessment: Record<string, any>;
  stability_assessment: Record<string, any>;
  target_properties_assessment: Record<string, any>;
  literature_evidence: EvidenceItem[];
  comparable_materials: ComparableMaterial[];
  citations: CitationItem[];
  scientific_risks: string[];
  missing_evidence_and_unknowns: string[];
  recommended_computational_tests: string[];
  recommended_experimental_tests: string[];
  llm_provider: string;
  llm_model: string;
  retrieval_mode: string;
  scientific_disclaimer: string;
}

export interface RAGDocument {
  document_id: string;
  title: string;
  authors?: string | null;
  publication_year?: number | null;
  doi_or_url?: string | null;
  source_type: string;
  chunk_count: number;
  formulas_mentioned: string[];
}

export interface ConnectorsStatusResponse {
  materials_project: {
    name: string;
    configured: boolean;
    status: string;
    url: string;
  };
  cod: {
    name: string;
    configured: boolean;
    status: string;
    url: string;
  };
  local_catalog: {
    name: string;
    configured: boolean;
    status: string;
    database_path: string;
  };
  vector_store: {
    total_chunks: number;
    total_documents: number;
    backend: string;
  };
}
