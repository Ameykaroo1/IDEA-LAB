"use client";

import { useEffect, useState } from "react";
import { Database, ShieldCheck, Layers, ArrowRight, ExternalLink, Info } from "lucide-react";
import { getDatasets } from "@/lib/api";

export default function DatasetsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDatasets()
      .then((d) => setData(d))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Header */}
      <div className="border-b border-borderColor pb-5">
        <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider mb-1">
          <Database className="w-4 h-4 text-accent" /> Benchmark Reference Datasets
        </div>
        <h1 className="text-2xl font-bold text-primaryText tracking-tight">
          Known Energy Materials Reference Library
        </h1>
        <p className="text-xs sm:text-sm text-secondaryText mt-1 max-w-2xl leading-relaxed">
          Curated benchmark materials from Materials Project (MP-20) and JARVIS-DFT used for StructureMatcher deduplication, novelty checks, and stability comparisons.
        </p>
      </div>

      {/* Scientific Integrity Note */}
      <div className="scientific-card p-4 flex items-start gap-3 text-xs text-secondaryText">
        <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
        <div>
          <strong className="text-primaryText">Data Provenance:</strong> Property values in this reference library originate directly from peer-reviewed DFT calculations and published crystallographic databases. These serve strictly as novelty baselines; the system never presents existing reference database materials as newly discovered generative output.
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-secondaryText text-xs flex items-center justify-center gap-2">
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span>Loading reference materials...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data?.materials?.map((mat: any) => (
            <div
              key={mat.material_id}
              className="scientific-card p-5 space-y-3 hover:border-accent/40 transition"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-accentDark">{mat.material_id}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-50 text-accentDark border border-accentBorder">
                  {mat.is_stable ? "STABLE ON HULL" : "METASTABLE"}
                </span>
              </div>

              <div>
                <h3 className="text-lg font-bold text-primaryText">{mat.pretty_formula}</h3>
                <p className="text-xs text-secondaryText font-mono">
                  {mat.crystal_system} • {mat.space_group}
                </p>
              </div>

              {/* Application tags */}
              <div className="flex flex-wrap gap-1">
                {mat.application_tags?.map((t: string) => (
                  <span key={t} className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700 border border-slate-200">
                    {t}
                  </span>
                ))}
              </div>

              {/* Physical Properties */}
              <div className="grid grid-cols-3 gap-2 text-xs font-mono pt-3 border-t border-borderColor">
                <div className="p-2 rounded bg-slate-50 border border-borderColor">
                  <span className="text-[10px] text-secondaryText block">E Above Hull</span>
                  <span className="text-primaryText font-bold">
                    {mat.energy_above_hull !== undefined && mat.energy_above_hull !== null ? `${mat.energy_above_hull} eV/at` : "Not available"}
                  </span>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-borderColor">
                  <span className="text-[10px] text-secondaryText block">Band Gap</span>
                  <span className="text-primaryText font-bold">
                    {mat.band_gap !== undefined && mat.band_gap !== null ? `${mat.band_gap} eV` : "Not available"}
                  </span>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-borderColor">
                  <span className="text-[10px] text-secondaryText block">Formation Energy</span>
                  <span className="text-primaryText font-bold">
                    {mat.formation_energy_per_atom !== undefined && mat.formation_energy_per_atom !== null ? `${mat.formation_energy_per_atom} eV/at` : "Not available"}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-secondaryText font-mono pt-1">
                <span>Source: {mat.source || "Materials Project (MP-20)"}</span>
                <span className="text-accentDark font-semibold">Dataset Reference</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
