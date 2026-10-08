import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client.js";
import { cx } from "../lib/ui";

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => { api.getEvaluation().then(setData).catch((e) => setError(e.message)); }, []);
  if (error) return <div className="glass-panel border-neon-red/40 p-5 text-red-200">Evaluation unavailable: {error}</div>;
  if (!data) return <div className="py-16 text-center font-mono text-xs tracking-[0.25em] text-neon-cyan animate-pulse-glow">RUNNING LOCAL EVALUATION LAB…</div>;
  const m = data.metrics;
  const c = data.confusion_matrix;
  const cards = [["ACCURACY", m.accuracy], ["PRECISION", m.precision], ["RECALL", m.recall], ["F1", m.f1], ["FALSE POSITIVE RATE", m.false_positive_rate]];
  return <div className="mx-auto max-w-6xl space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="font-mono text-[11px] tracking-[0.3em] text-neon-cyan">EVALUATION LAB</p><h1 className="mt-2 text-3xl font-black tracking-tight">Can the interceptor tell danger from normal?</h1><p className="mt-2 max-w-3xl text-sm text-slate-400">A local benchmark deliberately mixes scams, legitimate notices, borderline wording and adversarially safe language. No benchmark case is persisted and no suspicious link is opened.</p></div><Link to="/" className="font-mono text-xs tracking-wider text-neon-cyan hover:underline">← INTERCEPT</Link></div>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{cards.map(([label,value]) => <div key={label} className="glass-panel p-4"><p className="font-mono text-[10px] tracking-wider text-slate-500">{label}</p><p className="mt-2 text-2xl font-black">{(value*100).toFixed(1)}%</p></div>)}</div>
    <section className="glass-panel p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-mono text-sm tracking-[0.2em] text-neon-cyan">CONFUSION MATRIX</h2><span className="font-mono text-[10px] text-slate-500">{data.benchmark.cases} CASES · LOCAL / DETERMINISTIC-SAFE</span></div><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[["TRUE POSITIVE",c.true_positive,"Correct interception"],["TRUE NEGATIVE",c.true_negative,"Correctly left alone"],["FALSE POSITIVE",c.false_positive,"Legitimate/borderline flagged"],["FALSE NEGATIVE",c.false_negative,"Scam missed"]].map(([a,b,d])=><div key={a} className="rounded-lg border border-slate-800 bg-space-950/60 p-4"><p className="font-mono text-[10px] text-slate-500">{a}</p><p className="mt-2 text-3xl font-black">{b}</p><p className="mt-1 text-xs text-slate-400">{d}</p></div>)}</div></section>
    <section className="glass-panel overflow-hidden p-5"><h2 className="font-mono text-sm tracking-[0.2em] text-neon-cyan">CASE-BY-CASE EVIDENCE</h2><div className="mt-4 space-y-2">{data.results.map(r=><div key={r.id} className="grid gap-2 rounded-lg border border-slate-800 bg-space-950/50 p-3 sm:grid-cols-[1.2fr_.8fr_.8fr_.7fr] sm:items-center"><div><p className="text-sm font-semibold">{r.id}</p><p className="font-mono text-[10px] uppercase text-slate-500">{r.label}</p></div><span className="font-mono text-xs uppercase">{r.score} / {r.confidence}</span><span className="text-xs text-slate-400">{r.cue_count} cues · {r.evidence_count} evidence records</span><span className={cx("font-mono text-xs", r.correct ? "text-neon-green" : "text-neon-red")}>{r.correct ? "PASS" : "FAIL"}</span></div>)}</div></section>
    <div className="glass-panel border-gold-neon/20 p-4 text-xs text-slate-400">This benchmark is evidence, not a universal accuracy claim. Production evaluation should expand the dataset and include Malaysian-language and real-world samples with independently verified labels.</div>
  </div>;
}
