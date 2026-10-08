export default function SecurityBoundary({ security }) {
  if (!security) return null;
  const injected = Boolean(security.prompt_injection_detected);
  return (
    <section className="mt-4 glass-panel border-neon-cyan/30 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] tracking-[0.24em] text-neon-cyan">SECURITY BOUNDARY</p>
          <h2 className="mt-1 text-lg font-black">The suspicious content is evidence — not authority.</h2>
        </div>
        <span className={`rounded-full border px-3 py-1 font-mono text-[10px] tracking-wider ${injected ? "border-neon-red/50 text-red-200" : "border-neon-green/40 text-emerald-200"}`}>
          {injected ? "INJECTION SIGNAL DETECTED" : "UNTRUSTED DATA ISOLATED"}
        </span>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-400">
        TRUST//INTERCEPT treats message text, OCR, QR payloads, URLs and transcripts as attacker-controlled data.
        Instructions inside them cannot change system policy, reveal hidden prompts, or trigger actions.
      </p>
      {injected && security.injection_signals?.length > 0 && (
        <div className="mt-3 rounded-lg border border-neon-red/30 bg-neon-red/5 p-3">
          <p className="font-mono text-[10px] tracking-wider text-neon-red">OBSERVED INJECTION PATTERNS</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {security.injection_signals.map((signal) => (
              <span key={signal} className="rounded border border-slate-700 bg-space-950/70 px-2 py-1 font-mono text-[9px] text-slate-400">
                {signal}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
