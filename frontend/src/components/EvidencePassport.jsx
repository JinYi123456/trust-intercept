import { useEffect, useMemo, useState } from "react";

function short(value, left = 10, right = 8) {
  const text = String(value || "");
  if (text.length <= left + right + 3) return text;
  return `${text.slice(0, left)}…${text.slice(-right)}`;
}

export default function EvidencePassport({ caseInfo = {}, verdict = null, evidence = [] }) {
  const [hash, setHash] = useState("computing…");

  const tools = useMemo(
    () => evidence.map((entry) => entry.tool).filter(Boolean),
    [evidence]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const canonical = JSON.stringify({
          case_id: caseInfo.id || "",
          redacted_text: caseInfo.redacted_text || "",
          evidence: evidence.map((entry) => ({ tool: entry.tool, raw_output: entry.raw_output || {} })),
        });
        const digest = await crypto.subtle.digest(
          "SHA-256",
          new TextEncoder().encode(canonical)
        );
        const hex = Array.from(new Uint8Array(digest))
          .map((byte) => byte.toString(16).padStart(2, "0"))
          .join("");
        if (!cancelled) setHash(hex);
      } catch {
        if (!cancelled) setHash("unavailable-offline");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [caseInfo.id, caseInfo.redacted_text, evidence]);

  const piiProtected = Boolean(caseInfo.redacted_text);
  const decision = verdict?.score ? String(verdict.score).toUpperCase() : "PENDING";
  const confidence = verdict?.confidence ? String(verdict.confidence).toUpperCase() : "PENDING";

  return (
    <section className="glass-panel p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-black tracking-[0.24em] text-neon-cyan">EVIDENCE PASSPORT</p>
          <p className="mt-1 text-sm text-slate-400">
            A compact provenance record for this investigation. Original personal data is not included in the passport hash.
          </p>
        </div>
        <span className="rounded-full border border-neon-green/50 bg-neon-green/10 px-2.5 py-1 font-mono text-[10px] font-bold tracking-wider text-neon-green">
          {piiProtected ? "PII REDACTED" : "NO PII FIELD"}
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["CASE", short(caseInfo.id || "—", 12, 8)],
          ["DECISION", decision],
          ["CONFIDENCE", confidence],
          ["TOOLS", String(tools.length)],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-800 bg-space-950/70 p-3">
            <p className="font-mono text-[9px] font-bold tracking-[0.18em] text-faint">{label}</p>
            <p className="mt-1 break-all font-mono text-xs font-bold text-slate-200">{value}</p>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded-xl border border-slate-800 bg-space-950/70 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-mono text-[9px] font-bold tracking-[0.18em] text-faint">EVIDENCE HASH · SHA-256</span>
          <span className="break-all font-mono text-[10px] text-neon-cyan">{hash}</span>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-muted">
          The hash covers the redacted case view and captured evidence outputs so the investigation can be compared later without exposing the original message.
        </p>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {tools.map((tool, index) => (
          <span key={`${tool}-${index}`} className="rounded border border-slate-800 bg-space-950 px-2 py-1 font-mono text-[9px] text-muted">
            {tool}
          </span>
        ))}
      </div>
    </section>
  );
}
