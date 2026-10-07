import { useMemo, useState } from "react";

const KIND_LABELS = {
  source: "SOURCE MESSAGE",
  manipulation: "MANIPULATION TACTIC",
  requested_action: "REQUESTED ACTION",
};

const NODE_GUIDANCE = {
  message: {
    title: "Start with the claim, not the sender's pressure",
    action: "Verify the claim through a channel you already trust.",
  },
  authority: {
    title: "Borrowed authority can make a false request feel official",
    action: "Contact the organisation using its official app, a saved number, or a website you type yourself.",
  },
  urgency: {
    title: "Artificial deadlines are designed to reduce checking",
    action: "Pause. A legitimate request should survive independent verification.",
  },
  payment: {
    title: "Money movement is a high-impact decision",
    action: "Do not transfer or pay from this message. Confirm the request independently first.",
  },
  credential: {
    title: "OTP and credentials can hand over account control",
    action: "Never share an OTP or password with a sender. Open the official app directly.",
  },
  link: {
    title: "A supplied destination may lead away from the real service",
    action: "Do not open the supplied link. Find the official service independently and compare the claim there.",
  },
  action: {
    title: "The requested next step still needs verification",
    action: "Do not act on the message alone. Confirm the claim through an independent trusted channel.",
  },
};

function cueMatchesNode(node, cues) {
  const typesByNode = {
    authority: ["authority_spoof", "brand_impersonation", "spoofed_sender"],
    urgency: ["urgency_pressure", "threat_language"],
    payment: ["payment_request", "urgent_wire_transfer"],
    credential: ["credential_request", "otp_request"],
    link: ["disguised_link", "url_shortener", "brand_impersonation"],
  };
  const accepted = typesByNode[node.id] || [];
  return cues.filter((cue) => accepted.includes(String(cue?.cue_type || "")));
}

function severityClass(severity) {
  if (severity === "high") return "border-neon-red/50 bg-neon-red/10 text-red-200";
  if (severity === "medium") return "border-gold-neon/40 bg-gold-neon/10 text-amber-200";
  return "border-slate-700 bg-slate-900/70 text-slate-300";
}

/**
 * Interactive, evidence-linked view of the deterministic attack-chain graph.
 * It intentionally uses only the backend's recorded nodes, edges and cues.
 */
export default function ManipulationGraph({ attackChain, cues = [], intendedActions = [], recommendation = "VERIFY" }) {
  const nodes = attackChain?.nodes || [];
  const edges = attackChain?.edges || [];
  const [selectedId, setSelectedId] = useState(nodes[0]?.id || "");
  const selected = nodes.find((node) => node.id === selectedId) || nodes[0] || null;
  const linkedCues = useMemo(() => selected ? cueMatchesNode(selected, cues) : [], [selected, cues]);
  const incoming = edges.filter((edge) => edge.to === selected?.id);
  const outgoing = edges.filter((edge) => edge.from === selected?.id);
  const guidance = NODE_GUIDANCE[selected?.id] || {
    title: "Inspect this step before making a decision",
    action: "Pause and verify independently before acting.",
  };

  if (!nodes.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-space-950/70 p-4 text-sm text-slate-500">
        No manipulation-chain nodes were recorded for this case. Use the message cues and uncertainty notes below; an empty graph is not proof that a message is safe.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-space-950/70 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-slate-500">MANIPULATION GRAPH™</p>
          <p className="mt-1 text-xs text-slate-400">Select any stage to inspect its role and the evidence linked to it.</p>
        </div>
        <span className="rounded-full border border-gold-neon/30 bg-gold-neon/5 px-2.5 py-1 font-mono text-[9px] font-bold tracking-wider text-gold-neon">
          NEXT STEP: {String(recommendation).replaceAll("_", " ")}
        </span>
      </div>

      <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
        {nodes.map((node, index) => {
          const active = node.id === (selected?.id || selectedId);
          const nodeCues = cueMatchesNode(node, cues);
          return (
            <div key={node.id} className="flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={() => setSelectedId(node.id)}
                aria-pressed={active}
                className={`min-w-[130px] rounded-lg border px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-neon-cyan/70 ${active ? "border-neon-cyan/70 bg-neon-cyan/10 shadow-glow-cyan-soft" : "border-slate-700 bg-slate-900/70 hover:border-slate-500"}`}
              >
                <span className="block font-mono text-[9px] text-slate-500">STAGE {String(index + 1).padStart(2, "0")}</span>
                <span className={`mt-1 block text-[11px] font-bold leading-snug ${active ? "text-neon-cyan" : "text-slate-200"}`}>{node.label}</span>
                <span className="mt-2 block text-[8px] tracking-wider text-slate-500">{KIND_LABELS[node.kind] || String(node.kind || "EVIDENCE").toUpperCase()}</span>
                {nodeCues.length > 0 && <span className="mt-2 inline-flex rounded-full border border-neon-red/40 bg-neon-red/10 px-1.5 py-0.5 font-mono text-[9px] text-red-200">{nodeCues.length} linked cue{nodeCues.length === 1 ? "" : "s"}</span>}
              </button>
              {index < nodes.length - 1 && <span aria-hidden="true" className="font-mono text-lg text-slate-600">→</span>}
            </div>
          );
        })}
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1fr]">
        <section className="rounded-lg border border-neon-cyan/25 bg-neon-cyan/5 p-4">
          <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-neon-cyan">SELECTED STAGE</p>
          <h3 className="mt-1 text-base font-black text-slate-100">{selected?.label}</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">{guidance.title}</p>
          <div className="mt-3 space-y-1 text-[11px] text-slate-500">
            {incoming.map((edge, index) => <p key={`in-${index}`}>← From previous stage: {edge.reason || "recorded sequence"}</p>)}
            {outgoing.map((edge, index) => <p key={`out-${index}`}>→ Leads to next stage: {edge.reason || "recorded sequence"}</p>)}
            {!incoming.length && !outgoing.length && <p>This is the only recorded stage in the current chain.</p>}
          </div>
        </section>

        <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
          <p className="font-mono text-[9px] font-bold tracking-[0.16em] text-slate-500">EVIDENCE & SAFE BREAKPOINT</p>
          {linkedCues.length ? (
            <div className="mt-2 space-y-2">
              {linkedCues.map((cue, index) => (
                <div key={`${cue.cue_type}-${index}`} className={`rounded-md border p-2.5 ${severityClass(cue.severity)}`}>
                  <p className="font-mono text-[9px] font-bold tracking-wider">{String(cue.cue_type || "cue").replaceAll("_", " ").toUpperCase()} · {String(cue.severity || "unrated").toUpperCase()}</p>
                  {cue.text && <p className="mt-1 text-xs">“{cue.text}”</p>}
                  {cue.explanation && <p className="mt-1 text-xs opacity-80">{cue.explanation}</p>}
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs leading-relaxed text-slate-500">No direct cue-to-stage match was recorded. This stage is shown as part of the rule-based chain, not as independently confirmed intent.</p>
          )}
          <div className="mt-3 rounded-md border border-neon-green/25 bg-neon-green/5 p-3">
            <p className="font-mono text-[9px] font-bold tracking-wider text-neon-green">BREAK THE CHAIN HERE</p>
            <p className="mt-1 text-xs leading-relaxed text-slate-200">{guidance.action}</p>
          </div>
        </section>
      </div>

      {intendedActions.length > 0 && (
        <p className="mt-3 border-t border-slate-800 pt-3 text-[10px] leading-relaxed text-slate-500">
          Inferred target action(s): {intendedActions.map((action) => String(action).replaceAll("_", " ")).join(" · ")}. These are rule-based hypotheses from observed cues, not proof of the sender's identity or intent.
        </p>
      )}
    </div>
  );
}
