"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Atom, 
  Download, 
  Sliders, 
  Cpu, 
  CheckCircle2, 
  XCircle, 
  Eye, 
  Layers, 
  Filter,
  Check,
  Search,
  FileSpreadsheet,
  ArrowUpDown,
  ShieldCheck
} from "lucide-react";
import { getCandidates, reRankCandidates, addToDftQueue, removeFromDftQueue } from "@/lib/api";
import { Candidate, RankingWeights } from "@/types";
import RankingWeightsModal from "@/components/RankingWeightsModal";
import ValidationReportModal from "@/components/ValidationReportModal";

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [filteredCandidates, setFilteredCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter state
  const [filterType, setFilterType] = useState<"all" | "valid" | "screening" | "dft">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Selected for export
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Modals state
  const [isWeightsModalOpen, setIsWeightsModalOpen] = useState(false);
  const [selectedCandidateForReport, setSelectedCandidateForReport] = useState<Candidate | null>(null);

  // Active ranking weights
  const [currentWeights, setCurrentWeights] = useState<RankingWeights>({
    stability: 0.4,
    band_gap: 0.3,
    ionic_conductivity: 0.2,
    chemistry: 0.1,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getCandidates();
      setCandidates(data);
    } catch (err) {
      console.error("Failed to load candidates:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filter logic
  useEffect(() => {
    let result = [...candidates];

    if (filterType === "valid") {
      result = result.filter((c) => c.validation?.is_valid || c.structural_status === "VALID");
    } else if (filterType === "screening") {
      result = result.filter((c) => c.screening?.passed || c.requirement_compliance === "MATCH");
    } else if (filterType === "dft") {
      result = result.filter((c) => c.in_dft_queue);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.candidate_id.toLowerCase().includes(q) ||
          c.reduced_formula.toLowerCase().includes(q) ||
          c.elements.some((el) => el.toLowerCase().includes(q))
      );
    }

    setFilteredCandidates(result);
  }, [candidates, filterType, searchQuery]);

  // Handle weight apply
  const handleApplyWeights = async (newWeights: RankingWeights) => {
    setCurrentWeights(newWeights);
    try {
      const updated = await reRankCandidates(newWeights);
      setCandidates(updated);
    } catch (err) {
      alert("Failed to recalculate rankings");
    }
  };

  // Toggle selection
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Toggle DFT Queue
  const toggleDft = async (c: Candidate) => {
    try {
      if (c.in_dft_queue) {
        await removeFromDftQueue(c.candidate_id);
      } else {
        await addToDftQueue(c.candidate_id, "Candidate queued from Library Table");
      }
      setCandidates((prev) =>
        prev.map((item) =>
          item.candidate_id === c.candidate_id ? { ...item, in_dft_queue: !item.in_dft_queue } : item
        )
      );
    } catch (err) {
      alert("Failed to update DFT queue");
    }
  };

  // Batch CIF download
  const handleBatchExport = (mode: "selected" | "top5" | "all_valid") => {
    const params = new URLSearchParams();
    params.set("mode", mode);
    if (mode === "selected" && selectedIds.length > 0) {
      selectedIds.forEach((id) => params.append("candidate_ids", id));
    }
    window.open(`http://localhost:8000/api/export-cifs?${params.toString()}`, "_blank");
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-borderColor pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider mb-1">
            <Atom className="w-4 h-4 text-accent" /> Materials Library
          </div>
          <h1 className="text-2xl font-bold text-primaryText tracking-tight">
            Screening & Ranking Library
          </h1>
          <p className="text-xs text-secondaryText mt-0.5">
            Evaluate, compare, filter, and inspect AI-generated crystal candidates.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Weights Adjustment Button */}
          <button
            onClick={() => setIsWeightsModalOpen(true)}
            className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-secondaryText hover:text-primaryText border border-borderColor text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
          >
            <Sliders className="w-3.5 h-3.5 text-accent" />
            <span>Ranking Weights</span>
          </button>

          {/* Batch Export */}
          <button
            onClick={() => handleBatchExport("all_valid")}
            className="px-3.5 py-2 rounded-lg bg-accent hover:bg-accentDark text-white text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
            title="Download all valid candidate CIFs in a ZIP"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Valid CIFs</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="scientific-card p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-secondaryText absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by ID, formula, or element..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-50 border border-borderColor text-xs text-primaryText placeholder-secondaryText focus:bg-white focus:outline-none focus:border-accent"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {[
            { id: "all", label: `All Candidates (${candidates.length})` },
            { id: "valid", label: `Valid (${candidates.filter((c) => c.validation?.is_valid || c.structural_status === "VALID").length})` },
            { id: "screening", label: `Passed Screening (${candidates.filter((c) => c.screening?.passed || c.requirement_compliance === "MATCH").length})` },
            { id: "dft", label: `In DFT Queue (${candidates.filter((c) => c.in_dft_queue).length})` },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilterType(f.id as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                filterType === f.id
                  ? "bg-accent text-white shadow-sm font-semibold"
                  : "bg-slate-100 text-secondaryText hover:text-primaryText hover:bg-slate-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Candidate Table */}
      <div className="scientific-card overflow-hidden">
        {loading ? (
          <div className="py-20 text-center text-secondaryText text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span>Loading materials...</span>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div className="py-20 text-center text-secondaryText text-xs">
            <Atom className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p>No candidates match the selected criteria.</p>
            <Link href="/discover" className="mt-2 text-accent hover:underline font-semibold inline-block">
              Generate new candidates
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-secondaryText bg-slate-50 border-b border-borderColor">
                <tr>
                  <th className="py-3 px-3 w-10 text-center">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === filteredCandidates.length && filteredCandidates.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIds(filteredCandidates.map((c) => c.candidate_id));
                        } else {
                          setSelectedIds([]);
                        }
                      }}
                      className="rounded accent-accent"
                    />
                  </th>
                  <th className="py-3 px-3 font-semibold">Rank</th>
                  <th className="py-3 px-3 font-semibold">Candidate ID</th>
                  <th className="py-3 px-3 font-semibold">Formula</th>
                  <th className="py-3 px-3 font-semibold">Space Group</th>
                  <th className="py-3 px-3 font-semibold">Structure</th>
                  <th className="py-3 px-3 font-semibold">Requirement</th>
                  <th className="py-3 px-3 font-semibold">E_hull (eV/at)</th>
                  <th className="py-3 px-3 font-semibold">Band Gap (eV)</th>
                  <th className="py-3 px-3 font-semibold">Score</th>
                  <th className="py-3 px-3 font-semibold">Reference Check</th>
                  <th className="py-3 px-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderColor text-slate-700 bg-white">
                {filteredCandidates.map((c) => {
                  const isStructValid = c.structural_status === "VALID" || c.validation?.is_valid;
                  const isReqMatch = c.requirement_compliance === "MATCH";
                  const rankLabel = c.rank_label || c.requirement_match?.rank_label || `#${c.rank || "-"}`;

                  return (
                    <tr key={c.candidate_id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-3 text-center">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(c.candidate_id)}
                          onChange={() => toggleSelect(c.candidate_id)}
                          className="rounded accent-accent"
                        />
                      </td>
                      <td className="py-3 px-3 font-mono">
                        <span className="font-bold text-accentDark block">#{c.rank || "-"}</span>
                      </td>
                      <td className="py-3 px-3 font-mono font-semibold text-primaryText">
                        <Link href={`/candidates/${c.candidate_id}`} className="hover:text-accentDark hover:underline">
                          {c.candidate_id}
                        </Link>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-bold text-primaryText">{c.reduced_formula}</div>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-secondaryText">
                        {c.space_group}
                      </td>
                      <td className="py-3 px-3">
                        <button
                          onClick={() => setSelectedCandidateForReport(c)}
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold cursor-pointer hover:opacity-80 transition ${
                            isStructValid
                              ? "bg-emerald-50 text-accentDark border border-accentBorder"
                              : "bg-rose-50 text-rose-700 border border-rose-200"
                          }`}
                          title="Click to view crystallographic validation report"
                        >
                          {isStructValid ? "VALID" : "INVALID"}
                        </button>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          isReqMatch
                            ? "bg-emerald-50 text-accentDark border border-accentBorder"
                            : "bg-amber-50 text-amber-800 border border-amber-200"
                        }`}>
                          {c.requirement_compliance || (c.screening?.passed ? "MATCH" : "NON-COMPLIANT")}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-primaryText">
                        {c.predictions?.energy_above_hull?.value !== null && c.predictions?.energy_above_hull?.value !== undefined ? (
                          <span>{c.predictions.energy_above_hull.value.toFixed(3)}</span>
                        ) : (
                          <span className="text-secondaryText text-[11px]">Not available</span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono text-primaryText">
                        {c.predictions?.band_gap?.value !== null && c.predictions?.band_gap?.value !== undefined ? (
                          <span>{c.predictions.band_gap.value.toFixed(2)}</span>
                        ) : (
                          <span className="text-secondaryText text-[11px]">Not available</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-mono font-bold text-accentDark">
                          {c.ranking?.total_score ? `${c.ranking.total_score.toFixed(1)}/100` : "Not available"}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-[10px] font-mono text-secondaryText truncate max-w-[140px] block" title={c.novelty?.result}>
                          {c.novelty?.result || "NO CLOSE MATCH IN MP-20/JARVIS"}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link
                            href="/scientific-validation"
                            className="p-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 transition"
                            title="Run RAG Scientific Validation"
                          >
                            <ShieldCheck className="w-3.5 h-3.5" />
                          </Link>
                          <Link
                            href={`/candidates/${c.candidate_id}`}
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-secondaryText hover:text-primaryText transition"
                            title="Inspect 3D Lattice and Full Properties"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </Link>
                          <a
                            href={`http://localhost:8000/api/candidates/${c.candidate_id}/cif`}
                            download
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-secondaryText hover:text-primaryText transition"
                            title="Download CIF"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </a>
                          <button
                            onClick={() => toggleDft(c)}
                            className={`p-1.5 rounded-lg transition ${
                              c.in_dft_queue
                                ? "bg-amber-100 text-amber-800 border border-amber-300"
                                : "bg-slate-100 text-secondaryText hover:text-primaryText"
                            }`}
                            title={c.in_dft_queue ? "In DFT Queue (Click to remove)" : "Send to DFT Queue"}
                          >
                            <Cpu className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      <RankingWeightsModal
        isOpen={isWeightsModalOpen}
        onClose={() => setIsWeightsModalOpen(false)}
        currentWeights={currentWeights}
        onApply={handleApplyWeights}
      />

      {selectedCandidateForReport && (
        <ValidationReportModal
          isOpen={true}
          onClose={() => setSelectedCandidateForReport(null)}
          candidateId={selectedCandidateForReport.candidate_id}
          formula={selectedCandidateForReport.reduced_formula}
          validation={selectedCandidateForReport.validation}
        />
      )}
    </div>
  );
}
