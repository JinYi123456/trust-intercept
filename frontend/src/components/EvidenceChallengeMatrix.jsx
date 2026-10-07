import { useState } from "react";

function EvidenceRow({ side, argument, index }) {
  const red = side === "red";
  return (
    <article className={`rounded-lg border p-3 ${red ? "border-neon-red/20 bg-neon-red/5" : "border-neon-green/20 bg-neon-green/5"}`}>
      <div className="flex items-start gap-2">
        <span className={`grid h-5 w-5 shrink-0 place-items-center rounded font-mono text-[8px] font-bold ${red ? "bg-neon-red/15 text-neon-red" : "bg-neon-green/15 text-neon-green"}`}>{String(index + 1).padStart(2, "0")}</span>
        <div className="min-w-0">
          <p className="text-xs font-semibold leading-relaxed text-slate-200">{argument?.claim || "Unspecified argument"}</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <span className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wider text-slate-500">{argument?.technique || "evidence"}</span>
            <span className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wider text-slate-500">{argument?.strength || "unrated"}</span>
          </div>
          {argument?.evidence_quote && <p className="mt-2 border-l border-slate-700 pl-2 font-mono text-[9px] leading-relaxed text-slate-500">“{argument.evidence_quote}”</p>}
        </div>
      </div>
    </article>
  );
}

export default function EvidenceChallengeMatrix({ debate }) {
  const [side, setSide] = useState("red");
  const resolution = debate?.resolution || {};
  const matrix = resolution.challenge_matrix || {};
  const round = debate?.rounds?.[debate.rounds.length - 1] || {};
  const argumentsList = side === "red" ? (round.red?.arguments || []) : (round.blue?.arguments || []);
  const verifierTests = matrix.verifier_tests || round.verifier?.tests || [];
  const consensus = String(resolution.consensus || "contested").replaceAll("_", " ");

  if (!debate) return null;

  return (
    <section className="rounded-xl border border-slate-800 bg-space-950/70 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-slate-500">ADVERSARIAL EVIDENCE ARENA</p>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">The agents challenge the evidence, not each other for appearance. Every position must point to recorded evidence or an explicit verification test.</p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 font-mono text-[9px] font-bold uppercase tracking-wider ${consensus.includes("unanimous") ? "border-neon-green/30 bg-neon-green/5 text-neon-green" : "border-gold-neon/30 bg-gold-neon/5 text-gold-neon"}`}>STATUS: {consensus}</span>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-4">
        {[
          ["HUNTER EVIDENCE", matrix.red_evidence_count ?? round.red?.arguments?.length ?? 0],
          ["SKEPTIC EVIDENCE", matrix.blue_evidence_count ?? round.blue?.arguments?.length ?? 0],
          ["CONFLICTS", matrix.conflict_count ?? 0],
          ["JUDGE", resolution.judge_used ? "LLM" : "RULES"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/70 p-2.5">
            <p className="font-mono text-[8px] tracking-wider text-slate-500">{label}</p>
            <p className="mt-1 text-sm font-black uppercase text-slate-200">{value}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_1fr]">
        <div>
          <div className="mb-2 flex gap-1 rounded-lg border border-slate-800 bg-slate-900/60 p-1">
            {[['red', 'HUNTER — ATTACK CASE'], ['blue', 'SKEPTIC — BENIGN CASE']].map(([id, label]) => (
              <button key={id} type="button" onClick={() => setSide(id)} className={`flex-1 rounded-md px-2 py-2 font-mono text-[9px] font-bold tracking-wider transition ${side === id ? (id === 'red' ? 'bg-neon-red/10 text-neon-red ring-1 ring-neon-red/30' : 'bg-neon-green/10 text-neon-green ring-1 ring-neon-green/30') : 'text-slate-500 hover:text-slate-300'}`}>{label}</button>
            ))}
          </div>
          <div className="space-y-2">
            {argumentsList.slice(0, 6).map((argument, index) => <EvidenceRow key={`${side}-${index}`} side={side} argument={argument} index={index} />)}
            {!argumentsList.length && <p className="rounded-lg border border-slate-800 p-3 text-xs text-slate-500">No arguments were recorded for this side.</p>}
          </div>
        </div>

        <div className="space-y-3">
          <div className="rounded-lg border border-neon-cyan/20 bg-neon-cyan/5 p-3">
            <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-neon-cyan">VERIFIER — WHAT COULD CHANGE THE DECISION?</p>
            <div className="mt-2 space-y-2">
              {verifierTests.slice(0, 5).map((test, index) => <div key={index} className="flex gap-2 text-xs leading-relaxed text-slate-300"><span className="font-mono font-bold text-neon-cyan">0{index + 1}</span><span>{test}</span></div>)}
            </div>
          </div>
          <div className="rounded-lg border border-gold-neon/20 bg-gold-neon/5 p-3">
            <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-gold-neon">OVERTURN CONDITION</p>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">{matrix.overturn_condition || round.verifier?.overturn_condition || "Independent trusted evidence contradicts the suspicious request."}</p>
          </div>
          {matrix.shared_techniques?.length > 0 && (
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
              <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-slate-500">OVERLAPPING SIGNALS</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {matrix.shared_techniques.map((item) => <span key={item} className="rounded-full border border-slate-700 px-2 py-1 font-mono text-[8px] uppercase text-slate-400">{item.replaceAll('_', ' ')}</span>)}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
