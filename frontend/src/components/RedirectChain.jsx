import { cx } from "../lib/ui";

/**
 * RedirectChain — visualises the hop-by-hop redirect chain for every URL in
 * the case (Module 2), with domain-age badges and reputation engine results.
 * Dark cyber styling: neon status chips, glowing age badges, timeline hops.
 */

function truncateUrl(url, max = 72) {
  const value = String(url || "");
  if (value.length <= max) return value;
  return `${value.slice(0, max - 12)}…${value.slice(-10)}`;
}

function domainAgeBadge(ageDays) {
  if (ageDays === null || ageDays === undefined) {
    return { label: "DOMAIN AGE UNKNOWN", className: "border-slate-700 bg-space-950 text-muted" };
  }
  if (ageDays < 30) {
    return {
      label: `REGISTERED ${ageDays} DAY${ageDays === 1 ? "" : "S"} AGO — BRAND-NEW DOMAIN`,
      className: "border-neon-red/60 bg-neon-red/10 text-neon-red shadow-glow-red-soft",
    };
  }
  if (ageDays < 180) {
    return {
      label: `REGISTERED ${ageDays} DAYS AGO — RELATIVELY NEW`,
      className: "border-gold-neon/60 bg-gold-neon/10 text-gold-neon shadow-glow-gold-soft",
    };
  }
  return {
    label: `ESTABLISHED DOMAIN (${ageDays} DAYS OLD)`,
    className: "border-neon-green/60 bg-neon-green/10 text-neon-green",
  };
}

function ReputationRow({ engine }) {
  if (!engine) return null;
  const state = !engine.checked
    ? { text: "NOT CHECKED", className: "border-slate-700 bg-space-950 text-muted" }
    : engine.malicious
    ? { text: "FLAGGED AS MALICIOUS", className: "border-neon-red/70 bg-neon-red/15 text-neon-red shadow-glow-red-soft" }
    : { text: "NO THREATS FOUND", className: "border-neon-green/60 bg-neon-green/10 text-neon-green" };

  return (
    <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] tracking-wide">
      <span className="font-bold text-slate-400">
        {engine.engine === "virustotal" ? "VIRUSTOTAL" : "GOOGLE SAFE BROWSING"}:
      </span>
      <span className={cx("rounded-full border px-2 py-0.5 font-bold", state.className)}>
        {state.text}
      </span>
      {engine.detail && <span className="text-muted">{engine.detail}</span>}
      {engine.unavailable_reason && (
        <span className="italic text-muted">{engine.unavailable_reason}</span>
      )}
    </div>
  );
}

export default function RedirectChain({ chains = [], domains = [] }) {
  if (!chains.length) return null;

  return (
    <div className="space-y-4">
      {chains.map((chain, chainIndex) => {
        const intel = domains[chainIndex];
        const age = intel ? intel.domain_age_days : null;
        const badge = domainAgeBadge(age);
        const hops = chain.hops || [];

        return (
          <div key={chainIndex} className="glass-panel p-4">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-black tracking-wider text-slate-300">
                REDIRECT CHAIN #{chainIndex + 1}
              </span>
              <span className={cx("rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-bold", badge.className)}>
                {badge.label}
              </span>
            </div>

            {hops.length === 0 && chain.error && (
              <p className="rounded-lg border border-slate-800 bg-space-950 p-3 font-mono text-xs text-slate-400">
                {chain.error}
              </p>
            )}

            {hops.length > 0 && (
              <ol className="relative space-y-3 border-l border-dashed border-neon-cyan/30 pl-5">
                {hops.map((hop, hopIndex) => (
                  <li key={hopIndex} className="relative">
                    <span
                      className={cx(
                        "absolute -left-[27px] top-1 grid h-4 w-4 place-items-center rounded-full border font-mono text-[8px] font-bold",
                        hopIndex === hops.length - 1
                          ? "border-neon-red/60 bg-neon-red/15 text-neon-red"
                          : "border-neon-cyan/60 bg-neon-cyan/15 text-neon-cyan"
                      )}
                    >
                      {hopIndex + 1}
                    </span>
                    <div
                      title={hop.url}
                      className="break-url block text-sm font-medium text-neon-cyan"
                    >
                      {truncateUrl(hop.url)}
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted">
                      {hop.status_code && (
                        <span
                          className={cx(
                            "rounded border px-1.5 py-0.5 font-bold",
                            hop.status_code < 300
                              ? "border-neon-green/50 bg-neon-green/10 text-neon-green"
                              : "border-gold-neon/50 bg-gold-neon/10 text-gold-neon"
                          )}
                        >
                          HTTP {hop.status_code}
                        </span>
                      )}
                      {hop.location && (
                        <span className="break-url">
                          redirects to: <span className="text-slate-400">{truncateUrl(hop.location, 56)}</span>
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            )}

            {chain.final_url && hops.length > 1 && (
              <p className="mt-3 break-url rounded-lg border border-neon-red/40 bg-neon-red/10 p-3 text-sm text-red-200">
                <span className="font-mono text-[10px] font-bold tracking-wider text-neon-red">
                  FINAL LANDING DESTINATION:{" "}
                </span>
                <span className="font-semibold">{chain.final_url}</span>
              </p>
            )}

            {(chain.loop_detected || chain.truncated) && (
              <p className="mt-2 rounded-lg border border-gold-neon/40 bg-gold-neon/10 p-3 text-sm text-amber-200">
                {chain.loop_detected && "A redirect loop was detected. "}
                {chain.truncated && `The chain was truncated at the ${hops.length}-hop safety cap.`}
              </p>
            )}

            {intel && (
              <div className="mt-3 space-y-1.5 border-t border-slate-800 pt-3">
                <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] tracking-wide">
                  <span className="font-bold text-slate-400">DOMAIN:</span>
                  <span className="break-url text-neon-cyan">{intel.domain}</span>
                  {intel.created_at && (
                    <span className="text-muted">(registered {intel.created_at})</span>
                  )}
                  {intel.lookup_source && (
                    <span className="rounded border border-slate-700 bg-space-950 px-1.5 py-0.5 text-slate-400">
                      via {intel.lookup_source}
                    </span>
                  )}
                </div>
                {(intel.reputation || []).map((engine, engineIndex) => (
                  <ReputationRow key={engineIndex} engine={engine} />
                ))}
                {(intel.notes || []).map((note, noteIndex) => (
                  <p key={noteIndex} className="text-xs italic text-muted">
                    {note}
                  </p>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
