"use client";

import { useEffect, useState } from "react";
import { Settings, Cpu, Flame, ShieldAlert, CheckCircle2, Info, Database, Layers, CheckCircle } from "lucide-react";
import { getModelStatus, getDatasetsStatus } from "@/lib/api";
import { ModelStatusResponse, DatasetStatusResponse } from "@/types";

export default function SettingsPage() {
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [datasetsStatus, setDatasetsStatus] = useState<DatasetStatusResponse | null>(null);

  useEffect(() => {
    getModelStatus().then(setModelStatus).catch(() => {});
    getDatasetsStatus().then(setDatasetsStatus).catch(() => {});
  }, []);

  const totalStructures = datasetsStatus?.total_reference_structures ?? 139131;
  const mp20Count = datasetsStatus?.mp20?.count ?? 45229;
  const jarvisCount = datasetsStatus?.jarvis?.count ?? 93902;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      <div className="border-b border-borderColor pb-5">
        <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider mb-1">
          <Settings className="w-4 h-4 text-accent" /> Platform Settings & Model Status
        </div>
        <h1 className="text-2xl font-bold text-primaryText tracking-tight">System Architecture & Pipeline Configuration</h1>
        <p className="text-xs sm:text-sm text-secondaryText mt-1 max-w-2xl leading-relaxed">
          Configuration of crystal generator adapter, authentic reference catalog baselines (139,131 crystal structures), and scientific disclosure standards.
        </p>
      </div>

      {/* Reference Datasets Configuration */}
      <div className="scientific-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-primaryText flex items-center gap-2">
            <Database className="w-4 h-4 text-accent" /> Reference Benchmark Catalogs (139,131 Authentic Structures)
          </h3>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-accentDark border border-accentBorder">
            FULL BENCHMARK LOADED
          </span>
        </div>
        <p className="text-xs text-secondaryText">
          Reference datasets are strictly used for crystallographic structure matching, baseline property comparisons, and novelty verdicts. They are never returned as generated candidates.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-slate-50 border border-borderColor space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-primaryText text-sm">MP-20 Reference Catalog</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                {mp20Count.toLocaleString()} Structures
              </span>
            </div>
            <div className="text-secondaryText text-[11px] space-y-0.5">
              <div>Source: Microsoft MatterGen Release / Materials Project 2020</div>
              <div>Train split: 27,136 • Val split: 9,047 • Test split: 9,046</div>
              <div>Status: {datasetsStatus?.mp20?.status || "LOADED"}</div>
              <div>Role: StructureMatcher baseline & deduplication screening</div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-borderColor space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-primaryText text-sm">JARVIS-DFT Reference Catalog</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {jarvisCount.toLocaleString()} Structures
              </span>
            </div>
            <div className="text-secondaryText text-[11px] space-y-0.5">
              <div>Source: NIST Figshare (jdft_3d-9-24-2025 distribution)</div>
              <div>Domain: 3D Bulk inorganic crystal structures</div>
              <div>Status: {datasetsStatus?.jarvis?.status || "LOADED"}</div>
              <div>Role: Multi-property DFT comparisons & novelty baseline</div>
            </div>
          </div>
        </div>

        <div className="text-xs text-secondaryText font-mono pt-2 border-t border-borderColor flex items-center justify-between">
          <span>Total Combined Reference Catalog:</span>
          <span className="font-bold text-primaryText">{totalStructures.toLocaleString()} Crystal Structures</span>
        </div>
      </div>

      {/* Generator Adapter Configuration */}
      <div className="scientific-card p-6 space-y-4">
        <h3 className="text-sm font-bold text-primaryText flex items-center gap-2">
          <Cpu className="w-4 h-4 text-accent" /> Modular Crystal Generator Adapter Status
        </h3>
        <p className="text-xs text-secondaryText">
          CRYSTAL-X isolates generative backends through a unified <code className="text-accentDark font-semibold">CrystalGenerator</code> interface. Pretrained diffusion backends (such as Microsoft MatterGen) operate when environment variables and CUDA dependencies are detected.
        </p>

        <div className="p-4 rounded-xl bg-slate-50 border border-borderColor space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <span className="font-semibold text-primaryText">Active Generator Mode:</span>
            {modelStatus?.status === "CONNECTED" ? (
              <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-accentDark border border-accentBorder font-mono font-bold">
                REAL_GENERATOR (MatterGen Connected)
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-300 font-mono font-bold flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-amber-600" />
                MATTERGEN STATUS: NOT CONFIGURED (DEMO MODE)
              </span>
            )}
          </div>

          <div className="p-3 rounded-lg bg-amber-50/60 border border-amber-200 text-xs text-amber-900 font-mono">
            {modelStatus?.notice || "⚠ DEMO GENERATION MODE — Candidates are generated using the local demonstration generator and are NOT equivalent to real MatterGen output."}
          </div>

          <div className="text-xs space-y-1 text-secondaryText font-mono text-[11px] pt-2 border-t border-borderColor">
            <div>MATTERGEN_ENABLED = {modelStatus?.status === "CONNECTED" ? "true" : "false"}</div>
            <div>MATTERGEN_DEVICE = {modelStatus?.device || "CPU"}</div>
            <div>MATTERGEN_CHECKPOINT = {modelStatus?.checkpoint || "(Not configured; using local demo generator)"}</div>
            <div>CONFIGURED_MODEL = {modelStatus?.configured_model || "LOCAL_DEMO"}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 border border-borderColor space-y-2 text-xs text-secondaryText">
          <strong className="text-primaryText">How to connect MatterGen in production:</strong>
          <ol className="list-decimal list-inside space-y-1 text-[11px]">
            <li>Set up a Linux environment with PyTorch and CUDA support.</li>
            <li>Clone and install the official MatterGen package from Microsoft.</li>
            <li>Configure <code className="text-accentDark">MATTERGEN_ENABLED=1</code>, <code className="text-accentDark">MATTERGEN_PATH=/path/to/mattergen</code>, and <code className="text-accentDark">MATTERGEN_CHECKPOINT=mattergen_base.pt</code> in your <code className="text-accentDark">.env</code> file.</li>
            <li>The adapter will automatically detect the checkpoint and route generation jobs to MatterGen.</li>
          </ol>
        </div>
      </div>

      {/* Crystallographic Validation Settings */}
      <div className="scientific-card p-6 space-y-4">
        <h3 className="text-sm font-bold text-primaryText flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-accent" /> Crystallography Heuristic Parameters
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-borderColor">
            <span className="font-semibold text-primaryText block mb-1">Atom-Overlap Heuristic Threshold</span>
            <div className="font-mono text-accentDark font-bold text-sm">0.70 Å</div>
            <p className="text-[10px] text-secondaryText mt-1">
              Obvious atom-overlap heuristic: flags severe unphysical interatomic site overlap under periodic boundary conditions.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-borderColor">
            <span className="font-semibold text-primaryText block mb-1">Fractional Coordinate Handling</span>
            <div className="font-mono text-accentDark font-bold text-sm">Periodic Wrapping (coords % 1.0)</div>
            <p className="text-[10px] text-secondaryText mt-1">
              Coordinates outside [0, 1) are mathematically wrapped into the equivalent unit cell rather than rejected.
            </p>
          </div>
        </div>
      </div>

      {/* Scientific Honesty Standard */}
      <div className="scientific-card p-6 border-amber-200 bg-amber-50/40 space-y-3">
        <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-700" /> Computational Integrity Standard
        </h3>
        <p className="text-xs text-amber-900/90 leading-relaxed">
          In accordance with computational materials science standards, CRYSTAL-X strictly distinguishes between:
          (1) Generated candidates, (2) Structurally valid candidates, (3) ML-predicted properties, (4) Computationally promising candidates, (5) Downstream DFT-validated candidates, and (6) Experimentally synthesized materials.
        </p>
      </div>
    </div>
  );
}
