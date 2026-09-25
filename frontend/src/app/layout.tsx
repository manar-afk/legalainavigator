import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Legal Information Navigator',
  description: 'GenAI-powered legal information and situation-aware document navigation.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 flex flex-col">
        {/* Top Ethical & Regulatory Disclaimer Banner */}
        <div className="bg-slate-900 text-slate-300 text-xs py-2 px-4 border-b border-slate-800">
          <div className="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-2">
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="font-medium text-slate-200">Legal Information Tool:</span>
              <span>This system provides grounded information & document navigation. It does not provide legal representation or guaranteed advice.</span>
            </div>
            <span className="text-slate-400">Knowledge Hierarchy: User Documents → Stated Facts → Authoritative Law</span>
          </div>
        </div>

        {/* Global Navigation Header */}
        <header className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-legalNavy-800 text-white flex items-center justify-center font-bold text-xl shadow-inner">
                §
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-tight">
                  Legal Information Navigator
                </h1>
                <p className="text-xs text-slate-500 font-medium">
                  Situation-Aware & Grounded GenAI Assistant
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 font-medium border border-emerald-200 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Production System Active
              </span>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4">
            Legal Information Navigator · Built with Google Cloud GenAI & Vertex AI · Grounded in Evidence
          </div>
        </footer>
      </body>
    </html>
  );
}
