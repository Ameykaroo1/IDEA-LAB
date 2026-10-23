"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  ShieldCheck, 
  BookOpen, 
  AlertCircle, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  Search, 
  Upload, 
  RefreshCw, 
  ExternalLink, 
  FileText, 
  Layers, 
  Database, 
  Cpu, 
  ArrowRight,
  Info,
  ChevronDown,
  ChevronUp,
  FileCheck
} from "lucide-react";
import { 
  getCandidates, 
  runRAGValidation, 
  getRAGReport, 
  getRAGDocuments, 
  uploadRAGDocument, 
  getConnectorsStatus 
} from "@/lib/api";
import { 
  Candidate, 
  RAGValidationReport, 
  ValidationCheckStatus, 
  ScientificCheckResult, 
  EvidenceItem, 
  ConnectorsStatusResponse 
} from "@/types";

export default function ScientificValidationPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>("");
  const [customFormula, setCustomFormula] = useState("");
  const [customCif, setCustomCif] = useState("");
  const [application, setApplication] = useState("Solid electrolyte");
  const [mode, setMode] = useState<"candidate" | "custom">("candidate");

  // Validation report state
  const [report, setReport] = useState<RAGValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Category filter for checks
  const [activeCategory, setActiveCategory] = useState<string>("ALL");

  // Knowledge base state
  const [activeTab, setActiveTab] = useState<"report" | "knowledge_base">("report");
  const [documents, setDocuments] = useState<any[]>([]);
  const [connectors, setConnectors] = useState<any | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadAuthors, setUploadAuthors] = useState("");
  const [uploadYear, setUploadYear] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  // Quick preset candidates
  const samplePresets = [
    { label: "Li10GeP2S12 (LGPS Superionic)", formula: "Li10GeP2S12", app: "Solid electrolyte" },
    { label: "Li7La3Zr2O12 (LLZO Garnet)", formula: "Li7La3Zr2O12", app: "Solid electrolyte" },
    { label: "LiFePO4 (Olivine Cathode)", formula: "LiFePO4", app: "Battery cathode" },
    { label: "Na3Zr2Si2PO12 (NASICON)", formula: "Na3Zr2Si2PO12", app: "Solid electrolyte" },
    { label: "Si (Diamond Cubic)", formula: "Si", app: "Anode material" }
  ];

  // Load existing generated candidates & connectors status
  useEffect(() => {
    getCandidates()
      .then((data) => {
        setCandidates(data);
        if (data.length > 0) {
          setSelectedCandidateId(data[0].candidate_id);
        }
      })
      .catch((e) => console.log("No candidates loaded:", e));

    loadKnowledgeBase();
  }, []);

  const loadKnowledgeBase = async () => {
    try {
      const docsRes = await getRAGDocuments();
      setDocuments(docsRes.documents);
      const connRes = await getConnectorsStatus();
      setConnectors(connRes);
    } catch (e) {
      console.log("Could not load KB:", e);
    }
  };

  const handleRunValidation = async () => {
    setError(null);
    setLoading(true);
    setReport(null);

    try {
      let payload: any = {};
      if (mode === "candidate") {
        if (!selectedCandidateId) {
          throw new Error("Please select a candidate or switch to custom input.");
        }
        const cand = candidates.find((c) => c.candidate_id === selectedCandidateId);
        payload = {
          candidate_id: selectedCandidateId,
          formula: cand?.formula,
          cif_string: cand?.cif_string,
          application: application
        };
      } else {
        if (!customFormula.trim()) {
          throw new Error("Please enter a chemical formula.");
        }
        payload = {
          formula: customFormula.trim(),
          cif_string: customCif.trim() || undefined,
          application: application
        };
      }

      const res = await runRAGValidation(payload);
      setReport(res);
      setActiveTab("report");
    } catch (err: any) {
      setError(err.message || "RAG Scientific Validation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    setUploadMessage(null);

    const formData = new FormData();
    formData.append("file", uploadFile);
    if (uploadTitle.trim()) formData.append("title", uploadTitle.trim());
    if (uploadAuthors.trim()) formData.append("authors", uploadAuthors.trim());
    if (uploadYear.trim()) formData.append("year", uploadYear.trim());

    try {
      const res = await uploadRAGDocument(formData);
      setUploadMessage(res.message);
      setUploadFile(null);
      setUploadTitle("");
      setUploadAuthors("");
      setUploadYear("");
      await loadKnowledgeBase();
    } catch (err: any) {
      setUploadMessage(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  // Helper for check status badges
  const renderStatusBadge = (status: ValidationCheckStatus) => {
    switch (status) {
      case "PASS":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" /> PASS
          </span>
        );
      case "FAIL":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3 h-3" /> FAIL
          </span>
        );
      case "WARNING":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3" /> WARNING
          </span>
        );
      case "UNKNOWN":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
            <HelpCircle className="w-3 h-3" /> UNKNOWN
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-50 text-slate-500 border border-slate-200">
            NOT RUN
          </span>
        );
    }
  };

  // Helper for verdict styling
  const getVerdictStyle = (verdict: string) => {
    switch (verdict) {
      case "FAVORABLE_FOR_DFT":
        return {
          bg: "bg-emerald-50 border-emerald-200 text-emerald-900",
          badgeBg: "bg-emerald-600 text-white",
          icon: CheckCircle2
        };
      case "MARGINAL_WITH_CONCERNS":
        return {
          bg: "bg-amber-50 border-amber-200 text-amber-900",
          badgeBg: "bg-amber-600 text-white",
          icon: AlertTriangle
        };
      case "UNFAVORABLE":
        return {
          bg: "bg-rose-50 border-rose-200 text-rose-900",
          badgeBg: "bg-rose-600 text-white",
          icon: XCircle
        };
      default:
        return {
          bg: "bg-slate-50 border-slate-200 text-slate-800",
          badgeBg: "bg-slate-600 text-white",
          icon: HelpCircle
        };
    }
  };

  const filteredChecks = report
    ? report.checks.filter((c) => activeCategory === "ALL" || c.category === activeCategory)
    : [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                Scientific Module
              </span>
              <span className="text-xs text-slate-400 font-mono">RAG-VALIDATION-V1</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-emerald-600" />
              RAG-Based Scientific Validation & Literature Grounding
            </h1>
            <p className="text-xs text-slate-600 max-w-3xl">
              Cross-validates generated crystal structures against peer-reviewed literature, Materials Project, 
              Crystallography Open Database (COD), and 139,131 reference structures. Synthesizes crystallographic tool checks 
              with literature evidence without hallucinating thermodynamic stability.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("report")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === "report" 
                  ? "bg-emerald-600 text-white" 
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              Validation Studio
            </button>
            <button
              onClick={() => {
                setActiveTab("knowledge_base");
                loadKnowledgeBase();
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                activeTab === "knowledge_base" 
                  ? "bg-emerald-600 text-white" 
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              Literature Library ({documents.length})
            </button>
          </div>
        </div>
      </div>

      {activeTab === "report" ? (
        <>
          {/* Candidate Selection & Controls */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setMode("candidate")}
                  className={`text-xs font-semibold pb-2 -mb-4 border-b-2 transition ${
                    mode === "candidate"
                      ? "border-emerald-600 text-emerald-700"
                      : "border-transparent text-slate-500 hover:text-slate-900"
                  }`}
                >
                  Select Generated Candidate ({candidates.length})
                </button>
                <button
                  onClick={() => setMode("custom")}
                  className={`text-xs font-semibold pb-2 -mb-4 border-b-2 transition ${
                    mode === "custom"
                      ? "border-emerald-600 text-emerald-700"
                      : "border-transparent text-slate-500 hover:text-slate-900"
                  }`}
                >
                  Custom Formula / CIF Input
                </button>
              </div>

              {/* Quick Presets */}
              <div className="hidden lg:flex items-center gap-1.5 text-[11px] text-slate-500">
                <span className="font-semibold text-slate-700">Benchmarks:</span>
                {samplePresets.map((p) => (
                  <button
                    key={p.formula}
                    onClick={() => {
                      setMode("custom");
                      setCustomFormula(p.formula);
                      setApplication(p.app);
                    }}
                    className="px-2 py-0.5 rounded bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 border border-slate-200 text-slate-600 font-mono text-[10px] transition"
                  >
                    {p.formula}
                  </button>
                ))}
              </div>
            </div>

            {mode === "candidate" ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-xs font-medium text-slate-700">Choose Candidate Crystal</label>
                  {candidates.length > 0 ? (
                    <select
                      value={selectedCandidateId}
                      onChange={(e) => setSelectedCandidateId(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    >
                      {candidates.map((c) => (
                        <option key={c.candidate_id} value={c.candidate_id}>
                          {c.formula} ({c.reduced_formula}) — {c.crystal_system} {c.space_group} [Score: {c.ranking?.total_score?.toFixed(1) || "N/A"}]
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500 flex items-center justify-between">
                      <span>No candidates in current session library.</span>
                      <Link href="/discover" className="text-emerald-600 hover:underline font-medium">
                        Generate candidates in Discovery Studio →
                      </Link>
                    </div>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-700">Application Context</label>
                  <select
                    value={application}
                    onChange={(e) => setApplication(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  >
                    <option value="Solid electrolyte">Solid electrolyte (High Li/Na ion conduction)</option>
                    <option value="Battery cathode">Battery cathode (High theoretical capacity)</option>
                    <option value="Anode material">Anode material (Low insertion voltage)</option>
                    <option value="Energy storage framework">Energy storage framework (Open framework)</option>
                  </select>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-700">Chemical Formula</label>
                  <input
                    type="text"
                    value={customFormula}
                    onChange={(e) => setCustomFormula(e.target.value)}
                    placeholder="e.g. Li10GeP2S12 or Na3V2(PO4)3"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-700">Application Target</label>
                  <select
                    value={application}
                    onChange={(e) => setApplication(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  >
                    <option value="Solid electrolyte">Solid electrolyte</option>
                    <option value="Battery cathode">Battery cathode</option>
                    <option value="Anode material">Anode material</option>
                    <option value="Energy storage framework">Energy storage framework</option>
                  </select>
                </div>

                <div className="space-y-1.5 md:col-span-3">
                  <label className="text-xs font-medium text-slate-700">
                    Optional Crystallographic CIF (Recommended for Geometry & Space Group checks)
                  </label>
                  <textarea
                    rows={3}
                    value={customCif}
                    onChange={(e) => setCustomCif(e.target.value)}
                    placeholder="Paste optional CIF string here..."
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-[11px] font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>
            )}

            {/* Run Button */}
            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-2 text-[11px] text-slate-500">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Deterministic Crystallographic Tools + Hybrid RAG + Scientific Synthesis</span>
              </div>

              <button
                onClick={handleRunValidation}
                disabled={loading}
                className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition flex items-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing & Retrieving Literature...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>Run Scientific Validation (RAG)</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-3">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{error}</span>
            </div>
          )}

          {/* Validation Results Report */}
          {report && (
            <div className="space-y-8 animate-fadeIn">
              {/* Executive Verdict Banner */}
              {(() => {
                const style = getVerdictStyle(report.overall_verdict);
                const IconComponent = style.icon;
                return (
                  <div className={`border rounded-xl p-6 ${style.bg} space-y-4`}>
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-black/5 pb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-white shadow-sm border border-black/5">
                          <IconComponent className="w-6 h-6 text-slate-800" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${style.badgeBg}`}>
                              {report.verdict_badge}
                            </span>
                            <span className="text-xs font-mono text-slate-600">
                              Confidence: {report.confidence_level}
                            </span>
                          </div>
                          <h2 className="text-lg font-bold text-slate-900 mt-1">
                            {report.formula} ({report.reduced_formula}) — {report.application}
                          </h2>
                        </div>
                      </div>

                      <div className="text-right text-[11px] font-mono text-slate-600">
                        <div>Engine: {report.llm_provider} ({report.llm_model})</div>
                        <div>Retrieved Passages: {report.literature_evidence.length} | Citations: {report.citations.length}</div>
                      </div>
                    </div>

                    <div className="text-xs text-slate-800 leading-relaxed bg-white/70 backdrop-blur-sm p-4 rounded-lg border border-black/5">
                      <strong className="font-semibold text-slate-900">Executive Summary: </strong>
                      {report.executive_summary}
                    </div>

                    {/* Scientific Disclaimer */}
                    <div className="flex items-center gap-2 text-[11px] text-slate-600 italic">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                      <span>{report.scientific_disclaimer}</span>
                    </div>
                  </div>
                );
              })()}

              {/* Status Counters Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {(["PASS", "FAIL", "WARNING", "UNKNOWN", "NOT_RUN"] as ValidationCheckStatus[]).map((st) => {
                  const count = Object.values(report.checks_summary).filter((v) => v === st).length;
                  return (
                    <div key={st} className="bg-white border border-slate-200 rounded-lg p-3 text-center shadow-sm">
                      <div className="text-xl font-bold text-slate-900">{count}</div>
                      <div className="text-[10px] font-semibold uppercase text-slate-500 mt-0.5">{st}</div>
                    </div>
                  );
                })}
              </div>

              {/* Two Column Layout: Detailed Checks vs Literature Evidence */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Left Column: Tool Checks (7 cols) */}
                <div className="lg:col-span-7 space-y-6">
                  <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        <FileCheck className="w-4 h-4 text-emerald-600" />
                        Scientific Validation Tool Results ({report.checks.length})
                      </h3>

                      {/* Category filter pills */}
                      <div className="flex items-center gap-1">
                        {["ALL", "GEOMETRY", "CHEMISTRY", "STABILITY", "TARGET_PROPERTIES"].map((cat) => (
                          <button
                            key={cat}
                            onClick={() => setActiveCategory(cat)}
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider transition ${
                              activeCategory === cat
                                ? "bg-slate-900 text-white"
                                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                            }`}
                          >
                            {cat === "TARGET_PROPERTIES" ? "Props" : cat}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-3">
                      {filteredChecks.map((chk, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-white hover:border-slate-200 transition space-y-1.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-slate-900">{chk.name}</span>
                            {renderStatusBadge(chk.status)}
                          </div>
                          <p className="text-xs text-slate-600">{chk.detail}</p>
                          <div className="flex items-center gap-3 text-[10px] font-mono text-slate-400 pt-1">
                            {chk.actual_value !== undefined && chk.actual_value !== null && (
                              <span>Value: <strong className="text-slate-700">{String(chk.actual_value)} {chk.unit || ""}</strong></span>
                            )}
                            {chk.source_or_method && (
                              <span>Method: {chk.source_or_method}</span>
                            )}
                            <span className="ml-auto uppercase text-slate-500 font-semibold">{chk.category}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Risks & Unknowns */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2.5">
                      <h4 className="text-xs font-bold text-rose-700 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Identified Chemical & Physical Risks
                      </h4>
                      <ul className="text-xs text-slate-700 space-y-2 list-disc list-inside">
                        {report.scientific_risks.map((risk, idx) => (
                          <li key={idx} className="leading-relaxed">{risk}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2.5">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                        <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
                        Missing Calculations & Unknowns
                      </h4>
                      <ul className="text-xs text-slate-700 space-y-2 list-disc list-inside">
                        {report.missing_evidence_and_unknowns.map((miss, idx) => (
                          <li key={idx} className="leading-relaxed">{miss}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Recommended Next Tests */}
                  <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                      <Cpu className="w-4 h-4 text-emerald-600" />
                      Recommended Computational & Experimental Tests
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      <div className="space-y-1.5">
                        <span className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider">
                          Computational (DFT & AIMD)
                        </span>
                        <ul className="space-y-1.5 text-slate-600 list-disc list-inside">
                          {report.recommended_computational_tests.map((t, idx) => (
                            <li key={idx}>{t}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="space-y-1.5">
                        <span className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider">
                          Experimental Synthesis & Testing
                        </span>
                        <ul className="space-y-1.5 text-slate-600 list-disc list-inside">
                          {report.recommended_experimental_tests.map((t, idx) => (
                            <li key={idx}>{t}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Column: Retrieved Evidence & Citations (5 cols) */}
                <div className="lg:col-span-5 space-y-6">
                  {/* Literature Evidence Cards */}
                  <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        <BookOpen className="w-4 h-4 text-indigo-600" />
                        Retrieved Literature Evidence ({report.literature_evidence.length})
                      </h3>
                      <span className="text-[10px] font-mono text-slate-400">HYBRID RETRIEVAL</span>
                    </div>

                    {report.literature_evidence.length > 0 ? (
                      <div className="space-y-4">
                        {report.literature_evidence.map((ev, idx) => (
                          <div
                            key={idx}
                            className="p-3.5 rounded-lg border border-slate-200 bg-white hover:border-slate-300 transition space-y-2 shadow-xs"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <h5 className="text-xs font-bold text-slate-900 leading-snug">{ev.title}</h5>
                                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                  {ev.authors || "Authors not listed"} • {ev.publication_year || "N/A"}
                                </div>
                              </div>
                              <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider shrink-0 ${
                                ev.match_type === "EXACT_FORMULA" 
                                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                                  : "bg-slate-100 text-slate-700"
                              }`}>
                                {ev.match_type.replace("_", " ")}
                              </span>
                            </div>

                            <p className="text-xs text-slate-600 leading-relaxed border-l-2 border-slate-200 pl-2.5 italic">
                              "{ev.passage_text}"
                            </p>

                            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
                              <span>Relevance: <strong>{Math.round(ev.relevance_score * 100)}%</strong></span>
                              {ev.doi_or_url && (
                                <a
                                  href={ev.doi_or_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-emerald-600 hover:text-emerald-700 font-semibold flex items-center gap-1"
                                >
                                  Source Link <ExternalLink className="w-2.5 h-2.5" />
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500 text-center">
                        No direct peer-reviewed literature found matching this formula.
                      </div>
                    )}
                  </div>

                  {/* Comparable Materials */}
                  {report.comparable_materials.length > 0 && (
                    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                        <Database className="w-3.5 h-3.5 text-slate-600" />
                        Comparable Known Materials (MP-20 / Database)
                      </h4>
                      <div className="space-y-2">
                        {report.comparable_materials.map((m, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-lg border border-slate-100 bg-slate-50 text-xs flex items-center justify-between"
                          >
                            <div>
                              <span className="font-mono font-bold text-slate-900">{m.formula}</span>
                              <div className="text-[10px] text-slate-500">
                                {m.reference_source} • {m.similarity_type.replace("_", " ")}
                              </div>
                            </div>
                            <span className="text-[11px] font-mono text-slate-700 font-semibold">
                              {m.reported_stability || "Ehull uncalculated"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Citations List */}
                  {report.citations.length > 0 && (
                    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-slate-600" />
                        Referenced Literature Sources ({report.citations.length})
                      </h4>
                      <ol className="text-xs text-slate-700 space-y-2 list-decimal list-inside">
                        {report.citations.map((c, idx) => (
                          <li key={idx} className="leading-snug">
                            <span className="font-semibold text-slate-900">{c.title}</span>
                            {c.authors && <span className="text-slate-500"> ({c.authors}, {c.year || "N/A"})</span>}
                            {c.url_or_doi && (
                              <a
                                href={c.url_or_doi}
                                target="_blank"
                                rel="noreferrer"
                                className="text-emerald-600 hover:underline ml-1 inline-flex items-center gap-0.5"
                              >
                                [DOI]
                              </a>
                            )}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        /* Knowledge Base Management Tab */
        <div className="space-y-8 animate-fadeIn">
          {/* Connector Status Badges */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-900">Materials Project API</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  connectors?.materials_project?.configured
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-slate-100 text-slate-600"
                }`}>
                  {connectors?.materials_project?.configured ? "CONNECTED" : "NOT CONFIGURED"}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Official DFT materials database. Requires <code className="text-slate-700 font-mono">MP_API_KEY</code> in .env.
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-900">Crystallography Open Database (COD)</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  AVAILABLE
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Open-access experimental crystallographic structures. Zero authentication required.
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-900">Local Reference Catalog</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  139,131 STRUCTURES
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Pre-indexed SQLite catalog of MP-20 and JARVIS-DFT reference crystals. Always offline-accessible.
              </p>
            </div>
          </div>

          {/* Upload New Document Dropzone */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Upload className="w-4 h-4 text-emerald-600" />
              Ingest Scientific Literature (PDF / Plain Text / Markdown)
            </h3>
            <p className="text-xs text-slate-600">
              Upload published research papers or experimental reports. The system automatically chunks the text,
              extracts chemical formulas, and builds vector embeddings for hybrid retrieval.
            </p>

            <form onSubmit={handleFileUpload} className="space-y-4 pt-2">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <input
                  type="text"
                  placeholder="Paper Title (optional, defaults to filename)"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
                <input
                  type="text"
                  placeholder="Authors (e.g. Kamaya et al.)"
                  value={uploadAuthors}
                  onChange={(e) => setUploadAuthors(e.target.value)}
                  className="px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
                <input
                  type="text"
                  placeholder="Publication Year (e.g. 2024)"
                  value={uploadYear}
                  onChange={(e) => setUploadYear(e.target.value)}
                  className="px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <input
                  type="file"
                  accept=".pdf,.txt,.md"
                  onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                  className="text-xs text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100"
                />
                <button
                  type="submit"
                  disabled={!uploadFile || uploading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold disabled:opacity-50 transition flex items-center gap-1.5"
                >
                  {uploading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  <span>{uploading ? "Ingesting..." : "Upload & Index Paper"}</span>
                </button>
              </div>

              {uploadMessage && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700">
                  {uploadMessage}
                </div>
              )}
            </form>
          </div>

          {/* List of Indexed Papers */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-indigo-600" />
              Indexed Scientific Literature ({documents.length} Papers)
            </h3>

            <div className="divide-y divide-slate-100">
              {documents.map((doc, idx) => (
                <div key={idx} className="py-3.5 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <h5 className="text-xs font-bold text-slate-900">{doc.title}</h5>
                    <div className="text-[11px] text-slate-500 font-mono">
                      {doc.authors || "Authors not specified"} • {doc.publication_year || "Year unknown"} • {doc.source_type}
                    </div>
                    {doc.formulas_mentioned && doc.formulas_mentioned.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1">
                        <span className="text-[10px] text-slate-400 font-mono">Formulas:</span>
                        {doc.formulas_mentioned.slice(0, 6).map((f: string) => (
                          <span key={f} className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 font-mono text-[9px]">
                            {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="text-right text-[11px] font-mono text-slate-500 shrink-0">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                      {doc.chunk_count} Chunks
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
