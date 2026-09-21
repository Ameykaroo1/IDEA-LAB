"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Cpu, 
  Download, 
  Trash2, 
  AlertTriangle, 
  CheckCircle2, 
  FileArchive, 
  ArrowRight,
  Atom,
  Eye,
  Info
} from "lucide-react";
import { getDftQueue, removeFromDftQueue, exportDftPackage } from "@/lib/api";
import { DFTQueueItem } from "@/types";

export default function DFTQueuePage() {
  const [queue, setQueue] = useState<DFTQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getDftQueue();
      setQueue(data);
    } catch (err) {
      console.error("Failed to load DFT queue:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRemove = async (candId: string) => {
    try {
      await removeFromDftQueue(candId);
      setQueue((prev) => prev.filter((item) => item.candidate_id !== candId));
    } catch (err) {
      alert("Failed to remove candidate from DFT queue");
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      setExportSuccess(null);
      const res = await exportDftPackage();
      setExportSuccess(`Package generated successfully at: ${res.export_dir}`);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-borderColor pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider mb-1">
            <Cpu className="w-4 h-4 text-accent" /> Downstream Calculation Queue
          </div>
          <h1 className="text-2xl font-bold text-primaryText tracking-tight">
            DFT Validation Preparation Queue
          </h1>
          <p className="text-xs text-secondaryText mt-0.5">
            Stage promising candidates for downstream first-principles DFT relaxation (VASP / Quantum ESPRESSO).
          </p>
        </div>

        {queue.length > 0 && (
          <button
            onClick={handleExport}
            disabled={exporting}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accentDark text-white font-medium text-xs transition flex items-center gap-2 shadow-sm disabled:opacity-50"
          >
            <FileArchive className="w-4 h-4" />
            <span>{exporting ? "Packaging DFT Files..." : "Export DFT Package"}</span>
          </button>
        )}
      </div>

      {/* Downstream Clarification Banner */}
      <div className="p-4 rounded-xl bg-slate-50 border border-borderColor flex items-start gap-3">
        <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-primaryText">
            Scientific Scope: DFT validation is a downstream calculation and is not executed in real-time by this prototype.
          </p>
          <p className="text-secondaryText leading-relaxed">
            This module generates standardized inputs (POSCAR coordinates, INCAR relaxation templates, candidate CIFs, and screening provenance metadata JSON) formatted for cluster HPC job schedulers.
          </p>
        </div>
      </div>

      {exportSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-accentBorder text-xs text-accentDark flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-accent shrink-0" />
          <span>{exportSuccess}</span>
        </div>
      )}

      {/* Queue List */}
      <div className="scientific-card overflow-hidden">
        {loading ? (
          <div className="py-20 text-center text-secondaryText text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span>Loading DFT queue...</span>
          </div>
        ) : queue.length === 0 ? (
          <div className="py-20 text-center text-secondaryText text-xs space-y-2">
            <Cpu className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="font-semibold text-primaryText">DFT queue is currently empty.</p>
            <p className="text-secondaryText max-w-sm mx-auto">
              Select promising candidates from the library or discovery results to stage them for downstream DFT calculations.
            </p>
            <div className="pt-2">
              <Link
                href="/candidates"
                className="inline-flex items-center gap-1.5 text-accentDark font-semibold hover:underline"
              >
                <span>Browse Materials Library</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-secondaryText bg-slate-50 border-b border-borderColor">
                <tr>
                  <th className="py-3 px-4 font-semibold">Candidate ID</th>
                  <th className="py-3 px-4 font-semibold">Formula</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Predicted E_hull</th>
                  <th className="py-3 px-4 font-semibold">Predicted Band Gap</th>
                  <th className="py-3 px-4 font-semibold">Selection Reason</th>
                  <th className="py-3 px-4 font-semibold">Rank Score</th>
                  <th className="py-3 px-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderColor text-slate-700 bg-white">
                {queue.map((item) => (
                  <tr key={item.candidate_id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 font-mono font-semibold text-primaryText">
                      <Link href={`/candidates/${item.candidate_id}`} className="hover:text-accentDark hover:underline">
                        {item.candidate_id}
                      </Link>
                    </td>
                    <td className="py-3 px-4 font-bold text-primaryText">{item.formula}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-primaryText">
                      {item.predicted_properties?.energy_above_hull !== undefined && item.predicted_properties?.energy_above_hull !== null
                        ? `${item.predicted_properties.energy_above_hull} eV/at`
                        : "Not available"}
                    </td>
                    <td className="py-3 px-4 font-mono text-primaryText">
                      {item.predicted_properties?.band_gap !== undefined && item.predicted_properties?.band_gap !== null
                        ? `${item.predicted_properties.band_gap} eV`
                        : "Not available"}
                    </td>
                    <td className="py-3 px-4 text-secondaryText max-w-xs truncate" title={item.reason_selected}>
                      {item.reason_selected}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-accentDark">
                      {item.ranking_score ? `${item.ranking_score.toFixed(1)}/100` : "N/A"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/candidates/${item.candidate_id}`}
                          className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-secondaryText hover:text-primaryText transition"
                          title="Inspect candidate"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </Link>
                        <button
                          onClick={() => handleRemove(item.candidate_id)}
                          className="p-1.5 rounded-lg bg-slate-100 hover:bg-rose-50 text-secondaryText hover:text-rose-600 transition"
                          title="Remove from queue"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
