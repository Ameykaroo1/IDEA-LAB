"use client";

import { useEffect, useRef, useState } from "react";
import { 
  RotateCcw, 
  Box, 
  Tag, 
  Layers, 
  Info,
  Check,
  Play,
  Pause
} from "lucide-react";

interface CrystalViewer3DProps {
  cifString: string;
  formula: string;
  spaceGroup?: string;
  crystalSystem?: string;
  autoSpin?: boolean;
}

declare global {
  interface Window {
    $3Dmol: any;
  }
}

export default function CrystalViewer3D({
  cifString,
  formula,
  spaceGroup,
  crystalSystem,
  autoSpin = true
}: CrystalViewer3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);

  const [isScriptLoaded, setIsScriptLoaded] = useState(false);
  const [showUnitCell, setShowUnitCell] = useState(true);
  const [showLabels, setShowLabels] = useState(false);
  const [isSpinning, setIsSpinning] = useState(autoSpin);
  const [renderStyle, setRenderStyle] = useState<"ballAndStick" | "spacefill" | "wireframe">("ballAndStick");
  const [copySuccess, setCopySuccess] = useState(false);

  // Load 3Dmol script dynamically if not present
  useEffect(() => {
    if (window.$3Dmol) {
      setIsScriptLoaded(true);
      return;
    }

    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.4.2/3Dmol-min.js";
    script.async = true;
    script.onload = () => {
      setIsScriptLoaded(true);
    };
    document.head.appendChild(script);
  }, []);

  // Initialize and update 3D viewer
  useEffect(() => {
    if (!isScriptLoaded || !containerRef.current || !cifString) return;

    try {
      containerRef.current.innerHTML = "";
      
      // Crisp white background for publication aesthetic
      const config = { backgroundColor: "#FFFFFF" };
      const viewer = window.$3Dmol.createViewer(containerRef.current, config);
      viewerRef.current = viewer;

      // Add actual CIF model
      viewer.addModel(cifString, "cif");

      // Apply initial style
      applyViewerStyle(viewer, renderStyle, showUnitCell, showLabels);

      viewer.zoomTo();
      viewer.render();

      if (isSpinning) {
        viewer.spin("y", 0.35);
      }
    } catch (err) {
      console.error("Failed to render crystal structure in 3Dmol:", err);
    }
  }, [isScriptLoaded, cifString]);

  // Handle style or toggle changes without full reload
  const applyViewerStyle = (
    viewer: any,
    style: "ballAndStick" | "spacefill" | "wireframe",
    unitCell: boolean,
    labels: boolean
  ) => {
    if (!viewer) return;

    viewer.removeAllLabels();

    if (style === "ballAndStick") {
      viewer.setStyle({}, { 
        sphere: { radius: 0.42, scale: 0.8 }, 
        stick: { radius: 0.12, colorscheme: "Jmol" } 
      });
    } else if (style === "spacefill") {
      viewer.setStyle({}, { sphere: { scale: 0.90, colorscheme: "Jmol" } });
    } else if (style === "wireframe") {
      viewer.setStyle({}, { line: { linewidth: 1.5, colorscheme: "Jmol" } });
    }

    if (unitCell) {
      viewer.addUnitCell();
    }

    if (labels) {
      const atoms = viewer.selectedAtoms({});
      atoms.forEach((atom: any) => {
        viewer.addLabel(atom.elem || "", {
          position: { x: atom.x, y: atom.y, z: atom.z },
          backgroundColor: "#FFFFFF",
          fontColor: "#0F172A",
          fontSize: 10,
          backgroundOpacity: 0.85,
          borderColor: "#E2E8F0",
          borderThickness: 1
        });
      });
    }

    viewer.render();
  };

  const handleStyleChange = (newStyle: "ballAndStick" | "spacefill" | "wireframe") => {
    setRenderStyle(newStyle);
    if (viewerRef.current) {
      applyViewerStyle(viewerRef.current, newStyle, showUnitCell, showLabels);
    }
  };

  const toggleUnitCell = () => {
    const next = !showUnitCell;
    setShowUnitCell(next);
    if (viewerRef.current) {
      applyViewerStyle(viewerRef.current, renderStyle, next, showLabels);
    }
  };

  const toggleLabels = () => {
    const next = !showLabels;
    setShowLabels(next);
    if (viewerRef.current) {
      applyViewerStyle(viewerRef.current, renderStyle, showUnitCell, next);
    }
  };

  const toggleSpin = () => {
    const next = !isSpinning;
    setIsSpinning(next);
    if (viewerRef.current) {
      if (next) {
        viewerRef.current.spin("y", 0.35);
      } else {
        viewerRef.current.spin(false);
      }
    }
  };

  const resetCamera = () => {
    if (viewerRef.current) {
      viewerRef.current.zoomTo();
      viewerRef.current.render();
    }
  };

  const copyCif = () => {
    navigator.clipboard.writeText(cifString);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  return (
    <div className="flex flex-col h-full rounded-xl overflow-hidden bg-white border border-slate-200 shadow-sm">
      {/* Viewer Header */}
      <div className="px-4 py-3 bg-white border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <h3 className="text-sm font-semibold text-slate-900 tracking-tight">
            {formula} <span className="text-slate-500 font-mono text-xs font-normal">({spaceGroup || "P1"})</span>
          </h3>
          {crystalSystem && (
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
              {crystalSystem}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={copyCif}
            className="px-2.5 py-1 rounded text-xs text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 transition-colors flex items-center gap-1.5"
            title="Copy CIF content"
          >
            {copySuccess ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Layers className="w-3.5 h-3.5" />}
            <span>{copySuccess ? "Copied" : "Copy CIF"}</span>
          </button>
        </div>
      </div>

      {/* 3D WebGL Canvas Container */}
      <div className="relative flex-1 w-full min-h-[380px] bg-white">
        {!isScriptLoaded && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-xs gap-2">
            <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            Initializing WebGL 3Dmol Renderer...
          </div>
        )}
        <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* Floating Interactive Controls */}
        <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between pointer-events-none">
          {/* Style Toggles */}
          <div className="flex items-center gap-1 p-1 bg-white/95 backdrop-blur-sm rounded-lg border border-slate-200 pointer-events-auto shadow-sm">
            <button
              onClick={() => handleStyleChange("ballAndStick")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                renderStyle === "ballAndStick"
                  ? "bg-slate-900 text-white font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              Ball & Stick
            </button>
            <button
              onClick={() => handleStyleChange("spacefill")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                renderStyle === "spacefill"
                  ? "bg-slate-900 text-white font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              Spacefill
            </button>
            <button
              onClick={() => handleStyleChange("wireframe")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                renderStyle === "wireframe"
                  ? "bg-slate-900 text-white font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              Wireframe
            </button>
          </div>

          {/* View Helpers */}
          <div className="flex items-center gap-1 p-1 bg-white/95 backdrop-blur-sm rounded-lg border border-slate-200 pointer-events-auto shadow-sm">
            <button
              onClick={toggleSpin}
              title={isSpinning ? "Pause Slow Rotation" : "Start Slow Rotation"}
              className={`p-1.5 rounded text-xs transition-colors flex items-center gap-1 ${
                isSpinning ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              {isSpinning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={toggleUnitCell}
              title="Toggle Unit Cell Box"
              className={`p-1.5 rounded text-xs transition-colors flex items-center gap-1 ${
                showUnitCell ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              <span className="hidden sm:inline text-[11px]">Cell</span>
            </button>

            <button
              onClick={toggleLabels}
              title="Toggle Chemical Element Labels"
              className={`p-1.5 rounded text-xs transition-colors flex items-center gap-1 ${
                showLabels ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <Tag className="w-3.5 h-3.5" />
              <span className="hidden sm:inline text-[11px]">Labels</span>
            </button>

            <button
              onClick={resetCamera}
              title="Reset Camera View"
              className="p-1.5 rounded text-xs text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Helper Footer */}
      <div className="px-4 py-2 bg-slate-50 text-[11px] text-slate-500 border-t border-slate-200 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-slate-400" />
          Left click: rotate • Right click: pan • Scroll: zoom
        </span>
        <span className="font-mono text-slate-400 text-[10px]">Crystallographic 3Dmol.js</span>
      </div>
    </div>
  );
}
