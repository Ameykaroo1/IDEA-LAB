"use client";

import { useEffect, useState } from "react";
import { Settings, Cpu, Flame, ShieldAlert, CheckCircle2, Info, Database, Layers } from "lucide-react";
import { getHealth, getModelStatus, getDatasetsStatus } from "@/lib/api";
import { ModelStatusResponse, DatasetStatusResponse } from "@/types";

export default function SettingsPage() {
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [datasetsStatus, setDatasetsStatus] = useState<DatasetStatusResponse | null>(null);

  useEffect(() => {
    getModelStatus().then(setModelStatus).catch(() => {});
    getDatasetsStatus().then(setDatasetsStatus).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-1">
          <Settings className="w-4 h-4" /> Platform Settings & Model Status
        </div>
        <h1 className="text-2xl font-black text-white">System Architecture & Generator Modes</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
          Configuration of modular crystal generator adapter, reference baseline catalogs, and scientific disclosure standards.
        </p>
      </div>

      {/* Generator Adapter Configuration */}
      <div className="glass-card rounded-2xl p-6 border border-surfaceBorder space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" /> Modular Crystal Generator Adapter Status
        </h3>
        <p className="text-xs text-slate-300">
          CRYSTAL-X isolates generative backends through a unified <code className="text-cyan-400">CrystalGenerator</code> interface. Pretrained diffusion backends (such as Microsoft MatterGen) operate when environment variables and CUDA dependencies are detected.
        </p>

        <div className="p-4 rounded-xl bg-slate-950/70 border border-surfaceBorder space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <span className="font-semibold text-slate-300">Active Generator Mode:</span>
            {modelStatus?.status === "CONNECTED" ? (
              <span className="px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono font-bold">
                REAL_GENERATOR (MatterGen Connected)
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded-full bg-amber-950/80 text-amber-300 border border-amber-800 font-mono font-bold flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-amber-400" />
                MATTERGEN STATUS: NOT CONFIGURED (DEMO MODE)
              </span>
            )}
          </div>

          <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-800/40 text-xs text-amber-200 font-mono">
            {modelStatus?.notice || "⚠ DEMO GENERATION MODE — Candidates are generated using the local demonstration generator and are NOT equivalent to real MatterGen output."}
          </div>

          <div className="text-xs space-y-1.5 text-slate-400 font-mono text-[11px] pt-2 border-t border-surfaceBorder">
            <div>MATTERGEN_ENABLED = {modelStatus?.status === "CONNECTED" ? "true" : "false"}</div>
            <div>MATTERGEN_DEVICE = {modelStatus?.device || "CPU"}</div>
            <div>MATTERGEN_CHECKPOINT = {modelStatus?.checkpoint || "(Not configured; using local demo generator)"}</div>
            <div>CONFIGURED_MODEL = {modelStatus?.configured_model || "LOCAL_DEMO"}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-surfaceBorder space-y-2 text-xs text-slate-400">
          <strong className="text-slate-200">How to connect MatterGen in production:</strong>
          <ol className="list-decimal list-inside space-y-1 text-[11px]">
            <li>Set up a Linux environment with PyTorch and CUDA support.</li>
            <li>Clone and install the official MatterGen package from Microsoft.</li>
            <li>Configure <code className="text-cyan-400">MATTERGEN_ENABLED=1</code>, <code className="text-cyan-400">MATTERGEN_PATH=/path/to/mattergen</code>, and <code className="text-cyan-400">MATTERGEN_CHECKPOINT=mattergen_base.pt</code> in your <code className="text-cyan-400">.env</code> file.</li>
            <li>The adapter will automatically detect the checkpoint and route generation jobs to MatterGen.</li>
          </ol>
        </div>
      </div>

      {/* Reference Datasets Configuration */}
      <div className="glass-card rounded-2xl p-6 border border-surfaceBorder space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Database className="w-4 h-4 text-purple-400" /> Reference Catalogs & Comparison Baselines
        </h3>
        <p className="text-xs text-slate-300">
          Reference datasets are strictly used for crystallographic structure matching, baseline property comparisons, and novelty verdicts. They are never returned as generated candidates.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-surfaceBorder space-y-1">
            <span className="font-semibold text-slate-200 block text-sm">MP-20 Reference Catalog</span>
            <div className="text-cyan-300 font-bold">Status: {datasetsStatus?.mp20?.status || "LOADED"}</div>
            <div className="text-slate-400">Structures: {datasetsStatus?.mp20?.count || 4} reference crystals</div>
            <div className="text-[10px] text-slate-500">Role: Novelty baseline & structure matching</div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-surfaceBorder space-y-1">
            <span className="font-semibold text-slate-200 block text-sm">JARVIS-DFT Reference Catalog</span>
            <div className="text-purple-300 font-bold">Status: {datasetsStatus?.jarvis?.status || "LOADED"}</div>
            <div className="text-slate-400">Structures: {datasetsStatus?.jarvis?.count || 3} reference crystals</div>
            <div className="text-[10px] text-slate-500">Role: Clean-energy DFT property comparisons</div>
          </div>
        </div>
      </div>

      {/* Crystallographic Validation Settings */}
      <div className="glass-card rounded-2xl p-6 border border-surfaceBorder space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Crystallography Heuristic Parameters
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-surfaceBorder">
            <span className="font-semibold text-slate-200 block mb-1">Atom-Overlap Heuristic Threshold</span>
            <div className="font-mono text-cyan-300 font-bold text-sm">0.70 Å</div>
            <p className="text-[10px] text-slate-500 mt-1">
              Obvious atom-overlap heuristic: flags severe unphysical interatomic site overlap under periodic boundary conditions.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-surfaceBorder">
            <span className="font-semibold text-slate-200 block mb-1">Fractional Coordinate Handling</span>
            <div className="font-mono text-emerald-300 font-bold text-sm">Periodic Wrapping (coords % 1.0)</div>
            <p className="text-[10px] text-slate-500 mt-1">
              Coordinates outside [0, 1) are mathematically wrapped into the equivalent unit cell rather than rejected.
            </p>
          </div>
        </div>
      </div>

      {/* Scientific Honesty Standard */}
      <div className="glass-card rounded-2xl p-6 border border-amber-900/40 bg-amber-950/10 space-y-3">
        <h3 className="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center gap-2">
          <ShieldAlert className="w-4 h-4" /> Computational Integrity Standard
        </h3>
        <p className="text-xs text-amber-200/90 leading-relaxed">
          In accordance with computational materials science standards, CRYSTAL-X strictly distinguishes between:
          (1) Generated candidates, (2) Structurally valid candidates, (3) ML-predicted properties, (4) Computationally promising candidates, (5) Downstream DFT-validated candidates, and (6) Experimentally synthesized materials.
        </p>
      </div>
    </div>
  );
}
