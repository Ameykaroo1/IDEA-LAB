"use client";

import { useEffect, useState, useCallback } from "react";
import { Database, ShieldCheck, Search, Filter, RefreshCw, ChevronLeft, ChevronRight, Layers, Info, CheckCircle2 } from "lucide-react";
import { getDatasets } from "@/lib/api";

export default function DatasetsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [datasetSource, setDatasetSource] = useState("ALL");
  const [elementFilter, setElementFilter] = useState("");
  const [stableOnly, setStableOnly] = useState(false);
  const [page, setPage] = useState(1);

  const fetchMaterials = useCallback((newPage: number = 1) => {
    setLoading(true);
    getDatasets({
      query: searchQuery.trim() || undefined,
      dataset_source: datasetSource !== "ALL" ? datasetSource : undefined,
      element: elementFilter.trim() || undefined,
      stable_only: stableOnly,
      page: newPage,
      limit: 24
    })
      .then((d) => {
        setData(d);
        setPage(newPage);
      })
      .catch((err) => console.error("Error fetching datasets:", err))
      .finally(() => setLoading(false));
  }, [searchQuery, datasetSource, elementFilter, stableOnly]);

  useEffect(() => {
    fetchMaterials(1);
  }, [datasetSource, stableOnly]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchMaterials(1);
  };

  const mp20Count = data?.mp20_count ?? 45229;
  const jarvisCount = data?.jarvis_count ?? 93902;
  const totalCount = data?.total_reference_structures ?? 139131;
  const totalMatching = data?.total_records ?? 0;
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Header */}
      <div className="border-b border-borderColor pb-5">
        <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider mb-1">
          <Database className="w-4 h-4 text-accent" /> Verified Crystallographic Reference Library
        </div>
        <h1 className="text-2xl font-bold text-primaryText tracking-tight">
          Inorganic Reference Crystal Catalog
        </h1>
        <p className="text-xs sm:text-sm text-secondaryText mt-1 max-w-3xl leading-relaxed">
          The complete benchmark catalog of {totalCount.toLocaleString()} authentic crystal structures ({mp20Count.toLocaleString()} MP-20 + {jarvisCount.toLocaleString()} JARVIS-DFT). Used for StructureMatcher deduplication, novelty scoring, and baseline comparison.
        </p>
      </div>

      {/* Dataset Overview Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Metric */}
        <div className="scientific-card p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-secondaryText font-mono">
            <span>TOTAL REFERENCE STRUCTURES</span>
            <Database className="w-3.5 h-3.5 text-accent" />
          </div>
          <div className="text-2xl font-bold text-primaryText font-mono">
            {totalCount.toLocaleString()}
          </div>
          <div className="text-[11px] text-secondaryText">
            Complete indexed reference database
          </div>
        </div>

        {/* MP-20 Metric */}
        <div className="scientific-card p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-secondaryText font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> MP-20 (MATERIALS PROJECT)
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
              45,229
            </span>
          </div>
          <div className="text-xl font-bold text-primaryText font-mono">
            {mp20Count.toLocaleString()}
          </div>
          <div className="text-[11px] text-secondaryText font-mono">
            Train: 27,136 • Val: 9,047 • Test: 9,046
          </div>
        </div>

        {/* JARVIS-DFT Metric */}
        <div className="scientific-card p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-secondaryText font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> JARVIS-DFT (NIST 3D)
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
              93,902
            </span>
          </div>
          <div className="text-xl font-bold text-primaryText font-mono">
            {jarvisCount.toLocaleString()}
          </div>
          <div className="text-[11px] text-secondaryText font-mono">
            3D Bulk inorganic crystal structures
          </div>
        </div>
      </div>

      {/* Scientific Integrity Disclaimer */}
      <div className="scientific-card p-4 flex items-start gap-3 text-xs text-secondaryText bg-slate-50/60">
        <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
        <div>
          <strong className="text-primaryText">Reference Catalog Separation:</strong> All {totalCount.toLocaleString()} records below represent authentic peer-reviewed crystallographic baselines. The CRYSTAL-X platform never returns existing reference database materials as newly generated candidates. All generative candidates are strictly evaluated against this catalog for duplicate and similarity verdicts.
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="scientific-card p-4 space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          {/* Text search */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-secondaryText absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by formula (e.g. K2O, LiCoO2) or Material ID (e.g. mp-149, JVASP-1002)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-borderColor bg-white focus:outline-none focus:border-accent text-primaryText placeholder:text-secondaryText/60"
            />
          </div>

          {/* Element filter */}
          <div className="w-full md:w-44">
            <input
              type="text"
              placeholder="Element (e.g. K, Na)"
              value={elementFilter}
              onChange={(e) => setElementFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-borderColor bg-white focus:outline-none focus:border-accent text-primaryText placeholder:text-secondaryText/60 font-mono"
            />
          </div>

          {/* Search Button */}
          <button
            type="submit"
            className="px-4 py-2 bg-accent text-white rounded-lg text-xs font-semibold hover:bg-accentDark transition flex items-center justify-center gap-1.5 shadow-sm"
          >
            <Search className="w-3.5 h-3.5" />
            Search
          </button>
        </form>

        {/* Filter controls row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-borderColor/60 text-xs">
          {/* Dataset Source Tabs */}
          <div className="flex items-center gap-1">
            <span className="text-[11px] text-secondaryText font-mono mr-1">Source:</span>
            {[
              { id: "ALL", label: `All (${totalCount.toLocaleString()})` },
              { id: "MP-20", label: `MP-20 (${mp20Count.toLocaleString()})` },
              { id: "JARVIS-DFT", label: `JARVIS-DFT (${jarvisCount.toLocaleString()})` }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setDatasetSource(tab.id)}
                className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition ${
                  datasetSource === tab.id
                    ? "bg-primaryText text-white"
                    : "bg-slate-100 text-secondaryText hover:text-primaryText"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Stable toggle */}
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-secondaryText">
              <input
                type="checkbox"
                checked={stableOnly}
                onChange={(e) => setStableOnly(e.target.checked)}
                className="rounded border-borderColor text-accent focus:ring-accent w-3.5 h-3.5"
              />
              <span>Stable on Hull only (E_hull ≤ 0.05 eV/at)</span>
            </label>
          </div>
        </div>
      </div>

      {/* Results Header and Counter */}
      <div className="flex items-center justify-between text-xs text-secondaryText font-mono">
        <div>
          Showing {loading ? "..." : data?.materials?.length ?? 0} of {totalMatching.toLocaleString()} matching reference structures
        </div>
        {totalPages > 1 && (
          <div>
            Page {page} of {totalPages}
          </div>
        )}
      </div>

      {/* Grid of Reference Materials */}
      {loading ? (
        <div className="py-24 text-center text-secondaryText text-xs flex items-center justify-center gap-2">
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span>Searching 139,131 reference structures...</span>
        </div>
      ) : data?.materials?.length === 0 ? (
        <div className="py-20 text-center text-secondaryText text-xs scientific-card p-8 space-y-2">
          <Database className="w-8 h-8 text-secondaryText/40 mx-auto" />
          <div className="font-semibold text-primaryText">No matching reference materials found</div>
          <div>Try adjusting your element filter or search term.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {data?.materials?.map((mat: any) => {
            const isMp20 = mat.dataset_source === "MP-20";
            return (
              <div
                key={mat.material_id}
                className="scientific-card p-4 space-y-2.5 hover:border-accent/40 transition flex flex-col justify-between"
              >
                <div>
                  {/* Top Bar: ID and Badges */}
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-mono text-xs font-bold text-primaryText">{mat.material_id}</span>
                    <div className="flex items-center gap-1">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
                        isMp20
                          ? "bg-blue-50 text-blue-700 border border-blue-200"
                          : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      }`}>
                        {mat.dataset_source}
                      </span>
                      {mat.dataset_split && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-600 bg-slate-100 border border-slate-200">
                          {mat.dataset_split}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Formula and Crystallographic Info */}
                  <div>
                    <h3 className="text-base font-bold text-primaryText font-mono tracking-tight">
                      {mat.pretty_formula}
                    </h3>
                    <p className="text-[11px] text-secondaryText font-mono truncate">
                      {mat.crystal_system} • {mat.space_group}
                    </p>
                  </div>
                </div>

                {/* Physical Properties Grid */}
                <div className="grid grid-cols-3 gap-1.5 text-xs font-mono pt-2 border-t border-borderColor/60">
                  <div className="p-1.5 rounded bg-slate-50 border border-borderColor/60 text-center">
                    <span className="text-[9px] text-secondaryText block leading-tight">E Above Hull</span>
                    <span className="text-primaryText font-bold text-[11px]">
                      {mat.energy_above_hull !== null && mat.energy_above_hull !== undefined
                        ? `${mat.energy_above_hull.toFixed(3)} eV`
                        : "N/A"}
                    </span>
                  </div>
                  <div className="p-1.5 rounded bg-slate-50 border border-borderColor/60 text-center">
                    <span className="text-[9px] text-secondaryText block leading-tight">Band Gap</span>
                    <span className="text-primaryText font-bold text-[11px]">
                      {mat.band_gap !== null && mat.band_gap !== undefined
                        ? `${mat.band_gap.toFixed(2)} eV`
                        : "N/A"}
                    </span>
                  </div>
                  <div className="p-1.5 rounded bg-slate-50 border border-borderColor/60 text-center">
                    <span className="text-[9px] text-secondaryText block leading-tight">Formation E</span>
                    <span className="text-primaryText font-bold text-[11px]">
                      {mat.formation_energy_per_atom !== null && mat.formation_energy_per_atom !== undefined
                        ? `${mat.formation_energy_per_atom.toFixed(2)} eV`
                        : "N/A"}
                    </span>
                  </div>
                </div>

                {/* Footer status */}
                <div className="flex items-center justify-between text-[10px] text-secondaryText font-mono pt-1">
                  <span className={mat.is_stable ? "text-accentDark font-semibold flex items-center gap-1" : "text-slate-500"}>
                    {mat.is_stable ? "● Stable (≤ 0.05 eV)" : "○ Metastable"}
                  </span>
                  <span className="text-secondaryText/80">Ref Baseline</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-6">
          <button
            onClick={() => fetchMaterials(Math.max(1, page - 1))}
            disabled={page <= 1 || loading}
            className="px-3 py-1.5 rounded-lg border border-borderColor text-xs font-mono disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 flex items-center gap-1 text-primaryText"
          >
            <ChevronLeft className="w-3.5 h-3.5" /> Previous
          </button>
          <span className="text-xs font-mono text-secondaryText px-2">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => fetchMaterials(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages || loading}
            className="px-3 py-1.5 rounded-lg border border-borderColor text-xs font-mono disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 flex items-center gap-1 text-primaryText"
          >
            Next <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
