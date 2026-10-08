import React, { useState } from "react";

const stateMeta = {
  NOT_CHECKED: ["NOT CHECKED", "text-slate-400", "border-slate-700 bg-slate-900/60"],
  SUPPORTS: ["SUPPORTS", "text-neon-green", "border-neon-green/30 bg-neon-green/5"],
  CONTRADICTS: ["CONTRADICTS", "text-neon-red", "border-neon-red/30 bg-neon-red/5"],
  INCONCLUSIVE: ["INCONCLUSIVE", "text-gold-neon", "border-gold-neon/30 bg-gold-neon/5"],
};

function StateBadge({ state }) {
  const [label, color, bg] = stateMeta[state] || stateMeta.INCONCLUSIVE;
  return <span className={`rounded-full border px-2 py-1 font-mono text-[9px] font-bold tracking-wider ${color} ${bg}`}>{label}</span>;
}

export default function CounterfactualVerification({ verification }) {
  const [showDetails, setShowDetails] = useState(false);
  if (!verification) return null;

  return (
    <section className="mt-3 rounded-xl border border-neon-green/25 bg-neon-green/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-neon-green">COUNTERFACTUAL VERIFICATION ENGINE</p>
          <h3 className="mt-1 text-base font-black text-slate-100">What would prove this claim is legitimate?</h3>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-muted">
            The engine defines independent evidence to look for. It does not contact the sender or open the suspicious destination.
          </p>
        </div>
        <div className="text-right">
          <StateBadge state={verification.overall_state} />
          <p className="mt-1 font-mono text-[8px] tracking-wider text-faint">HUMAN VERIFICATION REQUIRED</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.1fr_.9fr]">
        <div className="rounded-lg border border-slate-800 bg-space-950/70 p-3">
          <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-muted">CLAIM UNDER TEST</p>
          <p className="mt-2 text-sm font-semibold leading-relaxed text-slate-200">{verification.claim_under_test}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(verification.independent_sources || []).map((source) => (
              <span key={source} className="rounded-md border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] text-slate-400">{source}</span>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-space-950/70 p-3">
          <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-muted">EXPECTED IF LEGITIMATE</p>
          <ul className="mt-2 space-y-2 text-xs leading-relaxed text-slate-300">
            {(verification.expected_evidence || []).map((item, index) => (
              <li key={`${index}-${item}`} className="flex gap-2"><span className="font-mono font-bold text-neon-green">0{index + 1}</span><span>{item}</span></li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-slate-800 bg-space-950/70 p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-muted">EVIDENCE ACTUALLY FOUND</p>
          <button type="button" onClick={() => setShowDetails((v) => !v)} className="font-mono text-[9px] font-bold tracking-wider text-neon-cyan hover:underline">
            {showDetails ? "HIDE DETAILS" : "SHOW DETAILS"}
          </button>
        </div>
        <div className="mt-2 space-y-2">
          {(verification.findings || []).map((finding, index) => (
            <div key={`${finding.claim}-${index}`} className="rounded-md border border-slate-800 bg-slate-900/70 p-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-200">{finding.claim}</span>
                <StateBadge state={finding.state} />
              </div>
              <p className="mt-1 text-[10px] text-muted">Source: {finding.source}</p>
              {showDetails && <p className="mt-2 text-xs leading-relaxed text-slate-400">{(finding.actual_evidence || []).join(" ")}</p>}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg border border-gold-neon/25 bg-gold-neon/5 p-3">
          <p className="font-mono text-[9px] font-bold tracking-wider text-gold-neon">RISK IMPACT</p>
          <p className="mt-1 text-xs font-semibold text-slate-200">{verification.risk_impact}</p>
          <p className="mt-1 text-[10px] text-muted">Risk delta: {verification.risk_delta > 0 ? "+" : ""}{verification.risk_delta}. No automatic lowering from independent checks.</p>
        </div>
        <div className="rounded-lg border border-neon-cyan/25 bg-neon-cyan/5 p-3">
          <p className="font-mono text-[9px] font-bold tracking-wider text-neon-cyan">SAFE VERIFICATION</p>
          <ol className="mt-1 space-y-1 text-[10px] leading-relaxed text-slate-400">
            {(verification.safe_verification_action || []).map((step, index) => <li key={index}><span className="font-mono font-bold text-neon-cyan">{index + 1}.</span> {step}</li>)}
          </ol>
        </div>
      </div>

      <p className="mt-3 text-[10px] font-semibold text-neon-green/80">✓ {verification.safety_boundary}</p>
    </section>
  );
}
