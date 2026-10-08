import { useEffect, useState } from "react";
import { ACTION_LABELS, cx, formatDateTime } from "../lib/ui";

/**
 * AuditLog — client-side audit-trail dashboard.
 *
 * For every human decision it shows: the frozen verdict snapshot that existed
 * at approval time, the decision timestamp, the risk delta between the
 * snapshot and the latest verdict, and a SHA-256 verification hash computed
 * CLIENT-SIDE (Web Crypto API) over the immutable decision record — so the
 * hash covers exactly what the user saw, independent of the backend.
 */

function scoreLabel(score) {
  return String(score || "?").toUpperCase();
}

function riskDeltaClass(delta) {
  if (delta === "raised") return "border-neon-red/60 bg-neon-red/10 text-neon-red";
  if (delta === "lowered") return "border-neon-green/60 bg-neon-green/10 text-neon-green";
  return "border-slate-700 bg-space-950 text-slate-400";
}

const RISK_RANK = { low: 0, medium: 1, high: 2 };

async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function DecisionRow({ decision, currentScore }) {
  const [hash, setHash] = useState("computing…");
  const [copied, setCopied] = useState(false);

  const payloadForHash = JSON.stringify({
    id: decision.id,
    case_id: decision.case_id,
    human_action: decision.human_action,
    action_taken: decision.action_taken,
    verdict_snapshot: decision.verdict_snapshot,
    correction: decision.correction,
    decided_by: decision.decided_by,
    decided_at: decision.decided_at,
  });

  useEffect(() => {
    let active = true;
    sha256Hex(payloadForHash).then((value) => {
      if (active) setHash(value);
    });
    return () => {
      active = false;
    };
  }, [payloadForHash]);

  const snapshotScore = decision.verdict_snapshot?.score;
  let delta = "unchanged";
  let deltaText = `${scoreLabel(snapshotScore)} → ${scoreLabel(currentScore)} · no change since approval`;
  if (currentScore && snapshotScore && currentScore !== snapshotScore) {
    delta = RISK_RANK[currentScore] > RISK_RANK[snapshotScore] ? "raised" : "lowered";
    deltaText = `Snapshot ${scoreLabel(snapshotScore)} → latest verdict ${scoreLabel(currentScore)} after a later re-check`;
  }

  async function copyHash() {
    try {
      await navigator.clipboard.writeText(hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (copyError) {
      // Clipboard unavailable — the full hash remains visible in the row.
    }
  }

  const cueCount = decision.verdict_snapshot?.cues?.length ?? 0;

  return (
    <li className="glass-panel p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded bg-neon-cyan/15 px-2 py-0.5 font-mono text-xs font-bold text-neon-cyan">
          {ACTION_LABELS[decision.human_action] || decision.human_action}
        </span>
        <span className={cx("rounded-full border px-2 py-0.5 font-mono text-[11px]", riskDeltaClass(delta))}>
          {deltaText}
        </span>
        <span className="ml-auto font-mono text-[11px] text-muted">{formatDateTime(decision.decided_at)}</span>
      </div>

      <p className="mt-2 text-sm text-slate-300">{decision.action_taken}</p>

      <div className="mt-3 grid grid-cols-1 gap-2 rounded-lg bg-space-950/70 p-3 font-mono text-[11px] text-slate-400 sm:grid-cols-3">
        <div>
          <span className="block font-bold uppercase tracking-wider text-muted">Approved by</span>
          {decision.decided_by}
        </div>
        <div>
          <span className="block font-bold uppercase tracking-wider text-muted">Evidence snapshot</span>
          {cueCount} cue{cueCount === 1 ? "" : "s"} in frozen verdict
        </div>
        <div>
          <span className="block font-bold uppercase tracking-wider text-muted">Snapshot confidence</span>
          {decision.verdict_snapshot?.confidence || "—"}
        </div>
      </div>

      {decision.correction && (
        <p className="mt-2 rounded border border-gold-neon/40 bg-gold-neon/10 p-2 font-mono text-[11px] italic text-amber-200">
          Correction noted (PII redacted): “{decision.correction}”
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] font-bold tracking-wider text-muted">
          VERIFICATION HASH (SHA-256, CLIENT-SIDE):
        </span>
        <code className="break-all rounded bg-space-950 px-2 py-1 font-mono text-[11px] text-neon-green">
          {hash}
        </code>
        <button
          type="button"
          onClick={copyHash}
          className="rounded px-2 py-1 font-mono text-[11px] text-neon-cyan hover:bg-neon-cyan/10"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
    </li>
  );
}

export default function AuditLog({ view }) {
  const decisions = view?.decisions || [];
  const evidenceCount = view?.evidence?.length || 0;
  const currentScore = view?.verdict?.score;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          { label: "Decisions recorded", value: decisions.length },
          { label: "Evidence entries", value: evidenceCount },
          { label: "Report bundle", value: view?.report ? "Generated" : "None" },
          { label: "Quiz artifact", value: view?.quiz ? "Generated" : "None" },
        ].map((stat) => (
          <div key={stat.label} className="glass-panel p-3 text-center">
            <p className="text-lg font-black text-neon-cyan">{stat.value}</p>
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted">{stat.label}</p>
          </div>
        ))}
      </div>

      {decisions.length === 0 ? (
        <div className="glass-panel p-6 text-center text-sm text-slate-400">
          No decisions have been recorded yet. Every approval you make on the Review tab will
          appear here with a tamper-evident, client-side verification hash.
        </div>
      ) : (
        <>
          <p className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/5 p-3 font-mono text-[11px] text-cyan-100">
            COMPLIANCE NOTE: each row hashes the exact decision record (including the frozen
            verdict snapshot) with SHA-256 <em>in your browser</em>. If the stored record ever
            changed, re-hashing it would no longer match the hash you copied.
          </p>
          <ul className="space-y-3">
            {decisions.map((decision) => (
              <DecisionRow
                key={decision.id || decision.decided_at}
                decision={decision}
                currentScore={currentScore}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
