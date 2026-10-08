import { useEffect, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { LangProvider, useLang } from "./lib/i18n.jsx";
import { OfflineBanner } from "./components/AsyncStates.jsx";
import InstallPrompt from "./components/InstallPrompt.jsx";
import Submit from "./pages/Submit.jsx";
import Review from "./pages/Review.jsx";
import ReportView from "./pages/ReportView.jsx";
import Coach from "./pages/Coach.jsx";
import Evaluation from "./pages/Evaluation.jsx";
import AppErrorBoundary from "./components/AppErrorBoundary.jsx";

function LangToggle() {
  const { lang, t, setLang } = useLang();
  return (
    <button
      type="button"
      onClick={() => setLang(lang === "en" ? "bm" : "en")}
      aria-label={lang === "en" ? "Switch to Bahasa Melayu" : "Tukar ke Bahasa Inggeris"}
      className="rounded-lg border border-neon-cyan/50 bg-neon-cyan/10 px-2.5 py-1.5 font-mono text-[11px] font-black tracking-wider text-neon-cyan transition hover:bg-neon-cyan/20"
    >
      🌐 {t("langButton")}
    </button>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-space-900/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="group flex items-center gap-3">
          <span className="relative grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-neon-cyan/40 bg-neon-cyan/10 font-mono text-lg font-black text-neon-cyan shadow-glow-cyan-soft">
            A
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-neon-green shadow-glow-green animate-pulse-glow" aria-hidden="true" />
          </span>
          <span className="animate-flicker">
            <span className="hero-title block text-lg font-black leading-tight tracking-[0.08em] sm:text-xl">
              TRUST//INTERCEPT
            </span>
            <span className="block font-mono text-[10px] tracking-[0.28em] text-muted">
              DECISION DEFENCE · MULTI-MODAL · HUMAN-GATED
            </span>
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <LangToggle />
          <InstallPrompt />
        </div>
      </div>
    </header>
  );
}

function OfflineWatcher() {
  const [offline, setOffline] = useState(
    () => typeof navigator !== "undefined" && navigator.onLine === false
  );

  useEffect(() => {
    const goOffline = () => setOffline(true);
    const goOnline = () => setOffline(false);
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  return offline ? <OfflineBanner /> : null;
}

function Shell() {
  const { t } = useLang();
  return (
    <BrowserRouter>
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[200] focus:rounded-lg focus:bg-space-950 focus:px-3 focus:py-2 focus:font-mono focus:text-xs focus:text-neon-cyan">
        {t("skipToContent")}
      </a>
      <div className="flex min-h-screen flex-col">
        <OfflineWatcher />
        <Header />

        <main id="main-content" tabIndex="-1" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 outline-none sm:px-6 sm:py-8 lg:px-8">
          <Routes>
            <Route path="/" element={<Submit />} />
            <Route path="/case/:caseId/review" element={<Review />} />
            <Route path="/case/:caseId/report" element={<ReportView />} />
            <Route path="/case/:caseId/coach" element={<Coach />} />
            <Route path="/evaluation" element={<Evaluation />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <footer className="border-t border-slate-800/80 bg-space-950/80 py-4 text-center font-mono text-[11px] tracking-wider text-muted">
          <span className="text-neon-cyan/80">TRUST//INTERCEPT v1.0</span> · TRUST//INTERCEPT investigates and explains; the
          person decides. Nothing is sent, blocked, or filed without your explicit approval.
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <AppErrorBoundary>
      <LangProvider>
        <Shell />
      </LangProvider>
    </AppErrorBoundary>
  );
}
