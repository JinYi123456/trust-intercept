import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import InstallPrompt from "./components/InstallPrompt.jsx";
import SelectionBadge from "./components/SelectionBadge.jsx";
import SocialThreatSimulator from "./components/SocialThreatSimulator.jsx";
import Submit from "./pages/Submit.jsx";
import Review from "./pages/Review.jsx";
import ReportView from "./pages/ReportView.jsx";
import Coach from "./pages/Coach.jsx";

function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-space-900/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="group flex items-center gap-3">
          <span className="relative grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-neon-cyan/40 bg-neon-cyan/10 font-mono text-lg font-black text-neon-cyan shadow-glow-cyan-soft">
            A
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-neon-green shadow-glow-green animate-pulse-glow" aria-label="Defence systems online" />
          </span>
          <span className="animate-flicker">
            <span className="hero-title block text-lg font-black leading-tight tracking-[0.08em] sm:text-xl">
              TRUST//INTERCEPT
            </span>
            <span className="block font-mono text-[10px] tracking-[0.28em] text-slate-500">
              DECISION DEFENCE · MULTI-MODAL · HUMAN-GATED
            </span>
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <SocialThreatSimulator />
          <InstallPrompt />
        </div>
        {/* In-app face of the browser-extension overlay: select text anywhere
            in the hub → floating "Analyze with TRUST//INTERCEPT" badge. */}
        <SelectionBadge />
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen flex-col">
        <Header />

        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
          <Routes>
            <Route path="/" element={<Submit />} />
            <Route path="/case/:caseId/review" element={<Review />} />
            <Route path="/case/:caseId/report" element={<ReportView />} />
            <Route path="/case/:caseId/coach" element={<Coach />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <footer className="border-t border-slate-800/80 bg-space-950/80 py-4 text-center font-mono text-[11px] tracking-wider text-slate-500">
          <span className="text-neon-cyan/80">TRUST//INTERCEPT v1.0</span> · TRUST//INTERCEPT investigates and explains; the
          person decides. Nothing is sent, blocked, or filed without your explicit approval.
        </footer>
      </div>
    </BrowserRouter>
  );
}
