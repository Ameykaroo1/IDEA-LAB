"use client";

import { useState } from "react";
import { Sliders, RefreshCw, X, Check } from "lucide-react";
import { RankingWeights } from "@/types";

interface RankingWeightsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentWeights: RankingWeights;
  onApply: (weights: RankingWeights) => void;
}

export default function RankingWeightsModal({
  isOpen,
  onClose,
  currentWeights,
  onApply,
}: RankingWeightsModalProps) {
  const [weights, setWeights] = useState<RankingWeights>({ ...currentWeights });

  if (!isOpen) return null;

  const total = weights.stability + weights.band_gap + weights.ionic_conductivity + weights.chemistry;

  const handleChange = (key: keyof RankingWeights, value: number) => {
    setWeights((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const resetToDefault = () => {
    setWeights({
      stability: 0.4,
      band_gap: 0.3,
      ionic_conductivity: 0.2,
      chemistry: 0.1,
    });
  };

  const handleSave = () => {
    const sum = total > 0 ? total : 1.0;
    const normalized: RankingWeights = {
      stability: Math.round((weights.stability / sum) * 100) / 100,
      band_gap: Math.round((weights.band_gap / sum) * 100) / 100,
      ionic_conductivity: Math.round((weights.ionic_conductivity / sum) * 100) / 100,
      chemistry: Math.round((weights.chemistry / sum) * 100) / 100,
    };
    onApply(normalized);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-lg bg-white rounded-xl border border-borderColor shadow-xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-borderColor bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Sliders className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-bold text-primaryText">Adjust Ranking Weights</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-secondaryText hover:text-primaryText hover:bg-slate-200 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          <p className="text-xs text-secondaryText leading-relaxed">
            Customize the multi-objective ranking equation. When a property is unavailable, weights dynamically renormalize across remaining criteria.
          </p>

          {/* Sliders */}
          <div className="space-y-4">
            {/* Stability */}
            <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="font-semibold text-primaryText">Thermodynamic Stability (E_hull)</span>
                <span className="font-mono text-accentDark font-bold">{Math.round(weights.stability * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={weights.stability}
                onChange={(e) => handleChange("stability", parseFloat(e.target.value))}
                className="w-full accent-accent h-1.5 bg-slate-200 rounded-lg cursor-pointer"
              />
            </div>

            {/* Band Gap */}
            <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="font-semibold text-primaryText">Target Band Gap Match</span>
                <span className="font-mono text-accentDark font-bold">{Math.round(weights.band_gap * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={weights.band_gap}
                onChange={(e) => handleChange("band_gap", parseFloat(e.target.value))}
                className="w-full accent-accent h-1.5 bg-slate-200 rounded-lg cursor-pointer"
              />
            </div>

            {/* Ionic Conductivity */}
            <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="font-semibold text-primaryText">Ionic Conductivity</span>
                <span className="font-mono text-accentDark font-bold">{Math.round(weights.ionic_conductivity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={weights.ionic_conductivity}
                onChange={(e) => handleChange("ionic_conductivity", parseFloat(e.target.value))}
                className="w-full accent-accent h-1.5 bg-slate-200 rounded-lg cursor-pointer"
              />
            </div>

            {/* Chemistry */}
            <div className="p-3 rounded-lg bg-slate-50 border border-borderColor">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="font-semibold text-primaryText">Chemistry & Synthesizability Compliance</span>
                <span className="font-mono text-accentDark font-bold">{Math.round(weights.chemistry * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={weights.chemistry}
                onChange={(e) => handleChange("chemistry", parseFloat(e.target.value))}
                className="w-full accent-accent h-1.5 bg-slate-200 rounded-lg cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-borderColor bg-slate-50 flex items-center justify-between">
          <button
            onClick={resetToDefault}
            className="flex items-center gap-1.5 text-xs text-secondaryText hover:text-primaryText transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Reset Defaults
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs text-secondaryText hover:text-primaryText bg-white hover:bg-slate-100 border border-borderColor transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold text-white bg-accent hover:bg-accentDark transition flex items-center gap-1.5 shadow-sm"
            >
              <Check className="w-3.5 h-3.5" />
              Apply & Re-Rank
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
