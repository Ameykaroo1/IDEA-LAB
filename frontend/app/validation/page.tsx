"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Upload, 
  CheckCircle2, 
  XCircle, 
  ShieldCheck, 
  FileText, 
  ArrowRight,
  AlertTriangle,
  FileCode
} from "lucide-react";
import { uploadCIF } from "@/lib/api";
import { Candidate } from "@/types";
import CrystalViewer3D from "@/components/CrystalViewer3D";

export default function CIFValidationPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sample CIF quick load helper
  const handleLoadSample = async () => {
    const sampleCif = `data_Si_cubic
_chemical_name_common 'Silicon'
_cell_length_a 5.4309
_cell_length_b 5.4309
_cell_length_c 5.4309
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0.0000 0.0000 0.0000
Si2 Si 0.2500 0.2500 0.2500
Si3 Si 0.5000 0.5000 0.0000
Si4 Si 0.7500 0.7500 0.2500
`;
    const blob = new Blob([sampleCif], { type: "chemical/x-cif" });
    const sampleFile = new File([blob], "sample_silicon.cif");
    setFile(sampleFile);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const res = await uploadCIF(file);
      setCandidate(res.candidate);
    } catch (err: any) {
      setError(err.message || "Failed to process CIF");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* Header */}
      <div className="border-b border-borderColor pb-5">
        <div className="flex items-center gap-2 text-xs font-semibold text-accentDark uppercase tracking-wider mb-1">
          <ShieldCheck className="w-4 h-4 text-accent" /> Crystallographic Utility
        </div>
        <h1 className="text-2xl font-bold text-primaryText tracking-tight">
          Upload & Validate Custom CIF
        </h1>
        <p className="text-xs sm:text-sm text-secondaryText mt-1 max-w-2xl leading-relaxed">
          Upload any inorganic crystallographic CIF file to test deterministic parsing, fractional coordinate wrapping, physical density, atomic overlap heuristics, and 3D WebGL rendering.
        </p>
      </div>

      {/* Upload Box */}
      <div className="scientific-card p-6 space-y-4">
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="border-2 border-dashed border-borderColor hover:border-accent/60 rounded-xl p-8 text-center bg-slate-50/50 transition">
            <Upload className="w-8 h-8 text-accent mx-auto mb-2" />
            <p className="text-xs text-primaryText font-semibold">
              Choose a .cif file to validate
            </p>
            <p className="text-[11px] text-secondaryText mt-0.5">
              Supports standard Crystallographic Information Files (CIF)
            </p>

            <input
              type="file"
              accept=".cif"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setFile(e.target.files[0]);
                }
              }}
              className="mt-4 block mx-auto text-xs text-secondaryText file:mr-4 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-accentDark hover:file:bg-emerald-100 cursor-pointer"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleLoadSample}
              className="text-xs text-accentDark hover:underline flex items-center gap-1 font-semibold"
            >
              <FileText className="w-3.5 h-3.5 text-accent" />
              <span>Load Sample Silicon CIF</span>
            </button>

            <button
              type="submit"
              disabled={!file || uploading}
              className="px-5 py-2 rounded-lg bg-accent hover:bg-accentDark text-white font-medium text-xs transition flex items-center gap-2 disabled:opacity-50 shadow-sm"
            >
              {uploading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Validating CIF...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Parse & Validate CIF</span>
                </>
              )}
            </button>
          </div>
        </form>

        {error && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Validation Error:</span> {error}
            </div>
          </div>
        )}
      </div>

      {/* Validation Result Display */}
      {candidate && (
        <div className="scientific-card p-6 space-y-6 animate-fadeIn">
          <div className="flex items-center justify-between border-b border-borderColor pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-primaryText">Parsed Formula: {candidate.reduced_formula}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                  candidate.validation.is_valid ? "bg-emerald-50 text-accentDark border border-accentBorder" : "bg-rose-50 text-rose-700 border border-rose-200"
                }`}>
                  {candidate.validation.status}
                </span>
              </div>
              <p className="text-xs text-secondaryText font-mono mt-0.5">
                {candidate.crystal_system} • {candidate.space_group} • ID: {candidate.candidate_id}
              </p>
            </div>

            <Link
              href={`/candidates/${candidate.candidate_id}`}
              className="px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-medium text-primaryText transition flex items-center gap-1.5 border border-borderColor"
            >
              <span>Full Inspection Page</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-7 h-[400px]">
              <CrystalViewer3D
                cifString={candidate.cif_string}
                formula={candidate.reduced_formula}
                spaceGroup={candidate.space_group}
                crystalSystem={candidate.crystal_system}
              />
            </div>

            <div className="lg:col-span-5 space-y-3">
              <h3 className="text-xs font-bold text-primaryText uppercase tracking-wider">
                Crystallographic Validation Report
              </h3>
              <div className="space-y-1.5 max-h-[340px] overflow-y-auto pr-1">
                {candidate.validation.checks.map((chk, i) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-50 border border-borderColor text-xs flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2">
                      {chk.passed ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0 mt-0.5" />
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
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
