/** Shared UI helpers used across TRUST//INTERCEPT components and pages. */

export function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

/** Verdict scores are always Low/Medium/High — never a bare true/false. */
export const SCORE_LABELS = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

export function scoreBadgeClass(score) {
  switch (String(score || "").toLowerCase()) {
    case "high":
      return "border-neon-red/60 bg-neon-red/10 text-neon-red shadow-glow-red-soft";
    case "medium":
      return "border-gold-neon/60 bg-gold-neon/10 text-gold-neon shadow-glow-gold-soft";
    case "low":
      return "border-neon-green/60 bg-neon-green/10 text-neon-green";
    default:
      return "border-slate-700 bg-space-950 text-slate-400";
  }
}

export function severityDotClass(severity) {
  switch (String(severity || "").toLowerCase()) {
    case "high":
      return "bg-neon-red shadow-glow-red-soft";
    case "medium":
      return "bg-gold-neon shadow-glow-gold-soft";
    case "low":
      return "bg-neon-green";
    default:
      return "bg-slate-500";
  }
}

export function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Human labels for the four gate actions (see routers/review.py). */
export const ACTION_LABELS = {
  looks_safe: "Looks Safe",
  report: "Report This",
  block_warn: "Block / Warn",
  disagree_recheck: "I Disagree, Re-check",
};
