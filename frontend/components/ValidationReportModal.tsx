"use client";

import { X, CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";
import { StructuralValidationResult } from "@/types";

interface ValidationReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateId: string;
  formula: string;
  validation: StructuralValidationResult;
}

export default function ValidationReportModal({
  isOpen,
  onClose,
  candidateId,
  formula,
  validation,
}: ValidationReportModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl bg-white rounded-xl border border-borderColor shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-borderColor bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${validation.is_valid ? "bg-emerald-50 text-accentDark border border-accentBorder" : "bg-rose-50 text-rose-700 border border-rose-200"}`}>
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-primaryText flex items-center gap-2">
                Structural Validation: <span className="font-mono text-accentDark">{candidateId}</span>
              </h2>
              <p className="text-xs text-secondaryText">Formula: {formula} • Pymatgen deterministic crystallographic checks</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-secondaryText hover:text-primaryText hover:bg-slate-200 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4">
          {/* Status Banner */}
          <div className={`p-4 rounded-lg border flex items-start gap-3 ${
            validation.is_valid 
              ? "bg-emerald-50/70 border-emerald-200 text-accentDark"
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}>
            {validation.is_valid ? (
              <CheckCircle2 className="w-5 h-5 text-accent shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
            )}
            <div>
              <span className="font-bold text-xs tracking-wide">
                OVERALL STATUS: {validation.status}
              </span>
              <p className="text-xs mt-0.5 leading-relaxed text-slate-600">
                {validation.is_valid
                  ? "This crystal candidate passed deterministic crystallographic syntax, physical density, chemistry, and atomic overlap criteria."
                  : "This structure failed one or more crystallographic or chemistry requirements."}
              </p>
              {validation.coordinates_wrapped && (
                <p className="text-xs text-accentDark mt-1 font-mono">
                  • Periodic fractional coordinates outside [0, 1) were mathematically wrapped into equivalent unit cell.
                </p>
              )}
            </div>
          </div>

          {/* Failure Reasons */}
          {validation.reasons && validation.reasons.length > 0 && (
            <div className="p-4 rounded-lg bg-rose-50/60 border border-rose-200">
              <h4 className="text-xs font-semibold text-rose-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> Specific Failure Reasons
              </h4>
              <ul className="space-y-1.5">
                {validation.reasons.map((r, i) => (
                  <li key={i} className="text-xs text-rose-700 flex items-start gap-2">
                    <span className="text-rose-500 font-bold">•</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Individual Checks Checklist */}
          <div>
            <h4 className="text-xs font-semibold text-secondaryText uppercase tracking-wider mb-3">
              Crystallographic Verification Criteria ({validation.checks?.length || 0})
            </h4>
            <div className="space-y-2">
              {validation.checks?.map((chk, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-slate-50 border border-borderColor flex items-start justify-between gap-3 text-xs"
                >
                  <div className="flex items-start gap-2.5">
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
                  <span className={`text-[10px] font-mono font-bold ${
                    chk.passed ? "text-accentDark" : "text-rose-600"
                  }`}>
                    {chk.passed ? "PASS" : "FAIL"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-borderColor bg-slate-50 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-xs font-medium text-white bg-primaryText hover:bg-slate-800 transition"
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
}
