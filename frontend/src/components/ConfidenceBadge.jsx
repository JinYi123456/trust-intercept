import { cx, SCORE_LABELS, scoreBadgeClass } from "../lib/ui";

/**
 * ConfidenceBadge — compact neon readout of the verdict's risk score AND its
 * confidence band. Never a false binary. (The large ThreatGauge handles the
 * hero presentation on the Review screen; this chip is used inline.)
 */

const NEON = {
  high: "bg-neon-red/10 text-neon-red ring-neon-red/40 shadow-glow-red",
  medium: "bg-neon-gold/10 text-neon-gold ring-neon-gold/40 shadow-glow-gold",
  low: "bg-neon-green/10 text-neon-green ring-neon-green/40 shadow-glow-green",
};

export default function ConfidenceBadge({ score, confidence, actionRequired }) {
  const scoreKey = String(score || "").toLowerCase();
  const confidenceKey = String(confidence || "").toLowerCase();

  return (
    <div className="flex flex-wrap items-center gap-2 font-mono">
      <span
        className={cx(
          "inline-flex items-center rounded-full px-3 py-1 text-sm font-bold tracking-widest ring-1",
          NEON[scoreKey] || "bg-slate-800/60 text-slate-300 ring-slate-600"
        )}
      >
        {SCORE_LABELS[scoreKey] || "UNRATED"}
      </span>

      <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-xs font-semibold tracking-widest text-slate-300">
        CONF <span className="ml-1.5 text-neon-cyan">{confidenceKey ? confidenceKey.toUpperCase() : "PENDING"}</span>
      </span>

      {actionRequired && (
        <span className="inline-flex items-center rounded-full border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-1 text-xs font-semibold tracking-widest text-neon-cyan">
          ACTION REQUIRED
        </span>
      )}
    </div>
  );
}
