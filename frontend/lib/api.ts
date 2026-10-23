import {
  MaterialRequirements,
  ParseResponse,
  Candidate,
  RankingWeights,
  DFTQueueItem,
  DashboardStats,
  DiscoverResponse,
  ModelStatusResponse,
  DatasetStatusResponse
} from "@/types";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    return "/api";
  }
  return "http://127.0.0.1:8000/api";
}

const API_BASE = getApiBase();

export async function getHealth(): Promise<{ status: string; mattergen_available: boolean }> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function getModelStatus(): Promise<ModelStatusResponse> {
  const res = await fetch(`${API_BASE}/model/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch model status");
  return res.json();
}

export async function getDatasetsStatus(): Promise<DatasetStatusResponse> {
  const res = await fetch(`${API_BASE}/datasets/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch datasets status");
  return res.json();
}

export async function getStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch dashboard statistics");
  return res.json();
}

export async function parseRequirements(text: string): Promise<ParseResponse> {
  const res = await fetch(`${API_BASE}/requirements/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Parse error" }));
    throw new Error(err.detail || "Failed to parse natural language requirement");
  }
  return res.json();
}

export async function validateRequirements(requirements: MaterialRequirements): Promise<{ is_valid: boolean; errors: string[]; warnings: string[] }> {
  const res = await fetch(`${API_BASE}/requirements/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirements }),
  });
  if (!res.ok) throw new Error("Validation check failed");
  return res.json();
}

export async function runDiscovery(
  requirements: MaterialRequirements,
  generator_mode?: string,
  configured_model?: string
): Promise<DiscoverResponse> {
  const res = await fetch(`${API_BASE}/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirements, generator_mode, configured_model }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Discovery failed" }));
    throw new Error(err.detail || "Discovery execution failed");
  }
  return res.json();
}

export async function getCandidates(): Promise<Candidate[]> {
  const res = await fetch(`${API_BASE}/candidates`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch candidates");
  return res.json();
}

export async function getCandidate(id: string): Promise<Candidate> {
  const res = await fetch(`${API_BASE}/candidates/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch candidate ${id}`);
  return res.json();
}

export async function reRankCandidates(weights: RankingWeights): Promise<Candidate[]> {
  const res = await fetch(`${API_BASE}/rank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ weights }),
  });
  if (!res.ok) throw new Error("Failed to re-rank candidates");
  return res.json();
}

export async function uploadCIF(file: File): Promise<{ candidate: Candidate; message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload-cif`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Failed to upload and validate CIF");
  }
  return res.json();
}

export async function getDftQueue(): Promise<DFTQueueItem[]> {
  const res = await fetch(`${API_BASE}/dft-queue`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch DFT queue");
  return res.json();
}

export async function addToDftQueue(candidateId: string, reason: string = "High-priority candidate for energy application"): Promise<void> {
  const formData = new FormData();
  formData.append("candidate_id", candidateId);
  formData.append("reason", reason);

  const res = await fetch(`${API_BASE}/dft-queue`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to add candidate to DFT queue");
}

export async function removeFromDftQueue(candidateId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/dft-queue/${candidateId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to remove from DFT queue");
}

export async function exportDftPackage(): Promise<{ export_dir: string; exported_candidates: string[]; disclaimer: string }> {
  const res = await fetch(`${API_BASE}/dft-queue/export`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Export failed" }));
    throw new Error(err.detail || "Failed to export DFT package");
  }
  return res.json();
}

export async function getDatasets(params?: {
  query?: string;
  dataset_source?: string;
  element?: string;
  max_ehull?: number;
  stable_only?: boolean;
  page?: number;
  limit?: number;
}): Promise<any> {
  const queryParams = new URLSearchParams();
  if (params?.query) queryParams.append("query", params.query);
  if (params?.dataset_source && params.dataset_source !== "ALL") queryParams.append("dataset_source", params.dataset_source);
  if (params?.element) queryParams.append("element", params.element);
  if (params?.max_ehull !== undefined) queryParams.append("max_ehull", params.max_ehull.toString());
  if (params?.stable_only) queryParams.append("stable_only", "true");
  if (params?.page) queryParams.append("page", params.page.toString());
  if (params?.limit) queryParams.append("limit", params.limit.toString());

  const qs = queryParams.toString();
  const url = qs ? `${API_BASE}/datasets?${qs}` : `${API_BASE}/datasets`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load reference datasets");
  return res.json();
}

export async function resetSystem(): Promise<void> {
  await fetch(`${API_BASE}/reset`, { method: "POST" });
}

// ==========================================
// RAG Scientific Validation API Calls
// ==========================================

export async function getConnectorsStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/rag/connectors/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch scientific connectors status");
  return res.json();
}

export async function getRAGDocuments(): Promise<{ count: number; documents: any[] }> {
  const res = await fetch(`${API_BASE}/rag/documents`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load RAG knowledge base documents");
  return res.json();
}

export async function uploadRAGDocument(formData: FormData): Promise<any> {
  const res = await fetch(`${API_BASE}/rag/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Failed to upload and index scientific document");
  }
  return res.json();
}

export async function retrieveEvidence(payload: {
  formula: string;
  reduced_formula?: string;
  elements?: string[];
  application?: string;
  max_results?: number;
  include_external_sources?: boolean;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/rag/retrieve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to retrieve scientific evidence");
  return res.json();
}

export async function runRAGValidation(payload: {
  candidate_id?: string;
  formula?: string;
  cif_string?: string;
  application?: string;
  llm_provider?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/rag/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Validation failed" }));
    throw new Error(err.detail || "RAG Scientific Validation failed");
  }
  return res.json();
}

export async function getRAGReport(candidate_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/rag/reports/${candidate_id}`, { cache: "no-store" });
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch report for candidate ${candidate_id}`);
  }
  return res.json();
}
