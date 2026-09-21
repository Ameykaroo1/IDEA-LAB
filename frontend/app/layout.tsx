import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata = {
  title: "CRYSTAL-X | AI-Based Novel Crystal Material Discovery",
  description: "Generative AI-Based Novel Crystal Material Discovery for Advanced Energy Applications",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#F8FAFC] text-slate-900 min-h-screen flex flex-col antialiased selection:bg-emerald-100 selection:text-emerald-900">
        <Navbar />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white py-8 text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-800 tracking-wider text-xs">CRYSTAL-X</span>
              <span className="text-slate-300">|</span>
              <span>Computational Materials Informatics Research</span>
            </div>
            <p className="text-slate-500 text-center sm:text-right max-w-xl text-[11px] leading-relaxed">
              AI-generated candidates are computational proposals. Structural validity and ML predictions do not constitute proof of thermodynamic stability or synthesizability. Downstream DFT and experimental validation required.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
