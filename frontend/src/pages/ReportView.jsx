import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client.js";
import { InlineError, Loading, ErrorState } from "../components/AsyncStates.jsx";
import { useLang } from "../lib/i18n.jsx";
import { cx, formatDateTime } from "../lib/ui";

/**
 * ReportView — preview and download of the Module 3 redacted scam-report
 * bundle. TRUST//INTERCEPT prepares the report; the human sends it to the bank, telco,
 * or CISA-style portal.
 */
export default function ReportView() {
  const { caseId } = useParams();
  const [view, setView] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .getCase(caseId)
      .then((data) => {
        if (active) setView(data);
      })
      .catch((fetchError) => {
        if (active) setError(fetchError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  async function handleCopy() {
    if (!view?.report?.report_markdown) return;
    try {
      await navigator.clipboard.writeText(view.report.report_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (copyError) {
      setError("Copying to the clipboard failed — use the download button instead.");
    }
  }

  if (loading) return <Loading label="LOADING REPORT BUNDLE…" />;

  if (error && !view) {
    return (
      <ErrorState
        message={error}
        onRetry={() => window.location.reload()}
        backLink={
          <Link to="/" className="rounded-lg border border-slate-700 bg-space-900 px-4 py-2 text-sm font-bold text-slate-300 transition hover:text-neon-cyan">
            ← BACK TO SUBMISSION
          </Link>
        }
      />
    );
  }

  const report = view?.report;

  if (!report) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="glass-panel border-gold-neon/50 p-6 text-center">
          <p className="text-lg font-bold text-gold-neon">No report bundle generated yet</p>
          <p className="mt-2 text-sm text-slate-300">
            A redacted report is only created after you choose{" "}
            <strong className="text-white">&ldquo;Report This&rdquo;</strong> on the Review screen —
            that approval is the structural gate that lets TRUST//INTERCEPT prepare it.
          </p>
          <Link
            to={`/case/${caseId}/review`}
            className="gate-btn gate-warn mt-4 inline-block rounded-lg px-4 py-2 text-sm"
          >
            GO TO REVIEW
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="font-mono text-xl font-black uppercase tracking-[0.15em] text-slate-100 sm:text-2xl">
          REDACTED <span className="neon-cyan-text">REPORT BUNDLE</span>
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Case <span className="font-mono font-semibold text-neon-cyan">{caseId}</span> · ready to
          forward to your bank, telco, or national reporting portal.
        </p>
      </div>

      <div className="glass-panel border-neon-cyan/30 p-4 text-sm text-cyan-100">
        <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-neon-cyan">
          PRIVACY NOTE:{" "}
        </span>
        all personal identifiers (IC/NRIC, phone numbers, card numbers) were redacted{" "}
        <em>before</em> this report was assembled — TRUST//INTERCEPT never uploads your originals.{" "}
        <strong>TRUST//INTERCEPT prepares it; you send it.</strong>
      </div>

      <div className="mt-4 space-y-4">
        {/* Metadata */}
        <div className="grid grid-cols-1 gap-3 glass-panel p-4 sm:grid-cols-2">
          <div>
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">CHANNEL</p>
            <p className="mt-1 text-sm text-slate-200">{report.channel}</p>
          </div>
          <div>
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
              INCIDENT TIMESTAMP
            </p>
            <p className="mt-1 text-sm text-slate-200">{formatDateTime(report.incident_timestamp)}</p>
          </div>
          <div>
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
              EVIDENCE HASH
            </p>
            <p className="mt-1 break-url font-mono text-sm text-neon-green">{report.evidence_hash}</p>
          </div>
          <div>
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
              CUES DETECTED
            </p>
            <p className="mt-1 text-sm text-slate-200">
              {(report.cues_detected || []).length} flagged cue
              {(report.cues_detected || []).length === 1 ? "" : "s"}
            </p>
          </div>
        </div>

        {/* Summary */}
        <div className="glass-panel p-4">
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
            INCIDENT SUMMARY
          </p>
          <p className="mt-2 text-sm leading-relaxed text-slate-200">{report.summary}</p>
        </div>

        {/* Cues */}
        {report.cues_detected?.length > 0 && (
          <div className="glass-panel p-4">
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
              CUES DETECTED (QUOTED FROM THE REDACTED MESSAGE)
            </p>
            <ul className="mt-3 space-y-2">
              {report.cues_detected.map((cue, index) => (
                <li key={index} className="text-sm text-slate-300">
                  <span className="mr-2 rounded border border-neon-red/40 bg-neon-red/10 px-1.5 py-0.5 font-mono text-[11px] text-neon-red">
                    {cue.cue_type}
                  </span>
                  <span className="break-url">&ldquo;{cue.text}&rdquo;</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Redacted message */}
        <div className="glass-panel p-4">
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
            REDACTED MESSAGE
          </p>
          <pre className="mt-2 whitespace-pre-wrap break-url rounded-lg bg-space-950 p-3 font-mono text-xs leading-relaxed text-slate-300">
            {report.redacted_text}
          </pre>
        </div>

        {/* Full markdown preview */}
        <div className="glass-panel p-4">
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
            FULL REPORT (MARKDOWN)
          </p>
          <pre className="mt-2 max-h-96 overflow-y-auto whitespace-pre-wrap rounded-lg bg-space-950 p-4 font-mono text-xs leading-relaxed text-neon-cyan/90">
            {report.report_markdown}
          </pre>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        <a
          href={api.reportUrl(caseId)}
          download
          className="flex-1 rounded-xl border border-neon-cyan/60 bg-neon-cyan/15 px-4 py-3 text-center font-mono text-sm font-black tracking-wider text-neon-cyan shadow-glow-cyan-soft transition hover:bg-neon-cyan/25"
        >
          ⬇ DOWNLOAD REPORT (.MD)
        </a>
        <button
          type="button"
          onClick={handleCopy}
          className={cx(
            "flex-1 rounded-xl border px-4 py-3 font-mono text-sm font-black tracking-wider transition",
            copied
              ? "border-neon-green/60 bg-neon-green/15 text-neon-green"
              : "border-slate-700 bg-space-900/70 text-slate-300 hover:border-neon-cyan/40 hover:text-neon-cyan"
          )}
        >
          {copied ? "✓ COPIED!" : "COPY MARKDOWN TO CLIPBOARD"}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-4 font-mono text-xs tracking-wider">
        <Link to={`/case/${caseId}/review`} className="text-neon-cyan hover:underline">
          ← BACK TO REVIEW
        </Link>
        <Link to={`/case/${caseId}/coach`} className="text-neon-green hover:underline">
          TAKE THE AWARENESS QUIZ →
        </Link>
      </div>

      {error && <InlineError message={error} />}
    </div>
  );
}
