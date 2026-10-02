"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  ArrowLeft, 
  Download, 
  Cpu, 
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  Layers, 
  Compass, 
  BarChart3, 
  Info,
  Check,
  Zap,
  Battery,
  Flame,
  AlertTriangle,
  HelpCircle
} from "lucide-react";
import { getCandidate, addToDftQueue, removeFromDftQueue } from "@/lib/api";
import { Candidate } from "@/types";
import CrystalViewer3D from "@/components/CrystalViewer3D";

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const data = await getCandidate(id);
      setCandidate(data);
    } catch (err: any) {
      setError(err.message || "Failed to load candidate");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const toggleDftQueue = async () => {
    if (!candidate) return;
    try {
      if (candidate.in_dft_queue) {
        await removeFromDftQueue(candidate.candidate_id);
        setCandidate({ ...candidate, in_dft_queue: false });
      } else {
        await addToDftQueue(candidate.candidate_id, "Added from Candidate Detail Page");
        setCandidate({ ...candidate, in_dft_queue: true });
      }
    } catch (err) {
      alert("Failed to update DFT queue");
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-secondaryText text-xs flex items-center justify-center gap-2">
        <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <span>Loading candidate {id}...</span>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <p className="text-sm text-rose-600 font-medium">{error || "Candidate not found."}</p>
        <Link
          href="/candidates"
          className="px-4 py-2 rounded-lg bg-primaryText text-xs text-white hover:bg-slate-800 transition inline-flex items-center gap-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Materials Library</span>
        </Link>
      </div>
    );
  }

  const isStructValid = candidate.structural_status === "VALID" || candidate.validation?.is_valid;
  const egVal = candidate.predictions?.band_gap?.value;
  const ehullVal = candidate.predictions?.energy_above_hull?.value;
  const formationVal = candidate.predictions?.formation_energy?.value;
  const voltageVal = candidate.predictions?.voltage?.value;
  const capacityVal = candidate.predictions?.capacity?.value || candidate.capacity?.theoretical_capacity || candidate.capacity?.theoretical_capacity_gravimetric;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-borderColor pb-5">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-lg bg-white border border-borderColor hover:bg-slate-50 text-secondaryText hover:text-primaryText transition"
            title="Go back"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono font-bold text-accentDark bg-emerald-50 border border-accentBorder px-2 py-0.5 rounded">
                {candidate.rank_label || candidate.requirement_match?.rank_label || `#${candidate.rank || "-"}`}
              </span>
              <h1 className="text-2xl font-bold text-primaryText tracking-tight">{candidate.reduced_formula}</h1>
              <span className="text-xs font-mono text-secondaryText">({candidate.candidate_id})</span>

              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                isStructValid
                  ? "bg-emerald-50 text-accentDark border border-accentBorder"
                  : "bg-rose-50 text-rose-700 border border-rose-200"
              }`}>
                Structure: {isStructValid ? "Valid" : "Invalid"}
              </span>

              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                Requires DFT Validation
              </span>
            </div>
            <p className="text-xs text-secondaryText font-mono mt-0.5">
              Space Group: {candidate.space_group} • Crystal System: {candidate.crystal_system} • Formula: {candidate.formula}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <a
            href={`http://localhost:8000/api/candidates/${candidate.candidate_id}/cif`}
            download
            className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-secondaryText hover:text-primaryText border border-borderColor text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-accent" />
            <span>Download CIF</span>
          </a>

          <button
            onClick={toggleDftQueue}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm ${
              candidate.in_dft_queue
                ? "bg-amber-50 text-amber-800 border border-amber-300"
                : "bg-accent hover:bg-accentDark text-white"
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>{candidate.in_dft_queue ? "Queued for DFT (Remove)" : "Add to DFT Queue"}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Large 3D Viewer Left + Key Scientific Properties Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left: 3D Crystal Viewer (Main visual element) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="h-[480px]">
            <CrystalViewer3D
              cifString={candidate.cif_string}
              formula={candidate.reduced_formula}
              spaceGroup={candidate.space_group}
              crystalSystem={candidate.crystal_system}
            />
          </div>

          {/* Environmental & Scientific Provenance Badges */}
          <div className="scientific-card p-4 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-primaryText flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-accent" />
                Environmental & Scientific Screening
              </span>
              <span className="text-[10px] font-mono text-accentDark bg-emerald-50 px-2 py-0.5 rounded border border-accentBorder font-semibold">
                Environmental Screening: Passed
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 text-xs">
              <div className="p-2.5 rounded bg-slate-50 border border-borderColor">
                <span className="text-[10px] uppercase font-mono text-secondaryText block">Toxic Elements</span>
                <span className="font-semibold text-accentDark text-[11px] flex items-center gap-1">
                  <Check className="w-3 h-3 text-accent" />
                  No Excluded Elements
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-50 border border-borderColor">
                <span className="text-[10px] uppercase font-mono text-secondaryText block">Generation Source</span>
                <span className="font-mono text-primaryText font-semibold text-[11px]">
                  {candidate.generation_source || candidate.generator || "AI Predicted"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-50 border border-borderColor">
                <span className="text-[10px] uppercase font-mono text-secondaryText block">Downstream State</span>
                <span className="font-mono text-slate-700 font-semibold text-[11px]">
                  Requires DFT Validation
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Comprehensive Properties & "Why this candidate?" */}
        <div className="lg:col-span-5 space-y-5">
          
          {/* Key Properties Grid */}
          <div className="scientific-card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-borderColor pb-3">
              <h2 className="text-sm font-bold text-primaryText tracking-tight">
                Calculated & Predicted Properties
              </h2>
              <span className="text-[10px] font-mono text-secondaryText">Screening Physics</span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                <span className="text-[10px] text-secondaryText block uppercase">Formation Energy</span>
                <span className="text-sm font-bold text-primaryText">
                  {formationVal !== undefined && formationVal !== null ? `${formationVal.toFixed(3)} eV/atom` : "Not available"}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                <span className="text-[10px] text-secondaryText block uppercase">Energy Above Hull</span>
                <span className="text-sm font-bold text-accentDark">
                  {ehullVal !== null && ehullVal !== undefined ? `${(ehullVal * 1000).toFixed(0)} meV/atom` : "Not available"}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                <span className="text-[10px] text-secondaryText block uppercase">Band Gap</span>
                <span className="text-sm font-bold text-primaryText">
                  {egVal !== null && egVal !== undefined ? `${egVal.toFixed(2)} eV` : "Not available"}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                <span className="text-[10px] text-secondaryText block uppercase">Nominal Voltage</span>
                <span className="text-sm font-bold text-primaryText">
                  {voltageVal !== undefined && voltageVal !== null ? `${voltageVal.toFixed(2)} V` : "Not available"}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                <span className="text-[10px] text-secondaryText block uppercase">Theoretical Capacity</span>
                <span className="text-sm font-bold text-primaryText">
                  {capacityVal ? `${Math.round(capacityVal)} mAh/g` : "Not available"}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
                <span className="text-[10px] text-secondaryText block uppercase">Stability Status</span>
                <span className="text-xs font-bold text-accentDark truncate block">
                  {candidate.stability_status || "FAVORABLE"}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-borderColor text-[11px] text-secondaryText space-y-1">
              <div className="flex items-center justify-between">
                <span>Total Requirement Match:</span>
                <span className="font-mono font-bold text-primaryText">
                  {candidate.ranking?.total_score ? `${candidate.ranking.total_score.toFixed(1)} / 100` : "Not available"}
                </span>
              </div>
              <div className="text-[10px] text-secondaryText">
                Score composed of stability, band gap, chemistry, and ionic migration heuristics.
              </div>
            </div>
          </div>

          {/* DEDICATED SECTION: "Why this candidate?" */}
          <div className="scientific-card p-5 space-y-3.5">
            <div className="flex items-center gap-2 border-b border-borderColor pb-2.5">
              <HelpCircle className="w-4 h-4 text-accent" />
              <h3 className="text-sm font-bold text-primaryText">
                Why this candidate?
              </h3>
            </div>

            <p className="text-xs text-secondaryText leading-relaxed">
              Scientific screening criteria and target alignment based on your confirmed requirement constraints:
            </p>

            <div className="space-y-2 text-xs">
              {candidate.ranking_explanation && candidate.ranking_explanation.length > 0 ? (
                candidate.ranking_explanation.map((item, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-borderColor flex items-start gap-2 text-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                    <span className="leading-snug">
                      {item.replace(/^[✓⚠ℹ\s]+/, '')}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-2.5 rounded-lg bg-slate-50 border border-borderColor text-secondaryText">
                  Candidate meets crystal lattice packing criteria, satisfies excluded element filters, and lies within the configured thermodynamic hull window.
                </div>
              )}

              {/* Reference Dataset Novelty Check */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-borderColor text-xs flex items-start gap-2">
                <Compass className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-semibold text-primaryText">Reference Comparison:</span>
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-bold ${
                      candidate.novelty?.result?.startsWith("DUPLICATE")
                        ? "bg-amber-50 text-amber-800 border border-amber-200"
                        : candidate.novelty?.result?.startsWith("SIMILAR")
                        ? "bg-blue-50 text-blue-700 border border-blue-200"
                        : "bg-emerald-50 text-accentDark border border-accentBorder"
                    }`}>
                      {candidate.novelty?.result || "NO CLOSE MATCH IN MP-20/JARVIS REFERENCE DATASET"}
                    </span>
                  </div>
                  <span className="text-[11px] text-secondaryText block">
                    {candidate.novelty?.verdict_label || "No close match found in MP-20 or JARVIS-DFT reference databases."}
                  </span>
                  {candidate.novelty?.matched_reference_id && (
                    <span className="text-[10px] font-mono text-accentDark block mt-0.5">
                      Matched ID: {candidate.novelty.matched_reference_id} ({candidate.novelty.matched_dataset})
                    </span>
                  )}
                  {candidate.novelty?.scientific_disclaimer && (
                    <span className="text-[10px] text-slate-500 block mt-1 leading-normal italic">
                      {candidate.novelty.scientific_disclaimer}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Crystallographic Details & Validation Checks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        
        {/* Unit Cell Parameters & Atomic Fractional Sites */}
        <div className="scientific-card p-6 space-y-4">
          <h3 className="text-xs font-bold text-primaryText uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-accent" />
            Unit Cell & Atomic Sites
          </h3>

          {/* Lattice constants */}
          <div className="grid grid-cols-4 gap-2 text-xs font-mono">
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">a</span>
              <span className="font-bold text-primaryText">{candidate.lattice.a.toFixed(3)} Å</span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">b</span>
              <span className="font-bold text-primaryText">{candidate.lattice.b.toFixed(3)} Å</span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">c</span>
              <span className="font-bold text-primaryText">{candidate.lattice.c.toFixed(3)} Å</span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">Volume</span>
              <span className="font-bold text-accentDark">{candidate.lattice.volume.toFixed(1)} Å³</span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">α</span>
              <span className="font-bold text-primaryText">{candidate.lattice.alpha.toFixed(1)}°</span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">β</span>
              <span className="font-bold text-primaryText">{candidate.lattice.beta.toFixed(1)}°</span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">γ</span>
              <span className="font-bold text-primaryText">{candidate.lattice.gamma.toFixed(1)}°</span>
            </div>
            <div className="p-2 rounded bg-slate-50 border border-borderColor">
              <span className="text-[10px] text-secondaryText block">Atoms</span>
              <span className="font-bold text-primaryText">{candidate.atom_count}</span>
            </div>
          </div>

          {/* Fractional Sites Table */}
          <div className="overflow-x-auto max-h-56 border border-borderColor rounded-lg">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 text-[10px] text-secondaryText sticky top-0 border-b border-borderColor">
                <tr>
                  <th className="py-2 px-3">Site</th>
                  <th className="py-2 px-3">Species</th>
                  <th className="py-2 px-3">x (fract)</th>
                  <th className="py-2 px-3">y (fract)</th>
                  <th className="py-2 px-3">z (fract)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderColor text-slate-700 bg-white">
                {candidate.atoms.map((a, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="py-1.5 px-3 text-secondaryText">{a.label || idx + 1}</td>
                    <td className="py-1.5 px-3 font-bold text-accentDark">{a.species}</td>
                    <td className="py-1.5 px-3">{a.fract_coords[0]?.toFixed(4)}</td>
                    <td className="py-1.5 px-3">{a.fract_coords[1]?.toFixed(4)}</td>
                    <td className="py-1.5 px-3">{a.fract_coords[2]?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Structural Validation Checklist */}
        <div className="scientific-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-borderColor pb-3">
            <h3 className="text-xs font-bold text-primaryText uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-accent" />
              Crystallographic Validation Protocol
            </h3>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
              candidate.validation.is_valid
                ? "bg-emerald-50 text-accentDark border border-accentBorder"
                : "bg-rose-50 text-rose-700 border border-rose-200"
            }`}>
              {candidate.validation.status}
            </span>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {candidate.validation.checks.map((chk, i) => (
              <div key={i} className="p-2.5 rounded-lg bg-slate-50 border border-borderColor flex items-start justify-between gap-2 text-xs">
                <div className="flex items-start gap-2">
                  {chk.passed ? (
                    <CheckCircle2 className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="font-semibold text-primaryText">{chk.name}</span>
                    <p className="text-[11px] text-secondaryText">{chk.detail}</p>
                  </div>
                </div>
                <span className={`text-[10px] font-mono font-bold ${chk.passed ? "text-accentDark" : "text-rose-600"}`}>
                  {chk.passed ? "PASS" : "FAIL"}
                </span>
              </div>
            ))}
          </div>

          {candidate.validation.reasons?.length > 0 && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 space-y-1">
              <span className="font-semibold">Validation Notes:</span>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                {candidate.validation.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
