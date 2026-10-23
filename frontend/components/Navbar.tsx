"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { 
  Atom, 
  Sparkles, 
  Database, 
  Info,
  Github,
  AlertCircle,
  Cpu,
  CheckCircle2,
  Menu,
  X,
  ShieldCheck
} from "lucide-react";
import { getHealth } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const [matterGenActive, setMatterGenActive] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    getHealth()
      .then((data) => setMatterGenActive(data.mattergen_available))
      .catch(() => setMatterGenActive(false));
  }, []);

  const navLinks = [
    { href: "/discover", label: "Discover", icon: Sparkles },
    { href: "/candidates", label: "Materials", icon: Atom },
    { href: "/scientific-validation", label: "RAG Validation", icon: ShieldCheck },
    { href: "/datasets", label: "Dataset", icon: Database },
    { href: "/#about", label: "About", icon: Info },
  ];

  return (
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-50">
      {/* Top Scientific Notice Strip */}
      <div className="bg-slate-50 border-b border-slate-200 px-4 py-1.5 text-[11px] text-slate-600">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 truncate">
            <AlertCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate">
              <strong className="font-semibold text-slate-700">Computational Research Platform:</strong> AI-generated candidates are computational proposals requiring DFT and experimental synthesis validation.
            </span>
          </div>
          <div className="hidden md:flex items-center gap-4 text-slate-500 font-mono text-[10px] shrink-0">
            <span>Hull Screening: ≤ 0.05 eV/atom</span>
            <span>•</span>
            <span>Reference: MP-20 / JARVIS-DFT</span>
          </div>
        </div>
      </div>

      {/* Main Navbar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center text-white shadow-sm group-hover:bg-emerald-600 transition-colors">
              <Atom className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold tracking-tight text-slate-900">CRYSTAL-X</span>
                <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Research
                </span>
              </div>
            </div>
          </Link>

          {/* Navigation Links: Logo | Discover | Materials | Dataset | About | GitHub */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href || (link.href !== "/" && link.href !== "/#about" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.label}
                  href={link.href}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "text-emerald-700 bg-emerald-50 font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}

            {/* Secondary Utility Links */}
            <Link
              href="/dft-queue"
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                pathname === "/dft-queue"
                  ? "text-emerald-700 bg-emerald-50 font-semibold"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              DFT Queue
            </Link>
            <Link
              href="/validation"
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                pathname === "/validation"
                  ? "text-emerald-700 bg-emerald-50 font-semibold"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              CIF Verify
            </Link>

            {/* GitHub Link */}
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="ml-2 p-2 text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-50 transition-colors"
              title="GitHub Repository"
            >
              <Github className="w-4 h-4" />
            </a>
          </nav>

          {/* Generator Status Badge */}
          <div className="flex items-center gap-2">
            {matterGenActive ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200 text-[11px] font-medium text-emerald-800">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="font-mono text-[10px]">REAL_GENERATOR: MatterGen</span>
              </div>
            ) : (
              <div 
                title="Demo generation mode active. Output is synthetic surrogate prototype."
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200 text-[11px] font-medium text-slate-600 cursor-help"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span className="font-mono text-[10px]">DEMO_GENERATOR ACTIVE</span>
              </div>
            )}

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-md"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-1">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              {link.label}
            </Link>
          ))}
          <Link
            href="/dft-queue"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            DFT Queue
          </Link>
          <Link
            href="/validation"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            CIF Verification
          </Link>
        </div>
      )}
    </header>
  );
}
