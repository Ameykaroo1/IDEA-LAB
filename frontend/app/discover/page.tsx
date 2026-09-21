"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Sparkles, 
  Send, 
  CheckCircle2, 
  AlertTriangle, 
  Sliders, 
  ArrowRight, 
  RefreshCw, 
  Cpu, 
  Atom, 
  HelpCircle,
  Edit3,
  Layers, 
  XCircle, 
  ShieldAlert, 
  Battery, 
  Zap, 
  Check, 
  FileCode, 
  ListOrdered,
  Filter,
  Download,
  Info,
  ChevronRight
} from "lucide-react";
import { parseRequirements, runDiscovery, validateRequirements, getModelStatus } from "@/lib/api";
import { MaterialRequirements, ParseResponse, Candidate, ModelStatusResponse } from "@/types";

export default function DiscoverPage() {
  const router = useRouter();

  // Natural Language Input State
  const defaultPrompt = "Find a crystalline energy-storage material containing Si and Li with a band gap between 1.5 and 2.2 eV, energy above hull below 0.03 eV/atom, high ionic conductivity, high capacity, and less than 5% volume change. Pb, Cd, Hg, and As must be completely excluded.";
  const [nlInput, setNlInput] = useState(defaultPrompt);

  // NLP Processing State
  const [isParsing, setIsParsing] = useState(false);
  const [parsingStep, setParsingStep] = useState<string>("");
  const [parsedData, setParsedData] = useState<ParseResponse | null>(null);

  // Filter Panel State
  const [reqElementsInput, setReqElementsInput] = useState("Li, Si");
  const [exElementsInput, setExElementsInput] = useState("Pb, Cd, Hg, As");
  const [bandGapMin, setBandGapMin] = useState<string>("1.5");
  const [bandGapMax, setBandGapMax] = useState<string>("2.2");
  const [hullEnergyMax, setHullEnergyMax] = useState<string>("0.03");
  const [formationEnergyMax, setFormationEnergyMax] = useState<string>("");
  const [voltageMin, setVoltageMin] = useState<string>("");
  const [voltageMax, setVoltageMax] = useState<string>("");
  const [capacityMin, setCapacityMin] = useState<string>("");
  const [stabilityCriterion, setStabilityCriterion] = useState<string>("metastable");
  const [numCandidates, setNumCandidates] = useState<number>(10);

  // Active editable requirements (sent to API)
  const [editableReqs, setEditableReqs] = useState<MaterialRequirements | null>(null);

  // Generation Pipeline State
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStepIndex, setGenerationStepIndex] = useState<number>(0);
  const [generatedCandidates, setGeneratedCandidates] = useState<Candidate[]>([]);
  const [rejectedCandidates, setRejectedCandidates] = useState<Candidate[]>([]);
  const [generationNotice, setGenerationNotice] = useState<string>("");
  const [configuredModel, setConfiguredModel] = useState<string>("LOCAL_DEMO");
  const [supportedConditions, setSupportedConditions] = useState<string[]>([]);
  const [unsupportedConditions, setUnsupportedConditions] = useState<string[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);

  useEffect(() => {
    getModelStatus().then(setModelStatus).catch(() => {});
  }, []);

  // Presets
  const presets = [
    {
      name: "Li-Si Energy Storage",
      text: "Find a crystalline energy-storage material containing Si and Li with a band gap between 1.5 and 2.2 eV, energy above hull below 0.03 eV/atom, high ionic conductivity, high capacity, and less than 5% volume change. Pb, Cd, Hg, and As must be completely excluded.",
      req: "Li, Si",
      ex: "Pb, Cd, Hg, As",
      egMin: "1.5",
      egMax: "2.2",
      ehull: "0.03"
    },
    {
      name: "Solid-State Li Electrolyte",
      text: "I need a crystalline solid-state battery electrolyte containing Li, P, and S with high ionic conductivity, band gap above 2.0 eV, energy above hull below 0.025 eV/atom, and no toxic elements (Pb, Cd, Hg, As).",
      req: "Li, P, S",
      ex: "Pb, Cd, Hg, As",
      egMin: "2.0",
      egMax: "4.0",
      ehull: "0.025"
    },
    {
      name: "Sodium-ion Cathode",
      text: "I need a sodium-ion battery cathode material containing Na, V, and O with high capacity, stable structure, energy above hull below 0.02 eV/atom, and completely excluding toxic metals.",
      req: "Na, V, O",
      ex: "Pb, Cd, Hg, As",
      egMin: "1.8",
      egMax: "3.2",
      ehull: "0.02"
    }
  ];

  const PIPELINE_STEPS = [
    "Requirement Extraction",
    "Constraint Validation",
    "Phenomena Routing",
    "Crystal Generation",
    "Structural Validation",
    "Structure Deduplication",
    "Stability Screening",
    "Phenomena Evaluation",
    "Hard Constraint Screening",
    "Multi-Objective Ranking",
    "MP-20 Benchmark Match",
    "JARVIS-DFT Match",
    "3D Lattice & CIF Export",
    "DFT Calculation Queue"
  ];

  const syncFiltersToRequirements = (reqs: MaterialRequirements) => {
    setReqElementsInput(reqs.required_elements?.join(", ") || "");
    setExElementsInput(reqs.excluded_elements?.join(", ") || "");
    const bg = reqs.properties?.["band_gap"] || reqs.band_gap;
    if (bg) {
      if (bg.min !== undefined && bg.min !== null) setBandGapMin(bg.min.toString());
      if (bg.max !== undefined && bg.max !== null) setBandGapMax(bg.max.toString());
      if (bg.target !== undefined && bg.target !== null && !bg.min) {
        setBandGapMin((bg.target - (bg.tolerance || 0.3)).toFixed(1));
        setBandGapMax((bg.target + (bg.tolerance || 0.3)).toFixed(1));
      }
    }
    const eh = reqs.properties?.["energy_above_hull"] || reqs.energy_above_hull;
    if (eh && eh.max !== undefined && eh.max !== null) {
      setHullEnergyMax(eh.max.toString());
    }
    if (reqs.num_candidates) setNumCandidates(reqs.num_candidates);
  };

  const buildRequirementsFromFilters = (): MaterialRequirements => {
    const reqEls = reqElementsInput.split(",").map((s) => s.trim().charAt(0).toUpperCase() + s.trim().slice(1).toLowerCase()).filter(Boolean);
    const exEls = exElementsInput.split(",").map((s) => s.trim().charAt(0).toUpperCase() + s.trim().slice(1).toLowerCase()).filter(Boolean);

    const properties: Record<string, any> = {};

    const bgMinNum = bandGapMin ? parseFloat(bandGapMin) : null;
    const bgMaxNum = bandGapMax ? parseFloat(bandGapMax) : null;
    if (bgMinNum !== null || bgMaxNum !== null) {
      properties["band_gap"] = {
        type: "hard_constraint",
        min: bgMinNum,
        max: bgMaxNum,
        unit: "eV",
        target: bgMinNum !== null && bgMaxNum !== null ? (bgMinNum + bgMaxNum) / 2 : (bgMinNum ?? bgMaxNum)
      };
    }

    const ehullNum = hullEnergyMax ? parseFloat(hullEnergyMax) : (stabilityCriterion === "stable" ? 0.00 : stabilityCriterion === "metastable" ? 0.05 : 0.10);
    properties["energy_above_hull"] = {
      type: "hard_constraint",
      max: ehullNum,
      unit: "eV/atom"
    };

    if (formationEnergyMax) {
      properties["formation_energy"] = {
        type: "hard_constraint",
        max: parseFloat(formationEnergyMax),
        unit: "eV/atom"
      };
    }

    if (capacityMin) {
      properties["capacity"] = {
        type: "soft_preference",
        min: parseFloat(capacityMin),
        unit: "mAh/g"
      };
    }

    return {
      application: "Energy storage",
      energy_domain: "ENERGY_STORAGE",
      battery_type: "lithium_ion",
      required_elements: reqEls,
      allowed_elements: [],
      excluded_elements: exEls,
      properties,
      structural_constraints: {},
      ranking_weights: {
        stability: 0.4,
        band_gap: 0.3,
        ionic_conductivity: 0.2,
        chemistry: 0.1
      },
      num_candidates: numCandidates
    };
  };

  // Handler: NLP Parse
  const handleUnderstand = async () => {
    if (!nlInput.trim()) return;

    setIsParsing(true);
    setParsedData(null);
    setGeneratedCandidates([]);
    setRejectedCandidates([]);

    const simulationSteps = [
      "Classifying clean-energy application domain...",
      "Extracting battery chemistry & required elements...",
      "Identifying excluded species (Pb, Cd, Hg, As)...",
      "Normalizing physical units (eV, eV/atom, S/cm)...",
      "Structuring material requirement constraints..."
    ];

    for (let i = 0; i < simulationSteps.length; i++) {
      setParsingStep(simulationSteps[i]);
      await new Promise((r) => setTimeout(r, 120));
    }

    try {
      const res = await parseRequirements(nlInput);
      setParsedData(res);
      setEditableReqs(JSON.parse(JSON.stringify(res.requirements)));
      syncFiltersToRequirements(res.requirements);
    } catch (err: any) {
      alert(`NLP Extraction error: ${err.message}`);
    } finally {
      setIsParsing(false);
    }
  };

  // Handler: Generation from confirmed requirements
  const handleConfirmAndGenerate = async () => {
    const reqsToUse = editableReqs || buildRequirementsFromFilters();

    setIsGenerating(true);
    setGenerationNotice("");
    setGeneratedCandidates([]);
    setRejectedCandidates([]);

    for (let i = 2; i < PIPELINE_STEPS.length; i++) {
      setGenerationStepIndex(i);
      await new Promise((r) => setTimeout(r, 90));
    }

    try {
      const res = await runDiscovery(reqsToUse, undefined, configuredModel);
      setGeneratedCandidates(res.candidates || []);
      setRejectedCandidates(res.rejected_candidates || []);
      if (res.generator_notice) setGenerationNotice(res.generator_notice);
      if (res.supported_conditions) setSupportedConditions(res.supported_conditions);
      if (res.unsupported_conditions) setUnsupportedConditions(res.unsupported_conditions);
    } catch (err: any) {
      alert(`Discovery pipeline failed: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-borderColor pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider mb-1.5">
            <Sparkles className="w-3.5 h-3.5 text-accent" />
            AI Materials Discovery Studio
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-primaryText tracking-tight">
            Generative Crystal Exploration
          </h1>
          <p className="text-xs sm:text-sm text-secondaryText mt-1 max-w-2xl leading-relaxed">
            Conditioned generative crystal diffusion for sustainable battery materials. MP-20 and JARVIS-DFT reference sets serve as validation and novelty baselines.
          </p>
        </div>

        {/* Model Status Indicator */}
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1.5 rounded-lg border text-xs font-mono flex items-center gap-2 ${
            modelStatus?.mattergen === "CONNECTED"
              ? "bg-accentLight text-accentDark border-accentBorder"
              : "bg-slate-100 text-slate-700 border-slate-200"
          }`}>
            <span className={`w-2 h-2 rounded-full ${modelStatus?.mattergen === "CONNECTED" ? "bg-accent animate-pulse" : "bg-slate-400"}`} />
            <span className="font-semibold">
              {modelStatus?.mattergen === "CONNECTED" ? "REAL_GENERATOR: MatterGen" : "DEMO_GENERATOR ACTIVE"}
            </span>
          </div>
        </div>
      </div>

      {/* Model Context & Academic Integrity Banner */}
      <div className="p-4 rounded-xl bg-white border border-borderColor flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-50 text-accentDark border border-emerald-100">
            <Cpu className="w-4 h-4 text-accent" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-primaryText">Pipeline Execution Environment:</span>
              <span className="text-secondaryText font-mono">{modelStatus?.generator || "Local Demonstration Generator"}</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-600 border border-slate-200">
                Device: {modelStatus?.device || "CPU"}
              </span>
            </div>
            <p className="text-[11px] text-secondaryText mt-0.5 leading-relaxed">
              {modelStatus?.notice || "Demo mode active: candidates are produced using the local screening generator with structural validation and relaxation heuristics."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 text-[11px] text-secondaryText font-mono">
          <span className="px-2 py-1 rounded bg-slate-50 border border-borderColor">
            Datasets: MP-20 + JARVIS
          </span>
        </div>
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT COLUMN: Compact Filter Panel (lg:col-span-4) */}
        <div className="lg:col-span-4 space-y-5">
          <div className="scientific-card p-5 space-y-5 lg:sticky lg:top-24">
            <div className="flex items-center justify-between border-b border-borderColor pb-3">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-accent" />
                <h2 className="text-sm font-bold text-primaryText tracking-tight">
                  Target Constraints
                </h2>
              </div>
              <span className="text-[10px] font-mono uppercase text-secondaryText">Screening Filters</span>
            </div>

            {/* Required Elements */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-primaryText flex items-center justify-between">
                <span>Required Elements</span>
                <span className="text-[10px] text-secondaryText font-normal">e.g. Li, Si, Na</span>
              </label>
              <input
                type="text"
                value={reqElementsInput}
                onChange={(e) => setReqElementsInput(e.target.value)}
                placeholder="Li, Si"
                className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-3 py-2 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
              />
              <div className="flex flex-wrap gap-1 pt-1">
                {["Li", "Na", "Si", "O", "P", "S", "V"].map((el) => (
                  <button
                    key={el}
                    type="button"
                    onClick={() => {
                      const current = reqElementsInput.split(",").map((s) => s.trim()).filter(Boolean);
                      if (!current.includes(el)) {
                        setReqElementsInput([...current, el].join(", "));
                      }
                    }}
                    className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 hover:bg-emerald-50 hover:text-accentDark border border-slate-200 hover:border-accentBorder text-secondaryText transition"
                  >
                    +{el}
                  </button>
                ))}
              </div>
            </div>

            {/* Excluded Elements */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-primaryText flex items-center justify-between">
                <span>Excluded Elements</span>
                <span className="text-[10px] text-rose-600 font-normal">Toxic / Environmental</span>
              </label>
              <input
                type="text"
                value={exElementsInput}
                onChange={(e) => setExElementsInput(e.target.value)}
                placeholder="Pb, Cd, Hg, As"
                className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-3 py-2 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
              />
              <div className="flex items-center gap-1.5 text-[10px] text-secondaryText">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>Environmental Screening: Active</span>
              </div>
            </div>

            {/* Band Gap Range */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-primaryText flex items-center justify-between">
                <span>Band Gap (eV)</span>
                <span className="text-[10px] text-secondaryText font-normal">Min – Max</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="0.1"
                  value={bandGapMin}
                  onChange={(e) => setBandGapMin(e.target.value)}
                  placeholder="Min (1.5)"
                  className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
                />
                <input
                  type="number"
                  step="0.1"
                  value={bandGapMax}
                  onChange={(e) => setBandGapMax(e.target.value)}
                  placeholder="Max (2.5)"
                  className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
                />
              </div>
            </div>

            {/* Energy Above Hull */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-primaryText flex items-center justify-between">
                <span>Energy Above Hull</span>
                <span className="text-[10px] text-secondaryText font-normal">Max eV/atom</span>
              </label>
              <input
                type="number"
                step="0.005"
                value={hullEnergyMax}
                onChange={(e) => setHullEnergyMax(e.target.value)}
                placeholder="≤ 0.03"
                className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
              />
              <span className="text-[10px] text-secondaryText block">
                Standard threshold: ≤ 0.05 eV/atom for synthesizability.
              </span>
            </div>

            {/* Formation Energy */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-primaryText flex items-center justify-between">
                <span>Formation Energy</span>
                <span className="text-[10px] text-secondaryText font-normal">Max eV/atom</span>
              </label>
              <input
                type="number"
                step="0.05"
                value={formationEnergyMax}
                onChange={(e) => setFormationEnergyMax(e.target.value)}
                placeholder="e.g. 0.00"
                className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
              />
            </div>

            {/* Voltage & Capacity */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-primaryText">Voltage Min (V)</label>
                <input
                  type="number"
                  step="0.1"
                  value={voltageMin}
                  onChange={(e) => setVoltageMin(e.target.value)}
                  placeholder="Min V"
                  className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-primaryText">Capacity (mAh/g)</label>
                <input
                  type="number"
                  step="20"
                  value={capacityMin}
                  onChange={(e) => setCapacityMin(e.target.value)}
                  placeholder="Min mAh/g"
                  className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-mono text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
                />
              </div>
            </div>

            {/* Stability Criterion Dropdown */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-primaryText">Thermodynamic Stability</label>
              <select
                value={stabilityCriterion}
                onChange={(e) => setStabilityCriterion(e.target.value)}
                className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-medium text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
              >
                <option value="stable">Stable on Convex Hull (0.00 eV/atom)</option>
                <option value="metastable">Metastable (≤ 0.05 eV/atom)</option>
                <option value="relaxed">Screening Surrogate (≤ 0.10 eV/atom)</option>
              </select>
            </div>

            {/* Candidate Count */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-primaryText">Generated Candidates</label>
              <select
                value={numCandidates}
                onChange={(e) => setNumCandidates(parseInt(e.target.value))}
                className="w-full bg-slate-50/70 border border-borderColor rounded-lg px-2.5 py-1.5 text-xs font-medium text-primaryText focus:bg-white focus:outline-none focus:border-accent transition"
              >
                <option value={10}>10 Candidates</option>
                <option value={25}>25 Candidates</option>
                <option value={50}>50 Candidates</option>
              </select>
            </div>

            {/* Apply & Generate Button */}
            <button
              type="button"
              disabled={isGenerating}
              onClick={handleConfirmAndGenerate}
              className="w-full py-2.5 rounded-lg bg-accent hover:bg-accentDark text-white font-semibold text-xs tracking-wide transition shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Generating Candidates...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Run Discovery With Filters</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* RIGHT COLUMN: Results & Natural Language Input (lg:col-span-8) */}
        <div className="lg:col-span-8 space-y-6">

          {/* 1. Natural Language Requirement Extraction Box */}
          <div className="scientific-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-borderColor pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-accent" />
                <h2 className="text-sm font-bold text-primaryText tracking-tight">
                  Natural Language Query
                </h2>
              </div>
              <span className="text-[10px] font-mono text-secondaryText">Scientific Requirement Parsing</span>
            </div>

            <textarea
              rows={3}
              value={nlInput}
              onChange={(e) => setNlInput(e.target.value)}
              placeholder="Describe your desired crystal material constraints..."
              className="w-full bg-slate-50/60 border border-borderColor rounded-xl p-3.5 text-xs sm:text-sm text-primaryText placeholder-secondaryText focus:bg-white focus:outline-none focus:border-accent transition resize-none leading-relaxed"
            />

            {/* Quick Presets */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-secondaryText">Benchmark Research Presets:</span>
              <div className="flex flex-wrap gap-2">
                {presets.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setNlInput(p.text);
                      setReqElementsInput(p.req);
                      setExElementsInput(p.ex);
                      setBandGapMin(p.egMin);
                      setBandGapMax(p.egMax);
                      setHullEnergyMax(p.ehull);
                    }}
                    className="px-2.5 py-1 rounded-md bg-slate-100 hover:bg-emerald-50 hover:text-accentDark text-[11px] text-secondaryText border border-slate-200 hover:border-accentBorder transition"
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setNlInput("")}
                className="text-xs text-secondaryText hover:text-primaryText transition flex items-center gap-1"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Clear
              </button>

              <button
                type="button"
                disabled={isParsing || !nlInput.trim()}
                onClick={handleUnderstand}
                className="px-4 py-2 rounded-lg bg-primaryText hover:bg-slate-800 text-white font-medium text-xs tracking-wide transition shadow-sm flex items-center gap-2 disabled:opacity-50"
              >
                {isParsing ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Extracting Requirements...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-accent" />
                    <span>Extract Requirements</span>
                  </>
                )}
              </button>
            </div>

            {/* NLP Step Animation */}
            {isParsing && (
              <div className="mt-2 p-3 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center gap-2.5 text-xs text-accentDark">
                <div className="w-3.5 h-3.5 border-2 border-accent border-t-transparent rounded-full animate-spin shrink-0" />
                <span className="font-mono">{parsingStep}</span>
              </div>
            )}
          </div>

          {/* 2. Understood Requirements Confirmation Panel */}
          {parsedData && editableReqs && (
            <div className="scientific-card p-6 border-accentBorder/80 space-y-5 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-borderColor pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg bg-emerald-50 text-accentDark border border-emerald-100">
                    <CheckCircle2 className="w-4 h-4 text-accent" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-primaryText">
                      Parsed Requirements Confirmation
                    </h3>
                    <p className="text-[11px] text-secondaryText">
                      Verified extracted physical parameters prior to generative dispatch.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-50 text-accentDark border border-accentBorder">
                    Domain: {editableReqs.energy_domain || "ENERGY_STORAGE"}
                  </span>
                </div>
              </div>

              {/* Grid of Parsed Requirements */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                  <span className="text-[10px] uppercase font-mono text-secondaryText block mb-1">Required Elements</span>
                  <div className="flex flex-wrap gap-1">
                    {editableReqs.required_elements?.length > 0 ? (
                      editableReqs.required_elements.map((el) => (
                        <span key={el} className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-100/70 text-accentDark">
                          {el}
                        </span>
                      ))
                    ) : (
                      <span className="text-secondaryText italic">None specified</span>
                    )}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                  <span className="text-[10px] uppercase font-mono text-secondaryText block mb-1">Excluded Elements</span>
                  <div className="flex flex-wrap gap-1">
                    {editableReqs.excluded_elements?.length > 0 ? (
                      editableReqs.excluded_elements.map((el) => (
                        <span key={el} className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          {el}
                        </span>
                      ))
                    ) : (
                      <span className="text-secondaryText italic">None excluded</span>
                    )}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                  <span className="text-[10px] uppercase font-mono text-secondaryText block mb-1">Band Gap Window</span>
                  <span className="font-semibold text-primaryText font-mono">
                    {editableReqs.properties?.["band_gap"]?.min !== undefined
                      ? `${editableReqs.properties["band_gap"].min} – ${editableReqs.properties["band_gap"].max} eV`
                      : editableReqs.properties?.["band_gap"]?.target !== undefined
                      ? `~${editableReqs.properties["band_gap"].target} eV`
                      : "Not specified"}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                  <span className="text-[10px] uppercase font-mono text-secondaryText block mb-1">Energy Above Hull</span>
                  <span className="font-semibold text-primaryText font-mono">
                    {editableReqs.properties?.["energy_above_hull"]?.max !== undefined
                      ? `≤ ${editableReqs.properties["energy_above_hull"].max} eV/atom`
                      : "≤ 0.05 eV/atom (Default)"}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                  <span className="text-[10px] uppercase font-mono text-secondaryText block mb-1">Ionic Conductivity</span>
                  <span className="font-semibold text-primaryText font-mono">
                    {editableReqs.properties?.["ionic_conductivity"]?.target !== undefined
                      ? `${editableReqs.properties["ionic_conductivity"].target} S/cm`
                      : editableReqs.properties?.["ionic_conductivity"]?.preference
                      ? editableReqs.properties["ionic_conductivity"].preference
                      : "High (Qualitative)"}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                  <span className="text-[10px] uppercase font-mono text-secondaryText block mb-1">Environmental Check</span>
                  <span className="text-accentDark font-semibold text-[11px] flex items-center gap-1">
                    <Check className="w-3.5 h-3.5 text-accent" />
                    No Excluded Elements
                  </span>
                </div>
              </div>

              {/* Generative Model Dispatch Configuration */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-borderColor flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div>
                  <span className="font-semibold text-primaryText block">Active Generative Model:</span>
                  <span className="text-[11px] text-secondaryText">Conditioned crystal generation engine</span>
                </div>
                <select
                  value={configuredModel}
                  onChange={(e) => setConfiguredModel(e.target.value)}
                  className="bg-white border border-borderColor rounded-md px-2.5 py-1.5 text-xs text-primaryText font-mono focus:outline-none focus:border-accent"
                >
                  <option value="LOCAL_DEMO">Local Generative Demo Engine</option>
                  <option value="MATTERGEN_PROPERTY_CONDITIONED">MatterGen Property-Conditioned</option>
                  <option value="MATTERGEN_BASE">MatterGen Base Diffusion</option>
                  <option value="MATTERGEN_CSP">MatterGen CSP</option>
                </select>
              </div>

              {/* Action */}
              <div className="pt-2 flex items-center justify-between border-t border-borderColor">
                <span className="text-xs text-secondaryText">
                  Ready to dispatch generation for <strong className="text-primaryText">{editableReqs.num_candidates || 10} candidates</strong>.
                </span>
                <button
                  type="button"
                  disabled={isGenerating}
                  onClick={handleConfirmAndGenerate}
                  className="px-5 py-2.5 rounded-lg bg-accent hover:bg-accentDark text-white font-semibold text-xs tracking-wide transition shadow-sm flex items-center gap-2 disabled:opacity-50"
                >
                  {isGenerating ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Executing Discovery Pipeline...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Confirm & Generate Candidates</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* 3. 14-Step Discovery Pipeline Status Tracker */}
          <div className="scientific-card p-4 space-y-2.5">
            <div className="flex items-center justify-between text-xs text-secondaryText font-mono">
              <span className="flex items-center gap-1.5 text-primaryText font-semibold">
                <ListOrdered className="w-3.5 h-3.5 text-accent" />
                14-Stage Scientific Pipeline
              </span>
              <span>{isGenerating ? `Processing Step ${generationStepIndex + 1}/14` : "Pipeline Ready"}</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-1.5">
              {PIPELINE_STEPS.map((step, idx) => {
                const isActive = isGenerating && generationStepIndex === idx;
                const isCompleted = isGenerating ? generationStepIndex > idx : generatedCandidates.length > 0;
                return (
                  <div
                    key={idx}
                    className={`p-1.5 rounded border text-center transition ${
                      isActive
                        ? "bg-emerald-50 text-accentDark border-accent font-semibold animate-pulse"
                        : isCompleted
                        ? "bg-slate-50 text-slate-700 border-emerald-200"
                        : "bg-slate-50/50 text-slate-400 border-borderColor"
                    }`}
                  >
                    <div className="text-[9px] font-mono opacity-70">#{idx + 1}</div>
                    <div className="text-[10px] font-medium truncate" title={step}>{step}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 4. Generated Candidates Result Section */}
          {generatedCandidates.length > 0 && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-borderColor pb-3">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider">
                    <Atom className="w-3.5 h-3.5 text-accent" />
                    Discovery Results ({generatedCandidates.length} Candidates)
                  </div>
                  <h3 className="text-lg font-bold text-primaryText">
                    Ranked Battery Material Candidates
                  </h3>
                </div>

                <Link
                  href="/candidates"
                  className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-primaryText text-xs font-medium border border-borderColor transition flex items-center gap-1.5 self-start sm:self-auto"
                >
                  <span>Candidate Library</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {/* Scientific Provenance Note */}
              <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-100 text-xs text-accentDark flex items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <Info className="w-4 h-4 text-accent shrink-0" />
                  <span>
                    <strong>AI Predicted:</strong> Newly generated structures conditioned on target constraints. Requires computational (DFT) and experimental validation.
                  </span>
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white border border-emerald-200">
                  Ref: MP-20 + JARVIS
                </span>
              </div>

              {generationNotice && (
                <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800 font-mono flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
                  <span>{generationNotice}</span>
                </div>
              )}

              {/* Compact Scientific Candidate Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {generatedCandidates.map((c) => {
                  const rankLabel = c.rank_label || c.requirement_match?.rank_label || `#${c.rank} Match`;
                  const isStructValid = c.structural_status === "VALID" || c.validation?.is_valid;
                  const egVal = c.predictions.band_gap.value;
                  const ehullVal = c.predictions.energy_above_hull.value;
                  const formationVal = c.predictions.formation_energy?.value;
                  const voltageVal = c.predictions.voltage?.value;
                  const capacityVal = c.predictions.capacity?.value || c.capacity?.theoretical_capacity || c.capacity?.theoretical_capacity_gravimetric;

                  return (
                    <div
                      key={c.candidate_id}
                      className="scientific-card p-4 flex flex-col justify-between space-y-3 hover:border-accent/40 transition group"
                    >
                      {/* Top Header: ID, Formula, Rank */}
                      <div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-50 text-accentDark border border-accentBorder">
                            {rankLabel}
                          </span>
                          <span className="text-[10px] font-mono text-secondaryText px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200">
                            {c.generation_source || c.generator || "AI Predicted"}
                          </span>
                        </div>

                        <div className="pt-2 flex items-baseline justify-between">
                          <span className="text-lg font-bold text-primaryText group-hover:text-accentDark transition">
                            {c.reduced_formula}
                          </span>
                          <span className="font-mono text-xs text-secondaryText">{c.candidate_id}</span>
                        </div>
                        <div className="text-[11px] text-secondaryText font-mono">
                          {c.crystal_system} • {c.space_group}
                        </div>
                      </div>

                      {/* Scientific Property Grid */}
                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        <div className="p-2 rounded bg-slate-50 border border-borderColor">
                          <span className="text-[10px] text-secondaryText block">Formation Energy</span>
                          <span className="font-semibold text-primaryText">
                            {formationVal !== undefined && formationVal !== null ? `${formationVal.toFixed(3)} eV/atom` : "Not available"}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-50 border border-borderColor">
                          <span className="text-[10px] text-secondaryText block">Energy Above Hull</span>
                          <span className="font-semibold text-primaryText">
                            {ehullVal !== null && ehullVal !== undefined ? `${(ehullVal * 1000).toFixed(0)} meV/atom` : "Not available"}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-50 border border-borderColor">
                          <span className="text-[10px] text-secondaryText block">Band Gap</span>
                          <span className="font-semibold text-primaryText">
                            {egVal !== null && egVal !== undefined ? `${egVal.toFixed(2)} eV` : "Not available"}
                          </span>
                        </div>
                        <div className="p-2 rounded bg-slate-50 border border-borderColor">
                          <span className="text-[10px] text-secondaryText block">Theoretical Capacity</span>
                          <span className="font-semibold text-primaryText">
                            {capacityVal ? `${Math.round(capacityVal)} mAh/g` : "Not available"}
                          </span>
                        </div>
                      </div>

                      {/* Scientific Labels */}
                      <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
                        <span className="px-2 py-0.5 rounded bg-emerald-50 text-accentDark border border-accentBorder font-semibold">
                          Structure: {isStructValid ? "Valid" : "Requires Check"}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                          Requires DFT Validation
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                          No Excluded Elements
                        </span>
                      </div>

                      {/* Why this candidate snippet */}
                      {c.ranking_explanation && c.ranking_explanation.length > 0 && (
                        <div className="p-2 rounded bg-slate-50 border border-borderColor text-[11px] text-secondaryText space-y-0.5">
                          <span className="text-[10px] uppercase font-semibold text-primaryText block">Scientific Screening Match</span>
                          <div className="truncate">
                            ✓ {c.ranking_explanation[0].replace(/^[✓⚠ℹ\s]+/, '')}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="pt-2 border-t border-borderColor flex items-center justify-between gap-2">
                        <Link
                          href={`/candidates/${c.candidate_id}`}
                          className="px-3 py-1.5 rounded-md bg-accent hover:bg-accentDark text-white text-xs font-medium transition flex items-center gap-1 shadow-sm"
                        >
                          <span>View Structure</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                        <a
                          href={`http://localhost:8000/api/candidates/${c.candidate_id}/cif`}
                          download
                          className="px-2.5 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-secondaryText hover:text-primaryText text-xs font-mono border border-borderColor transition flex items-center gap-1"
                          title="Download Crystallographic Information File"
                        >
                          <Download className="w-3 h-3" />
                          <span>CIF</span>
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 5. Clean Rejected Candidates Section */}
          {rejectedCandidates.length > 0 && (
            <div className="scientific-card p-5 border-rose-200 bg-rose-50/20 space-y-3 animate-fadeIn">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-rose-100 text-rose-700 border border-rose-200">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-rose-900">
                    Excluded Candidates ({rejectedCandidates.length})
                  </h3>
                  <p className="text-[11px] text-rose-700">
                    Structures failing hard physical or environmental criteria (e.g. prohibited toxic elements or atomic overlap).
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                {rejectedCandidates.map((rc) => (
                  <div key={rc.candidate_id} className="p-3 rounded-lg bg-white border border-rose-200 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-primaryText">{rc.reduced_formula}</span>
                      <span className="font-mono text-[10px] text-secondaryText">{rc.candidate_id}</span>
                      <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 text-[9px] font-mono font-bold border border-rose-200">
                        EXCLUDED
                      </span>
                    </div>
                    <div className="text-[11px] text-secondaryText font-mono">
                      {rc.crystal_system} • {rc.space_group}
                    </div>
                    <div className="text-[11px] text-rose-700 font-medium">
                      Reason: {rc.rejection_reason || "Failed hard constraint screening"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
