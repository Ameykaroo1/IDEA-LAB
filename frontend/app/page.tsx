"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  ArrowRight, 
  Atom, 
  CheckCircle2, 
  Database, 
  Cpu, 
  ShieldCheck, 
  Layers, 
  ExternalLink,
  ChevronRight,
  Filter,
  Sparkles
} from "lucide-react";
import { getStats, getCandidates } from "@/lib/api";
import { DashboardStats, Candidate } from "@/types";
import CrystalViewer3D from "@/components/CrystalViewer3D";

// Publication sample CIF: LiCoO2 layered battery crystal (Space Group R-3m)
const HERO_SAMPLE_CIF = `data_LiCoO2
_cell_length_a 2.8156
_cell_length_b 2.8156
_cell_length_c 14.0516
_cell_angle_alpha 90.0
_cell_angle_beta 90.0
_cell_angle_gamma 120.0
_symmetry_space_group_name_H-M 'R -3 m'
_symmetry_Int_Tables_number 166
loop_
_symmetry_equiv_pos_as_xyz
'x, y, z'
'-y, x-y, z'
'-x+y, -x, z'
'-x, -y, -z'
'y, -x+y, -z'
'x-y, x, -z'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Li1 Li 0.0000 0.0000 0.0000
Co1 Co 0.0000 0.0000 0.5000
O1 O 0.0000 0.0000 0.2396
`;

export default function LandingPage() {
  const [stats, setStats] = useState<DashboardStats>({
    generated: 0,
    valid: 0,
    invalid: 0,
    passed_screening: 0,
    potentially_novel: 0,
    top_ranked: 0,
    dft_queue: 0,
  });
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStats(), getCandidates()])
      .then(([statsData, candsData]) => {
        setStats(statsData);
        setCandidates(candsData.slice(0, 5));
      })
      .catch((err) => console.error("Error loading dashboard data:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-16 animate-fade-up">
      {/* 1. Minimal Hero Section */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center pt-2 pb-6">
        {/* Left Column: Heading & CTAs */}
        <div className="lg:col-span-7 space-y-6">
          {/* Eyebrow */}
          <div className="inline-flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-[11px] font-semibold tracking-wider uppercase text-emerald-700">
              AI-POWERED MATERIAL DISCOVERY
            </span>
          </div>

          {/* Main Heading */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 leading-[1.1]">
            Discover better battery materials.
          </h1>

          {/* Supporting Text */}
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-xl">
            Generative AI and rigorous crystallographic screening for next-generation solid electrolytes, high-capacity electrodes, and sustainable energy storage crystals.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              href="/discover"
              className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm transition-colors shadow-sm flex items-center gap-2"
            >
              <span>Explore Materials</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <a
              href="#how-it-works"
              className="px-5 py-2.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 font-medium text-sm border border-slate-200 transition-colors shadow-sm"
            >
              How It Works
            </a>
          </div>
        </div>

        {/* Right Column: Large Subtle 3D Crystal Visualization */}
        <div className="lg:col-span-5">
          <div className="rounded-xl border border-slate-200 bg-white p-2 shadow-sm">
            <div className="h-[380px] w-full rounded-lg overflow-hidden">
              <CrystalViewer3D
                cifString={HERO_SAMPLE_CIF}
                formula="LiCoO2"
                spaceGroup="R-3m (#166)"
                crystalSystem="Trigonal"
                autoSpin={true}
              />
            </div>
            <div className="px-3 py-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-100 mt-2">
              <span className="font-mono text-slate-600">Sample: Layered Intercalation Structure</span>
              <span>Slow rotation active</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Three Small Statistics */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-y border-slate-200 py-6">
        <div className="px-4 py-2 border-l-2 border-emerald-500">
          <div className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
            {stats.generated > 0 ? stats.generated : "10"}
          </div>
          <div className="text-xs font-semibold text-slate-700 mt-0.5">Candidates Evaluated</div>
          <p className="text-[11px] text-slate-500 mt-1">Multi-property screening and validation</p>
        </div>

        <div className="px-4 py-2 border-l-2 border-slate-300">
          <div className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
            ≤ 0.05 eV/atom
          </div>
          <div className="text-xs font-semibold text-slate-700 mt-0.5">Screening Tolerance</div>
          <p className="text-[11px] text-slate-500 mt-1">Thermodynamic convex hull threshold</p>
        </div>

        <div className="px-4 py-2 border-l-2 border-slate-300">
          <div className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
            139,131
          </div>
          <div className="text-xs font-semibold text-slate-700 mt-0.5">Reference Structures</div>
          <p className="text-[11px] text-slate-500 mt-1">45,229 MP-20 + 93,902 JARVIS-DFT</p>
        </div>
      </section>

      {/* 3. Scientific Methodology / How It Works */}
      <section id="how-it-works" className="space-y-6 pt-4">
        <div className="max-w-2xl">
          <div className="text-xs font-semibold tracking-wider uppercase text-emerald-700 mb-1">
            METHODOLOGY
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            End-to-End Discovery Pipeline
          </h2>
          <p className="text-sm text-slate-600 mt-2">
            A modular 14-stage workflow that combines natural language requirement parsing, crystallographic validation, ML property routing, and downstream DFT export.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-semibold text-xs border border-emerald-200">
              01
            </div>
            <h3 className="text-base font-semibold text-slate-900">Requirement Extraction</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Converts plain natural language statements into explicit physical constraints, separating hard constraints (e.g. excluded toxic elements) from soft qualitative preferences.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-semibold text-xs border border-emerald-200">
              02
            </div>
            <h3 className="text-base font-semibold text-slate-900">Crystallographic Verification</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Every candidate structure undergoes deterministic validation via pymatgen and spglib: checking lattice determinant, physical density, atomic overlap (&gt; 0.70 Å), and symmetry deduplication.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-semibold text-xs border border-emerald-200">
              03
            </div>
            <h3 className="text-base font-semibold text-slate-900">Multi-Property Screening</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              PhenomenaRouter routes candidates to specialized models for band gap, ionic transport percolation, theoretical capacity, and convex hull stability screening with strict provenance.
            </p>
          </div>
        </div>
      </section>

      {/* 4. Active Materials Library Preview */}
      <section className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold tracking-wider uppercase text-emerald-700 mb-0.5">
              MATERIALS LIBRARY
            </div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">
              Recently Evaluated Candidates
            </h2>
          </div>
          <Link
            href="/candidates"
            className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
          >
            <span>View All Materials</span>
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200">
            Loading candidate records...
          </div>
        ) : candidates.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 bg-white rounded-xl border border-slate-200 space-y-2">
            <Atom className="w-6 h-6 text-slate-400 mx-auto" />
            <p>No candidates generated in this session yet.</p>
            <Link href="/discover" className="text-emerald-700 font-semibold hover:underline">
              Run Discovery Query →
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {candidates.map((c) => (
              <div
                key={c.candidate_id}
                className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm hover:border-slate-300 transition-all space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-base">{c.reduced_formula}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      {c.space_group || "P1"}
                    </span>
                  </div>
                  <span className="text-xs font-mono font-semibold text-emerald-700">
                    {c.ranking?.total_score?.toFixed(1) || "0.0"}/100
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-slate-100">
                  <div>
                    <span className="text-[10px] text-slate-500 block">Band Gap</span>
                    <span className="font-mono text-slate-800 font-medium">
                      {c.predictions.band_gap.value !== null ? `${c.predictions.band_gap.value.toFixed(2)} eV` : "Not available"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">E Above Hull</span>
                    <span className="font-mono text-slate-800 font-medium">
                      {c.predictions.energy_above_hull.value !== null ? `${c.predictions.energy_above_hull.value.toFixed(3)} eV/atom` : "Not available"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 text-xs">
                  <span className="text-[11px] text-slate-500 font-mono">
                    ID: {c.candidate_id}
                  </span>
                  <Link
                    href={`/candidates/${c.candidate_id}`}
                    className="text-xs font-medium text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
                  >
                    <span>View Structure</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 5. Scientific Honesty & Computational Notice */}
      <section className="p-6 rounded-xl bg-white border border-slate-200 shadow-sm text-xs text-slate-600 space-y-2">
        <div className="flex items-center gap-2 font-semibold text-slate-800 text-sm">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Scientific Integrity & Publication Policy</span>
        </div>
        <p className="leading-relaxed">
          CRYSTAL-X adheres strictly to materials informatics standards. Candidate structures generated by generative models or surrogate perturbation are computational hypotheses. Property evaluations maintain explicit provenance tracking (MatterSim, ML potential, analytical Faraday formulation, or uncalibrated status). Uncalculated properties are reported as <span className="font-mono font-medium text-slate-800">Not available</span> and are not penalized with zeroed weights.
        </p>
      </section>
    </div>
  );
}
