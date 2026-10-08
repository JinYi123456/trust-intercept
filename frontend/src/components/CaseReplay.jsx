import { useMemo, useState } from "react";

const stageLabels = {
  INTAKE: "INTAKE",
  NORMALISATION: "NORMALISE",
  ROUTING: "ROUTE",
  "TOOL INVESTIGATION": "INVESTIGATE",
  "AGENT INVESTIGATION": "AGENT",
  "DECISION SYNTHESIS": "SYNTHESIS",
  "HUMAN APPROVAL": "HUMAN",
};

export default function CaseReplay({ provenance }) {
  const [selected, setSelected] = useState(null);
  const steps = provenance?.steps || [];
  const groups = useMemo(() => {
    const map = new Map();
    steps.forEach((step) => {
      if (!map.has(step.stage)) map.set(step.stage, []);
      map.get(step.stage).push(step);
    });
    return Array.from(map.entries());
  }, [steps]);

  if (!provenance) return null;

  return (
    <section className="glass-panel mt-4 border-neon-cyan/25 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-black tracking-[0.24em] text-neon-cyan">CASE REPLAY / PROVENANCE</p>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-slate-400">
            A deterministic replay of the persisted investigation. It shows what happened and where evidence came from — without opening links or re-running external tools.
          </p>
        </div>
        <span className="rounded-full border border-neon-green/40 bg-neon-green/10 px-2.5 py-1 font-mono text-[9px] font-bold tracking-wider text-neon-green">
          {provenance.replayable ? "REPLAYABLE" : "SNAPSHOT"}
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["STEPS", provenance.step_count],
          ["EVIDENCE", provenance.evidence_count],
          ["VERDICTS", provenance.verdict_count],
          ["DECISIONS", provenance.decision_count],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-800 bg-space-950/70 p-3">
            <p className="font-mono text-[9px] font-bold tracking-[0.18em] text-slate-600">{label}</p>
            <p className="mt-1 font-mono text-xl font-black text-slate-100">{value}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-slate-800 bg-space-950/70 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-mono text-[9px] font-bold tracking-[0.18em] text-slate-600">MANIFEST INTEGRITY · SHA-256</span>
          <span className="break-all font-mono text-[10px] text-neon-cyan">{provenance.integrity_hash}</span>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {groups.map(([stage, items]) => (
          <div key={stage} className="overflow-hidden rounded-xl border border-slate-800 bg-space-950/60">
            <div className="border-b border-slate-800 px-3 py-2 font-mono text-[9px] font-black tracking-[0.18em] text-slate-500">
              {stageLabels[stage] || stage}
            </div>
            {items.map((step) => (
              <button
                key={`${step.sequence}-${step.event}`}
                type="button"
                onClick={() => setSelected(selected?.sequence === step.sequence ? null : step)}
                className="flex w-full items-center gap-3 border-b border-slate-900 px-3 py-3 text-left transition hover:bg-slate-900/60 last:border-b-0"
              >
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-slate-700 font-mono text-[9px] font-bold text-neon-cyan">
                  {String(step.sequence).padStart(2, "0")}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-mono text-[10px] font-bold uppercase tracking-wider text-slate-200">{step.event}</span>
                  <span className="mt-0.5 block text-[10px] text-slate-600">actor: {step.actor}</span>
                </span>
                <span className="font-mono text-[9px] text-neon-green">✓</span>
              </button>
            ))}
          </div>
        ))}
      </div>

      {selected && (
        <div className="mt-3 rounded-xl border border-neon-cyan/25 bg-neon-cyan/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-mono text-[10px] font-black tracking-[0.18em] text-neon-cyan">STEP {selected.sequence} · {selected.event}</p>
            <span className="font-mono text-[9px] text-slate-500">{selected.actor}</span>
          </div>
          <pre className="mt-3 max-h-52 overflow-auto whitespace-pre-wrap break-words font-mono text-[10px] leading-relaxed text-slate-400">
            {JSON.stringify(selected.details || {}, null, 2)}
          </pre>
          {selected.evidence_fingerprint && (
            <p className="mt-3 break-all font-mono text-[9px] text-slate-600">evidence fingerprint: {selected.evidence_fingerprint}</p>
          )}
        </div>
      )}

      <p className="mt-3 text-[10px] leading-relaxed text-slate-600">{provenance.safety_boundary}</p>
    </section>
  );
}
